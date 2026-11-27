"""Map regressions using MapPortable's disposable project and print seam."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import threading
from unittest import mock
import zipfile


class MapUpdateCases:
    def test_round2_v08_approved_allocation_is_required_before_first_archive(self):
        self.map_text()
        self.approved_copy().unlink()
        phases = self.specification["phases"]
        phases[0]["files"], phases[1]["files"] = phases[1]["files"], phases[0]["files"]
        self.write_mapping()
        self.assert_refuses("allocation")
        phases[0]["files"], phases[1]["files"] = phases[1]["files"], phases[0]["files"]
        phases[0]["files"][0].update(lines_low=700, lines_high=800)
        self.write_mapping()
        self.assert_refuses("allocation")

    def test_round2_v08_legacy_plan_needs_its_own_archived_map(self):
        self.write_plan(legacy=True)
        self.write_ledger("PLAN APPROVED v1")
        self.write_mapping()
        self.assert_refuses("legacy")
        self.seed_approved_copy()
        self.assertIn("Phase allocations and estimates unverified", self.map_text())
        self.specification["phases"][0]["files"][0]["lines_high"] += 1
        self.write_mapping()
        self.assert_refuses("approved copy")

    def test_round2_v09_latest_approval_supersedes_previous_inputs(self):
        self.map_text()
        original = self.specification["plan_fingerprint"]
        old_plan, old_mapping = self.plan.read_bytes(), self.mapping.read_bytes()
        self.specification["plan_version"] = "2"
        self.write_plan()
        self.write_mapping()
        self.approve_revision_after_phase_one(original)
        self.assert_states(self.map_text(), "Done", "Waiting")
        self.plan.write_bytes(old_plan)
        self.mapping.write_bytes(old_mapping)
        self.assert_refuses("current approval")

    def test_round2_v09_fingerprint_belongs_to_this_approval(self):
        fp = self.specification["plan_fingerprint"]
        self.write_ledger("PLAN APPROVED v1", fingerprints={"PLAN APPROVED v1": "a" * 40})
        self.ledger.write_text("Earlier file in a note: " + fp + "\n" + self.ledger.read_text())
        self.assert_refuses("fingerprint")
        note = "Plan fingerprint: `%s`\n" % ("a" * 40)
        block = "```\nPlan fingerprint: " + fp + "\n```\n"
        quoted = "> Plan fingerprint: " + fp + "\n"
        indented = "    Plan fingerprint: " + fp + "\n"
        self.ledger.write_text(self.ledger.read_text().replace(note, note + block + quoted + indented))
        self.assert_refuses("fingerprint")

    def test_round2_v09_new_run_can_reuse_a_version(self):
        self.map_text()
        old_copy = self.approved_copy().read_bytes()
        old_ledger = self.ledger.read_text()
        self.specification["phases"][0]["title"] = "Revised first step"
        self.write_plan()
        self.write_mapping()
        self.write_ledger("MIGRATION STOPPED", "PLAN APPROVED v1")
        self.ledger.write_text(old_ledger + self.ledger.read_text())
        self.assertIn("Revised first step", self.map_text())
        self.assertEqual(self.approved_copy().read_bytes(), old_copy)
        self.assertEqual(json.loads((self.state / "approved-map-r2-v1.json").read_bytes()), self.specification)

    @staticmethod
    def print_copy(argv):
        # A deterministic stand-in ties the printed bytes to the exact HTML supplied.
        Path(argv[-1]).write_bytes(b"%PDF-test\n" + Path(argv[-2]).read_bytes())
        return 0

    def test_round2_v10_interrupted_pair_is_recoverable_then_refreshes(self):
        self.assertEqual(self.run_map(renderer=self.print_copy)[0], 0)
        old_html = self.html.read_bytes()
        self.write_ledger("PLAN APPROVED v1", "PHASE 1 STARTED")
        replace = os.replace

        def interrupt(source, dest, *args, **kwargs):
            if Path(dest).name == self.pdf.name:
                raise OSError("interrupted publication")
            return replace(source, dest, *args, **kwargs)

        with mock.patch.object(os, "replace", side_effect=interrupt):
            self.assertNotEqual(self.run_map(renderer=self.print_copy)[0], 0)
        pending = self.state / "Migration-Map.pending.zip"
        self.assertTrue(pending.is_file())
        with zipfile.ZipFile(pending) as complete:
            html = complete.read(self.html.name)
            self.assertNotEqual(html, old_html)
            self.assertIn(b"In progress", html)
            self.assertEqual(complete.read(self.pdf.name), b"%PDF-test\n" + html.split(b"\n<!-- v2e-printed-pdf:")[0])
        # A damaged recovery PDF must not replace a public file, even if its
        # own ZIP checksum was recalculated. The trusted digest lives in HTML.
        original_pair = pending.read_bytes()
        old_pdf = self.pdf.read_bytes()
        with zipfile.ZipFile(pending) as complete:
            comment = complete.comment
        with zipfile.ZipFile(pending, "w") as damaged:
            damaged.comment = comment
            damaged.writestr(self.pdf.name, b"%PDF-test corrupted")
            damaged.writestr(self.html.name, html)
        code, message, print_call = self.run_map(renderer=lambda argv: 1)
        self.assertNotEqual(code, 0)
        self.assertIn("published HTML digest", message)
        print_call.assert_not_called()
        self.assertEqual(self.pdf.read_bytes(), old_pdf)
        pending.write_bytes(original_pair)
        code, _, print_call = self.run_map(renderer=lambda argv: 1)
        self.assertNotEqual(code, 0)
        print_call.assert_called_once()
        self.assertFalse(pending.exists())
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-test\n" + self.html.read_bytes().split(b"\n<!-- v2e-printed-pdf:")[0])
        self.assertIn(b"In progress", self.html.read_bytes())

        pending.write_bytes(b"unrelated entry")
        before = self.html.read_bytes(), self.pdf.read_bytes()
        code, message, _ = self.run_map(renderer=self.print_copy)
        self.assertNotEqual(code, 0)
        self.assertIn("unrecognized file", message)
        self.assertEqual(pending.read_bytes(), b"unrelated entry")
        self.assertEqual(before, (self.html.read_bytes(), self.pdf.read_bytes()))

    def test_round2_v10_old_refresh_cannot_overwrite_later_progress(self):
        # Both requests use the renderer's public entry point; only printing is stubbed.
        old_print, release = threading.Event(), threading.Event()
        results = {}
        project = self.project
        def draw(argv):
            if threading.current_thread().name == "older":
                old_print.set()
                if not release.wait(5):
                    raise AssertionError("timed out releasing the first print")
            return self.print_copy(argv)
        def refresh():
            try:
                results[threading.current_thread().name] = self.renderer.render_project(project)
            except self.renderer.Fail as error:
                results[threading.current_thread().name] = str(error)
        with mock.patch.object(self.renderer.render_pdf, "main", side_effect=draw), redirect_stdout(StringIO()):
            older = threading.Thread(target=refresh, name="older")
            newer = threading.Thread(target=refresh, name="newer")
            older.start()
            try:
                self.assertTrue(old_print.wait(5))
                self.write_ledger("PLAN APPROVED v1", "PHASE 1 STARTED")
                newer.start()
                newer.join(0.15)
            finally:
                release.set()
                older.join(5)
                if newer.ident is not None:
                    newer.join(5)
        self.assertFalse(older.is_alive() or newer.is_alive())
        self.assertEqual(results.get("newer"), 0, results)
        self.assertIn(b"In progress", self.html.read_bytes())
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-test\n" + self.html.read_bytes().split(b"\n<!-- v2e-printed-pdf:")[0])
