"""Migration Map contract on disposable projects, with one native PDF check."""

import base64
import contextlib
from html import escape
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
from xml.etree import ElementTree


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "vibe-to-engineering" / "scripts"
SCRIPT = SCRIPTS / "render_map.py"
APPROVAL = "PLAN APPROVED v1"
PDF_FIXTURE = b"%PDF-1.4\nfixture\n"


class MapFixture:
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="v2e-map-test-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        (self.project / "src").mkdir(parents=True)
        self.state = self.project / ".vibe-to-engineering"
        self.state.mkdir()
        (self.state / ".gitignore").write_bytes(b"*\n")
        self.plan = self.state / "Engineering-Migration-Plan.html"
        self.ledger = self.state / "ledger.md"
        self.mapping = self.state / "migration-map.json"
        self.html = self.state / "Migration-Map.html"
        self.pdf = self.state / "Migration-Map.pdf"
        (self.project / "src" / "large.py").write_bytes(b"# original\n" * 20)
        self.specification = {
            "schema": 1,
            "plan_version": "1",
            "project": "Sample",
            "sources": [{"path": "src/large.py", "lines": 20, "parts": [
                {"id": "flow", "label": "Flow", "from": 1, "to": 12},
                {"id": "record", "label": "Record", "from": 13, "to": 20},
            ]}],
            "phases": [
                {"number": 1, "title": "Move flow", "files": [
                    {"path": "src/flow.py", "lines_low": 10, "lines_high": 15,
                     "from": [{"part": "flow", "exact": True}]},
                ]},
                {"number": 2, "title": "Move records", "files": [
                    {"path": "src/records.py", "lines_low": 5, "lines_high": 9,
                     "from": [{"part": "record", "exact": False}]},
                ]},
            ],
        }
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

    def write_plan(self):
        paths = ["src/large.py", "src/decoy.py.backup"]
        paths += [f["path"] for phase in self.specification["phases"] for f in phase["files"]]
        rows = "".join('<tr><td class="path">%s</td><td>new</td></tr>' % escape(path) for path in paths)
        headings = "".join(
            '<article class="phase"><h3><span>Phase %d — %s</span>'
            '<span class="badge low">Low risk</span></h3></article>' % (phase["number"], escape(phase["title"]))
            for phase in self.specification["phases"]
        )
        self.plan.write_text(
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sample plan</title></head><body>'
            '<section class="sheet" id="files"><h2>Every file</h2><table><tbody>' + rows +
            '</tbody></table><h3>Why each new file exists</h3><table><tbody>' + rows +
            '</tbody></table></section><section class="sheet" id="phases">' + headings + '</section></body></html>',
            encoding="utf-8",
        )
        self.specification["plan_fingerprint"] = subprocess.check_output(
            ["git", "hash-object", "--no-filters", str(self.plan)], cwd=self.project, text=True,
        ).strip()

    def write_ledger(self, *events, body=""):
        self.ledger.write_text("# Ledger\n\n" + "".join(
            "## 2026-11-21T10:00:%02dZ — %s — synthetic event\n\n" % (index, event)
            for index, event in enumerate(events)
        ) + body, encoding="utf-8")

    def write_mapping(self):
        self.mapping.write_text(json.dumps(self.specification), encoding="utf-8")


class MapPortable(MapFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location("render_map_under_test", str(SCRIPT))
        self.renderer = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
            spec.loader.exec_module(self.renderer)
        profile = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)})
        profile.start()
        self.addCleanup(profile.stop)

    @staticmethod
    def fake_pdf(argv):
        Path(argv[-1]).write_bytes(PDF_FIXTURE)
        return 0

    def run_map(self, renderer=None, **gate):
        output = io.StringIO()
        with mock.patch.object(self.renderer, "require_supported_platform", **gate), \
                mock.patch.object(self.renderer.render_pdf, "main", side_effect=renderer or self.fake_pdf) as pdf, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = self.renderer.main([str(SCRIPT), "--project", str(self.project)])
        return code, output.getvalue(), pdf

    def snapshot_state(self):
        def record(path):
            info = path.lstat()
            body = (path.read_bytes() if stat.S_ISREG(info.st_mode) else
                    os.readlink(path) if stat.S_ISLNK(info.st_mode) and os.name != "nt" else None)
            return info.st_mode, info.st_ino, info.st_mtime_ns, body

        if self.state.is_symlink():
            return {".": record(self.state)}
        return {str(path.relative_to(self.state)): record(path) for path in self.state.rglob("*")}

    def assert_refuses(self, *reason):
        before = self.snapshot_state()
        code, output, pdf = self.run_map()
        self.assertNotEqual(code, 0, output)
        self.assertTrue(output.strip())
        self.assertNotIn("Traceback", output)
        if reason:
            self.assertTrue(any(word in output.lower() for word in reason), output)
        pdf.assert_not_called()
        self.assertEqual(self.snapshot_state(), before)

    def map_text(self):
        code, output, pdf = self.run_map()
        self.assertEqual(code, 0, output)
        pdf.assert_called_once()
        self.assertEqual(self.pdf.read_bytes(), PDF_FIXTURE)
        return self.html.read_text(encoding="utf-8")

    def phase_card(self, text, number):
        card = re.search(r'<article\b[^>]*\bid="phase-%d"[^>]*>(.*?)</article>' % number, text, re.S)
        self.assertIsNotNone(card, "phase %d card is missing" % number)
        return card.group(1)

    def assert_states(self, text, first, second):
        for number, state in enumerate((first, second), 1):
            self.assertRegex(self.phase_card(text, number), r">\s*%s\s*<" % state)

    @contextlib.contextmanager
    def fixture_link(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name != "nt" or getattr(error, "winerror", None) not in (5, 1314):
                raise
            # Windows may deny creation to an unprivileged process. Present the
            # link's lstat at the same boundary without requiring that privilege.
            if directory:
                path.mkdir()
            else:
                path.write_bytes(b"not an actual source file\n")
            real_lstat = os.lstat

            def linked_lstat(candidate, *args, **kwargs):
                result = real_lstat(candidate, *args, **kwargs)
                if Path(candidate) != path:
                    return result
                attributes = {name: getattr(result, name) for name in dir(result) if name.startswith("st_")}
                attributes.update(st_mode=stat.S_IFLNK, st_file_attributes=0x400)
                return SimpleNamespace(**attributes)

            with mock.patch.object(os, "lstat", side_effect=linked_lstat):
                yield
        else:
            yield

    def test_stale_fingerprint_preserves_existing_map_outputs(self):
        self.html.write_bytes(b"existing map HTML")
        self.pdf.write_bytes(PDF_FIXTURE)
        with self.plan.open("ab") as handle:
            handle.write(b"<!-- edited after approval -->")
        self.assert_refuses("fingerprint", "hash")

    def test_requires_an_approval_heading_for_the_version(self):
        self.write_ledger("PLAN APPROVED v10", body="### PLAN APPROVED v1\n\nQuoted `PLAN APPROVED v1`.")
        self.assert_refuses("approval", "approved")

    def test_phase_number_and_title_must_both_match_the_plan(self):
        phase = self.specification["phases"][1]
        for key, different in (("number", 3), ("title", "Unexpected title")):
            with self.subTest(field=key):
                previous = phase[key]
                phase[key] = different
                self.write_mapping()
                self.assert_refuses("phase")
                phase[key] = previous

    def test_mapped_path_requires_a_complete_match_in_the_plan(self):
        self.specification["phases"][0]["files"][0]["path"] = "src/decoy.py"
        self.write_mapping()
        self.assert_refuses("src/decoy.py", "plan")

    def test_old_source_coverage_refuses_overlap_gap_and_open_ends(self):
        parts = self.specification["sources"][0]["parts"]
        cases = ((1, "from", 12), (1, "from", 14), (0, "from", 2), (1, "to", 19), (1, "to", 21))
        for part, key, boundary in cases:
            with self.subTest(part=part, field=key, boundary=boundary):
                previous = parts[part][key]
                parts[part][key] = boundary
                self.write_mapping()
                self.assert_refuses("part", "range", "coverage", "cover", "overlap", "gap")
                parts[part][key] = previous

    def test_every_part_is_known_and_mapped_to_a_file(self):
        link = self.specification["phases"][1]["files"][0]["from"][0]
        for part in ("flow", "unknown"):
            with self.subTest(part=part):
                link["part"] = part
                self.write_mapping()
                self.assert_refuses("part", "mapped", "used", "unknown")

    def test_refuses_inverted_planned_line_range(self):
        self.specification["phases"][0]["files"][0]["lines_low"] = 16
        self.write_mapping()
        self.assert_refuses("line", "range")

    def test_refuses_a_bad_checkpoint_state_guard_file(self):
        (self.state / ".gitignore").write_bytes(b"wrong\n")
        self.assert_refuses(".gitignore", "state ignore")

    def test_refuses_a_linked_state_folder(self):
        outside = self.base / "elsewhere"
        self.state.rename(outside)
        previous = sorted(path.name for path in outside.iterdir())
        with self.fixture_link(self.state, outside, directory=True):
            self.assert_refuses("link", "state")
        self.assertEqual(sorted(path.name for path in outside.iterdir()), previous)

    def test_refuses_linked_map_input_and_output(self):
        elsewhere = self.base / "outside.json"
        self.mapping.rename(elsewhere)
        original = elsewhere.read_bytes()
        with self.fixture_link(self.mapping, elsewhere):
            self.assert_refuses("link", "migration-map.json")
        self.mapping.unlink()
        self.write_mapping()
        with self.fixture_link(self.pdf, elsewhere):
            self.assert_refuses("link", "migration-map.pdf")
        self.assertEqual(elsewhere.read_bytes(), original)

    def test_refuses_a_nonregular_output_destination(self):
        self.html.mkdir()
        self.assert_refuses("regular", "migration-map.html")

    def test_ledger_uses_only_headings_after_the_last_matching_approval(self):
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "MIGRATION STOPPED", APPROVAL,
                          "PLAN APPROVED v2", "PHASE 1 STARTED",
                          body="PHASE 2 COMPLETE\n\n### PHASE 2 FAILED\n\n```\n## PHASE 2 COMPLETE\n```\n")
        text = self.map_text()
        self.assert_states(text, "Now", "Waiting")
        self.assertNotRegex(text, r">\s*Stopped\s*<")

    def test_ledger_waiting_now_failed_and_done(self):
        events = [APPROVAL]
        for event, expected in ((None, "Waiting"), ("PHASE 1 STARTED", "Now"),
                                ("PHASE 1 FAILED", "Failed"), ("PHASE 1 COMPLETE", "Done")):
            with self.subTest(expected=expected):
                if event:
                    events.append(event)
                self.write_ledger(*events)
                self.assert_states(self.map_text(), expected, "Waiting")

    def test_phase_restore_keeps_earlier_phases_and_allows_retry(self):
        events = [APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 STARTED", "PHASE 2 FAILED"]
        for checkpoint in ("01-phase-1", "r2-01-phase-1"):
            with self.subTest(checkpoint=checkpoint):
                restore = "RESTORED " + checkpoint
                self.write_ledger(*events, restore)
                self.assert_states(self.map_text(), "Done", "Waiting")
                self.write_ledger(*events, restore, "PHASE 2 STARTED")
                self.assert_states(self.map_text(), "Done", "Now")
                self.write_ledger(*events, restore, "PHASE 2 STARTED", "PHASE 2 COMPLETE")
                self.assert_states(self.map_text(), "Done", "Done")

    def test_baseline_restore_puts_every_phase_back_to_waiting(self):
        for checkpoint in ("00-baseline", "00-baseline-checked"):
            with self.subTest(checkpoint=checkpoint):
                self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 FAILED", "RESTORED " + checkpoint)
                text = self.map_text()
                self.assert_states(text, "Waiting", "Waiting")
                self.assertIn("Phase 1 retry approval", text)

    def test_unrecognized_restore_is_refused(self):
        self.write_ledger(APPROVAL, "RESTORED pre-restore-example")
        self.assert_refuses("restore", "checkpoint")

    def test_migration_stop_is_visible_and_does_not_erase_phase_state(self):
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 FAILED", "MIGRATION STOPPED")
        text = self.map_text()
        self.assertRegex(text, r">[^<>]*\bStopped\b[^<>]*<")
        self.assert_states(text, "Done", "Failed")

    def test_completed_phase_displays_actual_lines_with_planned_range(self):
        (self.project / "src" / "flow.py").write_bytes(b"first\r\nsecond\nthird")
        (self.project / "src" / "records.py").write_bytes(b"four\nfive\n")
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 STARTED")
        text = self.map_text()
        self.assertRegex(self.phase_card(text, 1), r"10\s*[–—-]\s*15")
        self.assertRegex(self.phase_card(text, 1), r"Actual:\s*3\b")
        self.assertNotIn("Actual:", self.phase_card(text, 2))

    def test_approved_characterization_check_in_state_folder_can_be_mapped(self):
        path = ".vibe-to-engineering/checks/check_cli.py"
        file = self.specification["phases"][0]["files"][0]
        file["path"] = path
        self.write_plan()
        self.write_mapping()
        planned = self.project / path
        planned.parent.mkdir()
        planned.write_text("# first\n# second\n", encoding="utf-8")
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE")
        card = self.phase_card(self.map_text(), 1).replace("<br>", "")
        self.assertIn(path, card)
        self.assertIn("Actual: 2", card)

    def test_completed_missing_linked_and_nonregular_files_are_missing(self):
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 COMPLETE")
        (self.project / "src" / "flow.py").mkdir()
        self.assertEqual(self.map_text().count("Actual: missing"), 2)
        outside = self.base / "outside.py"
        outside.write_bytes(b"outside\n" * 148)
        with self.fixture_link(self.project / "src" / "records.py", outside):
            text = self.map_text()
        self.assertEqual(text.count("Actual: missing"), 2)
        self.assertNotIn("Actual: 148", text)

    def test_user_labels_are_escaped_text(self):
        hostile = '<img src="https://example.invalid/fixture.png" onerror="oops()"> & quoted'
        self.specification["project"] = hostile
        self.specification["sources"][0]["parts"][0]["label"] = hostile
        self.specification["phases"][0]["title"] = hostile
        self.write_plan()
        self.write_mapping()
        text = self.map_text()
        self.assertNotIn(hostile, text)
        self.assertGreaterEqual(text.replace("<br>", "").count(escape(hostile)), 3)
        self.assertEqual(self.renderer.render_pdf.static_problems(text), [])

    def test_hostile_theme_markup_is_refused_before_pdf_rendering(self):
        theme = self.home / ".vibe-to-engineering" / "map-theme.css"
        theme.parent.mkdir()
        theme.write_text('</style><img src="https://example.invalid/fixture.png">', encoding="utf-8")
        self.assert_refuses("theme")

    def test_theme_css_must_pass_the_existing_pdf_checks(self):
        theme = self.home / ".vibe-to-engineering" / "map-theme.css"
        theme.parent.mkdir()
        theme.write_text('@import "https://example.invalid/theme.css";', encoding="utf-8")
        before = self.snapshot_state()
        real_pdf = self.renderer.render_pdf.main
        with mock.patch.object(self.renderer.render_pdf, "require_supported_platform"), \
                mock.patch.object(self.renderer.render_pdf, "find_browser") as browser:
            code, output, _ = self.run_map(renderer=real_pdf)
        self.assertNotEqual(code, 0, output)
        self.assertEqual(self.snapshot_state(), before)
        browser.assert_not_called()

    def test_pdf_failure_preserves_both_previous_outputs(self):
        self.html.write_bytes(b"previous HTML")
        self.pdf.write_bytes(PDF_FIXTURE)
        before = self.snapshot_state()
        code, output, render = self.run_map(renderer=lambda argv: 1)
        self.assertNotEqual(code, 0, output)
        render.assert_called_once()
        self.assertEqual(self.snapshot_state(), before)

    def test_long_map_breaks_between_phases_and_keeps_every_file(self):
        for phase in self.specification["phases"]:
            prototype = phase["files"][0]
            phase["files"] = [dict(prototype, path="src/chunk-%d-%02d.py" % (phase["number"], index))
                              for index in range(20)]
        self.write_plan()
        self.write_mapping()
        sheets = self.map_text().split("</section>")
        for index, phase in enumerate(self.specification["phases"], 1):
            page = sheets[index - 1]
            self.assertIn("Page %d of 2" % index, page)
            self.assertEqual(page.count('<article id="phase-'), 1)
            for file in phase["files"]:
                self.assertIn(file["path"], page)

    def test_platform_refuses_before_resolving_project(self):
        before = self.snapshot_state()
        with mock.patch.object(self.renderer, "resolve_project") as resolve:
            code, output, pdf = self.run_map(side_effect=self.renderer.PlatformRefusal("macOS only"))
        self.assertNotEqual(code, 0, output)
        self.assertIn("macOS", output)
        self.assertEqual(self.snapshot_state(), before)
        resolve.assert_not_called()
        pdf.assert_not_called()


@unittest.skipUnless(sys.platform == "darwin", "native macOS browser render")
class MapRenderer(MapFixture, unittest.TestCase):
    def test_printed_map_accepts_solid_and_dashed_connector_image(self):
        if not os.environ.get("V2E_BROWSER"):
            if os.environ.get("V2E_REQUIRE_MATRIX"):
                self.fail("native validation requires the pinned V2E_BROWSER")
            self.skipTest("set V2E_BROWSER to a native Chrome-family browser")
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.project)],
                                env=env, capture_output=True, text=True, timeout=195)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = self.html.read_text(encoding="utf-8")
        payloads = re.findall(r'<img\b[^>]*\bsrc="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"', text)
        self.assertEqual(len(payloads), 1)
        self.assertNotRegex(text, r"(?i)<\s*svg\b")
        layer = ElementTree.fromstring(base64.b64decode(payloads[0], validate=True))
        self.assertEqual(layer.tag, "{http://www.w3.org/2000/svg}svg")
        paths = list(layer)
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(path.tag == "{http://www.w3.org/2000/svg}path" and not list(path) for path in paths))
        self.assertEqual(sum("stroke-dasharray" in path.attrib for path in paths), 1)
        pdf = self.pdf.read_bytes()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page(?!s)\b", pdf)), 1)


if __name__ == "__main__":
    unittest.main()
