"""Migration Map contract on disposable projects, with native PDF checks."""

import base64
import contextlib
from copy import deepcopy
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
ALL_GREEN = "VIBE-TO-ENGINEERING — ALL GREEN"
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

    def write_plan(self, *, version=None, evidence=None, old_lines=None, without_evidence=()):
        version = self.specification["plan_version"] if version is None else version
        evidence = {} if evidence is None else evidence
        old_lines = {} if old_lines is None else old_lines
        files = [file for phase in self.specification["phases"] for file in phase["files"]]
        sources = self.specification["sources"]
        parts = {part["id"]: (source["path"], part["from"], part["to"])
                 for source in sources for part in source["parts"]}
        paths = [source["path"] for source in sources] + ["src/decoy.py.backup"] + [file["path"] for file in files]
        rows = "".join('<tr><td class="path">%s</td></tr>' % escape(path) for path in paths)
        new_rows = []
        for file in files:
            path = file["path"]
            if path in without_evidence:
                continue
            ranges = {}
            for link in file["from"]:
                source, start, end = parts[link["part"]]
                prefix = "" if link["exact"] else "part of "
                ranges.setdefault(source, []).append(f"{prefix}{start}–{end}")
            cell = "; ".join(f"{source}: {', '.join(items)}" for source, items in ranges.items()) or "none"
            state = "exact" if all(link["exact"] for link in file["from"]) else "not yet exact: split boundary"
            new_rows.append(
                '<tr><td class="path">%s</td><td>%s</td><td>F1</td>'
                '<td>Extract a responsibility</td><td>%s</td></tr>' %
                (escape(path), escape(old_lines.get(path, cell)), escape(evidence.get(path, state))),
            )
        headings = "".join(
            '<article class="phase"><h3><span>Phase %d — %s</span>'
            '<span class="badge low">Low risk</span></h3></article>' % (phase["number"], escape(phase["title"]))
            for phase in self.specification["phases"]
        )
        self.plan.write_text(
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Sample plan</title></head><body>'
            '<section class="sheet" id="summary"><div class="meta"><span>Plan version ' + escape(version) +
            '</span></div></section><section class="sheet" id="files"><h2>Every file</h2><table><tbody>' + rows +
            '</tbody></table><h3>Why each new file exists</h3><table id="new-files"><tbody>' + "".join(new_rows) +
            '</tbody></table></section><section class="sheet" id="phases">' + headings + '</section></body></html>',
            encoding="utf-8",
        )
        self.fingerprint_plan()

    def fingerprint_plan(self):
        self.specification["plan_fingerprint"] = subprocess.check_output(
            ["git", "hash-object", "--no-filters", str(self.plan)], cwd=self.project, text=True,
        ).strip()

    def write_ledger(self, *events, body="", fingerprints=None):
        if fingerprints is None:
            approval = "PLAN APPROVED v" + self.specification["plan_version"]
            fingerprints = {approval: self.specification["plan_fingerprint"]}
        entries = ["# Ledger\n\n"]
        for index, event in enumerate(events):
            if event in fingerprints:
                entries.append("Plan fingerprint: `%s`\n\n" % fingerprints[event])
            entries.append("## 2026-11-21T10:00:%02dZ — %s — synthetic event\n\n" % (index, event))
        self.ledger.write_text("".join(entries) + body, encoding="utf-8")

    def write_mapping(self):
        self.mapping.write_text(json.dumps(self.specification), encoding="utf-8")

    def approved_copy(self, version=None):
        version = self.specification["plan_version"] if version is None else version
        return self.state / ("approved-map-v%s.json" % version)

    def seed_approved_copy(self):
        with self.approved_copy().open("x", encoding="utf-8") as archive:
            json.dump(self.specification, archive)


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

    def assert_refuses(self, *reason, saves_approval=False):
        before = self.snapshot_state()
        code, output, pdf = self.run_map()
        self.assertNotEqual(code, 0, output)
        self.assertTrue(output.strip())
        self.assertNotIn("Traceback", output)
        if reason:
            self.assertTrue(any(word in output.lower() for word in reason), output)
        pdf.assert_not_called()
        after = self.snapshot_state()
        if saves_approval:
            archive = self.approved_copy()
            self.assertEqual(json.loads(archive.read_bytes()), self.specification)
            del after[archive.name]
        self.assertEqual(after, before)

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

    def test_ledger_uses_current_run_headings_only(self):
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "MIGRATION STOPPED", APPROVAL,
                          "PLAN APPROVED v2", "PHASE 1 STARTED",
                          body="PHASE 2 COMPLETE\n\n### PHASE 2 FAILED\n\n```\n## PHASE 2 COMPLETE\n```\n")
        text = self.map_text()
        self.assert_states(text, "Now", "Waiting")
        self.assertNotRegex(text, r">\s*Stopped\s*<")

    def test_fix_f1_carries_completed_phases_through_plan_revisions(self):
        self.seed_approved_copy()
        original_fingerprint = self.specification["plan_fingerprint"]
        self.specification["plan_version"] = "2"
        self.write_plan()
        self.write_mapping()
        revised = "PLAN APPROVED v2"
        fingerprints = {APPROVAL: original_fingerprint, revised: self.specification["plan_fingerprint"]}
        (self.project / "src" / "flow.py").write_text("def flow():\n    return 1\n", encoding="utf-8")
        completed = (APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE")

        with self.subTest("previously completed phase"):
            self.write_ledger(*completed, revised, fingerprints=fingerprints)
            text = self.map_text()
            self.assert_states(text, "Done", "Waiting")
            self.assertIn("Actual: 2", self.phase_card(text, 1))
            self.assertIn("1 of 2", text)
            self.assertIn("Phase 2 approval", text)

        with self.subTest("phase removed from the revised plan"):
            self.write_ledger(*completed, "PHASE 3 STARTED", revised, fingerprints=fingerprints)
            self.assert_states(self.map_text(), "Done", "Waiting")
            self.write_ledger(*completed, revised, "PHASE 3 STARTED", fingerprints=fingerprints)
            self.assert_refuses("phase", "plan")

        for terminal in (
            "MIGRATION STOPPED",
            "VIBE-TO-ENGINEERING — ALL GREEN",
            "VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES",
            "VIBE-TO-ENGINEERING — COMPLETE WITH ACCEPTED VERIFICATION GAPS",
        ):
            with self.subTest(previous_run_ended=terminal):
                self.write_ledger(*completed, terminal, revised, fingerprints=fingerprints)
                text = self.map_text()
                self.assert_states(text, "Waiting", "Waiting")
                self.assertNotRegex(text, r">\s*Stopped\s*<")
                self.assertIn("Prepare baseline", text)

    def test_fix_f2_refuses_an_omitted_planned_new_file(self):
        phases = self.specification["phases"]
        flow, records = (phase["files"][0] for phase in phases)
        records["from"].extend(flow["from"])
        self.write_plan()
        self.write_ledger(APPROVAL)
        phases[0]["files"].pop()
        self.write_mapping()
        self.assert_refuses("planned new file is missing from the map: src/flow.py")

    def test_fix_f3_requires_plan_version_and_fingerprint_from_its_approval(self):
        with self.plan.open("ab") as plan:
            plan.write(b"<!-- edited after approval -->")
        self.fingerprint_plan()
        self.write_mapping()
        current = self.specification["plan_fingerprint"]
        with self.subTest("unapproved edit and new map hash"):
            self.assert_refuses("fingerprint")

        with self.subTest("hash only before the preceding approval"):
            self.write_ledger("PLAN APPROVED v0", APPROVAL, fingerprints={"PLAN APPROVED v0": current})
            self.assert_refuses("fingerprint")

        with self.subTest("hash only after approval"):
            self.write_ledger(APPROVAL, body="Plan fingerprint: `%s`\n" % current, fingerprints={})
            self.assert_refuses("fingerprint")

        with self.subTest("hash embedded in a longer word"):
            self.write_ledger(APPROVAL, fingerprints={APPROVAL: current + "0"})
            self.assert_refuses("fingerprint")

        with self.subTest("visible plan version differs"):
            self.write_plan(version="2")
            self.write_mapping()
            self.write_ledger(APPROVAL)
            self.assert_refuses("version")

    def test_fix_f4_requires_map_links_to_match_approved_evidence(self):
        flow = self.specification["phases"][0]["files"][0]
        records = self.specification["phases"][1]["files"][0]
        records["from"].append({"part": "flow", "exact": True})
        self.write_plan(evidence={flow["path"]: "exact",
                                  records["path"]: "not yet exact: one split boundary remains"})
        self.write_ledger(APPROVAL)
        self.write_mapping()
        with self.subTest("mixed links match a not yet exact row"):
            self.assert_states(self.map_text(), "Waiting", "Waiting")

        for file, invalid in ((flow, False), (records, True)):
            link = file["from"][0]
            original = link["exact"]
            with self.subTest(path=file["path"], exact=invalid):
                link["exact"] = invalid
                self.write_mapping()
                self.assert_refuses("evidence", "exact", file["path"])
            link["exact"] = original

        with self.subTest("unrecognized evidence"):
            self.write_plan(evidence={records["path"]: "reviewed"})
            self.write_mapping()
            self.write_ledger(APPROVAL)
            self.assert_refuses("evidence", records["path"])

    def test_fix_f5_verifies_listed_source_counts_before_the_first_phase_starts(self):
        source = self.specification["sources"][0]
        last_part = source["parts"][-1]
        with self.subTest("false source count before starting"):
            source["lines"] = last_part["to"] = 999
            self.write_mapping()
            self.assert_refuses("source", "lines")

        with self.subTest("start in a previous run does not waive verification"):
            self.write_ledger("PLAN APPROVED v0", "PHASE 1 STARTED", "MIGRATION STOPPED", APPROVAL)
            self.assert_refuses("source", "lines")

        source["lines"] = last_part["to"] = 20
        (self.project / "src" / "large.py").write_bytes(b"# after the split\n" * 4)
        self.write_ledger(APPROVAL, "PHASE 1 STARTED")
        self.write_mapping()
        with self.subTest("historic source count after starting"):
            text = self.map_text()
            self.assert_states(text, "Now", "Waiting")
            self.assertIn("20 lines today", text)

        with self.subTest("source missing from the plan after starting"):
            source["path"] = "src/unplanned.py"
            (self.project / source["path"]).write_bytes(b"# unplanned\n" * 20)
            self.write_mapping()
            self.assert_refuses("source", "plan")

    def approve_revision_after_phase_one(self, original_fingerprint, *, version="2"):
        self.specification["plan_version"] = version
        self.write_plan()
        self.write_mapping()
        revised = "PLAN APPROVED v" + version
        self.write_ledger(
            APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE", revised,
            fingerprints={APPROVAL: original_fingerprint, revised: self.specification["plan_fingerprint"]},
        )

    def test_fix_g1_refuses_changed_completed_phases(self):
        original = deepcopy(self.specification)
        self.seed_approved_copy()
        for version, change in enumerate(("retitle", "swap", "file set"), start=2):
            with self.subTest(change=change):
                self.specification = deepcopy(original)
                phases = self.specification["phases"]
                if change == "retitle":
                    phases[0]["title"] = "Different unbuilt work"
                elif change == "swap":
                    phases.reverse()
                    phases[0]["number"], phases[1]["number"] = 1, 2
                else:
                    phases[0]["files"][0]["path"] = "src/new-unbuilt-file.py"
                self.approve_revision_after_phase_one(original["plan_fingerprint"], version=str(version))
                self.assert_refuses("phase 1")

    def test_fix_g1_refuses_missing_completed_phase_approved_copy(self):
        original = deepcopy(self.specification)
        with self.subTest("earlier version"):
            self.approve_revision_after_phase_one(original["plan_fingerprint"])
            self.assert_refuses("phase 1")
        with self.subTest("current version"):
            self.specification = original
            self.write_plan()
            self.write_mapping()
            self.write_ledger(APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE")
            self.assert_states(self.map_text(), "Done", "Waiting")
            self.assertEqual(json.loads(self.approved_copy().read_bytes()), self.specification)

    def test_removed_completed_phase_stays_allowed_in_revision(self):
        original_fingerprint = self.specification["plan_fingerprint"]
        self.specification["phases"].pop(0)
        source = self.specification["sources"][0]
        source["parts"].pop(0)
        source["parts"][0]["from"] = 1
        self.approve_revision_after_phase_one(original_fingerprint)
        text = self.map_text()
        self.assertNotIn('id="phase-1"', text)
        self.assertRegex(self.phase_card(text, 2), r">\s*Waiting\s*<")
        self.assertIn("Phase 2 approval", text)

    def submit_moved_file_revision(self):
        original_fingerprint = self.specification["plan_fingerprint"]
        self.seed_approved_copy()
        self.approve_revision_after_phase_one(original_fingerprint)
        first, second = self.specification["phases"]
        second["files"].append(first["files"].pop())
        self.write_mapping()

    def test_fix_j1_refused_revision_does_not_save_v2_copy(self):
        self.submit_moved_file_revision()
        self.assert_refuses("phase 1 cannot carry completion")

    def test_fix_j1_corrected_revision_renders_after_refusal(self):
        self.submit_moved_file_revision()
        code, output, pdf = self.run_map()
        self.assertNotEqual(code, 0, output)
        self.assertIn("Phase 1 cannot carry completion", output)
        pdf.assert_not_called()

        first, second = self.specification["phases"]
        first["files"].append(second["files"].pop())
        self.write_mapping()
        self.assert_states(self.map_text(), "Done", "Waiting")
        self.assertEqual(json.loads(self.approved_copy().read_bytes()), self.specification)

    def test_fix_g1_records_parsed_map_in_write_once_approved_copy(self):
        # The layout supports an unsorted map, but the saved copy must keep its submitted order.
        self.specification["sources"][0]["parts"].reverse()
        self.write_mapping()
        self.map_text()
        archive = self.approved_copy()
        self.assertTrue(archive.is_file(), "rendering an approved map creates its own copy")
        body = archive.read_bytes()
        self.assertEqual(json.loads(body), self.specification)
        before = archive.stat()
        self.mapping.write_text(json.dumps(self.specification, sort_keys=True, indent=2), encoding="utf-8")
        self.map_text()
        self.assertEqual(archive.read_bytes(), body)
        after = archive.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_fix_g1_refuses_changed_map_data_for_same_approved_version(self):
        self.seed_approved_copy()
        self.map_text()
        original = deepcopy(self.specification)
        for change in ("estimate", "source part order"):
            with self.subTest(change=change):
                self.specification = deepcopy(original)
                if change == "estimate":
                    self.specification["phases"][0]["files"][0]["lines_low"] = 11
                else:
                    self.specification["sources"][0]["parts"].reverse()
                self.write_mapping()
                self.assert_refuses("version", "approved")

    def test_fix_g1_refuses_linked_approved_copy(self):
        outside = self.base / "outside.json"
        outside.write_text(json.dumps(self.specification), encoding="utf-8")
        before = outside.read_bytes()
        with self.fixture_link(self.approved_copy(), outside):
            self.assert_refuses("link", "approved")
        self.assertEqual(outside.read_bytes(), before)

    def test_fix_g1_refuses_unsafe_plan_version(self):
        version = "1/../elsewhere"
        self.specification["plan_version"] = version
        self.write_plan()
        self.write_mapping()
        self.write_ledger("PLAN APPROVED v" + version)
        self.assert_refuses("version")

    def test_fix_g2_requires_strict_evidence_with_inexact_reason(self):
        for path, value in (
            ("src/flow.py", "exact? guessed, never read"),
            ("src/records.py", "not yet exact"),
            ("src/records.py", "not yet exact:    "),
        ):
            with self.subTest(evidence=value):
                self.write_plan(evidence={path: value})
                self.write_ledger(APPROVAL)
                self.write_mapping()
                self.assert_refuses("evidence", "exact")

    def move_flow_link_to_records(self):
        flow, records = (phase["files"][0] for phase in self.specification["phases"])
        records["from"].append(flow["from"].pop())
        return flow["path"]

    def test_fix_g3_none_means_an_exact_file_without_links(self):
        self.write_plan(old_lines={"src/flow.py": "none"})
        self.write_ledger(APPROVAL)
        self.write_mapping()
        with self.subTest("none with a link"):
            self.assert_refuses("src/flow.py", "link")
        with self.subTest("none without links"):
            path = self.move_flow_link_to_records()
            self.write_plan(old_lines={path: "none"})
            self.write_ledger(APPROVAL)
            self.write_mapping()
            self.assert_states(self.map_text(), "Waiting", "Waiting")

    def test_fix_g3_refuses_exact_file_with_unmapped_old_lines(self):
        path = self.move_flow_link_to_records()
        self.write_plan(old_lines={path: "src/large.py: 1–12"})
        self.write_ledger(APPROVAL)
        self.write_mapping()
        self.assert_refuses("src/flow.py", "link")

    def test_fix_g4_finished_map_shows_specific_outcome_and_no_next_stop(self):
        self.seed_approved_copy()
        for event, state in (
            ("ALL GREEN", "All green"),
            ("COMPLETE WITH APPROVED BASELINE FAILURES", "Complete with approved failures"),
            ("COMPLETE WITH ACCEPTED VERIFICATION GAPS", "Complete with accepted gaps"),
        ):
            with self.subTest(event=event):
                self.write_ledger(APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE", "PHASE 2 STARTED",
                                  "PHASE 2 COMPLETE", "VIBE-TO-ENGINEERING — " + event)
                text = self.map_text()
                self.assert_states(text, "Done", "Done")
                self.assertIn("<span>Status</span><strong>%s</strong>" % state, text)
                self.assertIn("<span>Next stop</span><strong>None</strong>", text)

    def test_fix_h1_refuses_outcome_with_a_waiting_now_or_failed_phase(self):
        self.seed_approved_copy()
        for second_phase in ((), ("PHASE 2 STARTED",), ("PHASE 2 STARTED", "PHASE 2 FAILED")):
            with self.subTest(second_phase=second_phase):
                self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", *second_phase, ALL_GREEN)
                self.assert_refuses("final outcome requires every phase to be done")

    def test_fix_h1_refuses_phase_and_restore_events_after_an_outcome(self):
        self.seed_approved_copy()
        for event in ("PHASE 2 STARTED", "PHASE 2 COMPLETE", "PHASE 2 FAILED", "RESTORED 01-phase-1"):
            with self.subTest(event=event):
                self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 COMPLETE", ALL_GREEN, event)
                self.assert_refuses("follows the final outcome")

    def test_fix_j4_refuses_stop_after_each_final_outcome(self):
        self.seed_approved_copy()
        for outcome in (
            ALL_GREEN,
            "VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES",
            "VIBE-TO-ENGINEERING — COMPLETE WITH ACCEPTED VERIFICATION GAPS",
        ):
            with self.subTest(outcome=outcome):
                self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 COMPLETE", outcome,
                                  "MIGRATION STOPPED")
                self.assert_refuses("migration stopped follows the final outcome")

    def test_fix_h1_later_approval_starts_a_new_run_after_outcome(self):
        original_fingerprint = self.specification["plan_fingerprint"]
        self.specification["plan_version"] = "2"
        self.write_plan()
        self.write_mapping()
        revised = "PLAN APPROVED v2"
        fingerprints = {APPROVAL: original_fingerprint, revised: self.specification["plan_fingerprint"]}
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 COMPLETE", ALL_GREEN,
                          revised, "PHASE 1 STARTED", fingerprints=fingerprints)
        text = self.map_text()
        self.assert_states(text, "Now", "Waiting")
        self.assertNotIn("All green", text)

    def validate_plan_map(self):
        plan = self.renderer.PlanEntries(self.plan.read_text(encoding="utf-8"))
        self.renderer.validate_map(self.specification, plan)

    def test_fix_h2_refuses_swapped_ranges_on_exact_rows(self):
        flow, records = (phase["files"][0] for phase in self.specification["phases"])
        records["from"][0]["exact"] = True
        self.write_plan()
        flow["from"], records["from"] = records["from"], flow["from"]
        with self.assertRaisesRegex(self.renderer.Fail, r"old-lines ranges.*src/flow\.py"):
            self.validate_plan_map()

    def test_fix_h2_refuses_partial_or_provisional_ranges_on_exact_rows(self):
        for cell in ("src/large.py: 1–10", "src/large.py: part of 1–12"):
            with self.subTest(cell=cell):
                self.write_plan(old_lines={"src/flow.py": cell})
                with self.assertRaisesRegex(self.renderer.Fail, r"old-lines.*src/flow\.py"):
                    self.validate_plan_map()

    def test_fix_h2_checks_mixed_links_against_plain_and_provisional_ranges(self):
        source = self.specification["sources"][0]
        source["parts"][1]["to"] = 18
        source["parts"].append({"id": "tail", "label": "Tail", "from": 19, "to": 20})
        flow, records = (phase["files"][0] for phase in self.specification["phases"])
        flow["from"].append({"part": "tail", "exact": True})
        records["from"].append({"part": "flow", "exact": True})
        for ranges, reason in (
            ("1–10, part of 13–18", "plain old-lines range"),
            ("1–12, 13–18", "part of old-lines range"),
            ("1–12, part of 10–12", "part of old-lines range"),
            ("1–12, part of 13–18, part of 19–20", "old-lines range has no linked part"),
        ):
            with self.subTest(ranges=ranges):
                self.write_plan(old_lines={records["path"]: "src/large.py: " + ranges})
                with self.assertRaisesRegex(self.renderer.Fail, reason):
                    self.validate_plan_map()
        self.write_plan(old_lines={records["path"]: "src/large.py: 1–12, part of 12–15"})
        self.validate_plan_map()

    def test_fix_h2_checks_ranges_from_two_sources(self):
        self.specification["sources"].append({"path": "src/previous.py", "lines": 9, "parts": [
            {"id": "previous", "label": "Previous", "from": 1, "to": 9},
        ]})
        flow = self.specification["phases"][0]["files"][0]
        flow["from"].append({"part": "previous", "exact": True})
        self.write_plan(old_lines={flow["path"]: "src/large.py: 1–12"})
        with self.assertRaisesRegex(self.renderer.Fail, "old-lines ranges"):
            self.validate_plan_map()
        self.write_plan(old_lines={flow["path"]: "src/large.py: 1–12; src/previous.py: 1-9"})
        self.validate_plan_map()

    def test_fix_h2_refuses_bad_format_unlisted_sources_and_out_of_bounds_lines(self):
        for cell, reason in (
            ("", "invalid old-lines format"),
            ("src/large.py:1–12", "invalid old-lines format"),
            ("src/large.py: 1—12", "invalid old-lines format"),
            ("src/large.py: 1–12;", "invalid old-lines format"),
            ("src/decoy.py.backup: 1–12", "unlisted source"),
            ("src/large.py: 0–12", "outside source"),
            ("src/large.py: 1–21", "outside source"),
            ("src/large.py: 13–12", "outside source"),
        ):
            with self.subTest(cell=cell):
                self.write_plan(old_lines={"src/flow.py": cell})
                with self.assertRaisesRegex(self.renderer.Fail, reason):
                    self.validate_plan_map()

    def test_fix_h2_merges_adjacent_ranges_without_closing_a_gap(self):
        flow = self.specification["phases"][0]["files"][0]
        flow["from"].append({"part": "record", "exact": True})
        self.write_plan(old_lines={flow["path"]: "src/large.py: 1–7, 9–20"})
        with self.assertRaisesRegex(self.renderer.Fail, "old-lines ranges"):
            self.validate_plan_map()
        self.write_plan(old_lines={flow["path"]: "src/large.py: 1–7, 8-20"})
        self.validate_plan_map()

    def map_kept_file(self):
        path = "src/edited.py"
        (self.project / path).write_bytes(b"# existing file\n")
        self.specification["phases"][0]["files"][0]["path"] = path
        return path

    def test_fix_j2_refuses_mapped_file_without_evidence_row(self):
        path = self.map_kept_file()
        self.write_plan(without_evidence=(path,))
        with self.assertRaisesRegex(self.renderer.Fail, r"evidence.*src/edited\.py|src/edited\.py.*evidence"):
            self.validate_plan_map()

    def test_fix_j2_renders_kept_file_with_valid_evidence_row(self):
        path = self.map_kept_file()
        self.write_plan(without_evidence=(path,))
        self.write_ledger(APPROVAL)
        self.write_mapping()
        self.assert_refuses("mapped file is missing a plan evidence row: " + path)

        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()
        self.assertIn(path, self.phase_card(self.map_text(), 1))

    def test_fix_h3_recovers_after_bad_theme_at_approval(self):
        theme = self.home / ".vibe-to-engineering" / "map-theme.css"
        theme.parent.mkdir()
        theme.write_text("</style>", encoding="utf-8")
        code, output, pdf = self.run_map()
        self.assertEqual(code, 1, output)
        self.assertIn("theme", output)
        pdf.assert_not_called()
        recorded_before_phase = self.approved_copy().is_file()
        theme.write_text(":root {}", encoding="utf-8")
        self.write_ledger(APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE")
        self.assert_states(self.map_text(), "Done", "Waiting")
        self.assertTrue(recorded_before_phase)

    def test_fix_h3_first_render_after_phase_one_saves_current_approval(self):
        self.write_ledger(APPROVAL, "PHASE 1 STARTED", "PHASE 1 COMPLETE")
        (self.project / "src" / "large.py").write_text("# already split\n", encoding="utf-8")
        (self.project / "src" / "flow.py").write_text("# moved flow\n", encoding="utf-8")
        text = self.map_text()
        self.assert_states(text, "Done", "Waiting")
        self.assertIn("Actual: 1", self.phase_card(text, 1))
        self.assertEqual(json.loads(self.approved_copy().read_bytes()), self.specification)

    def test_fix_h3_ignores_leftover_temporary_approval_file(self):
        stale = self.state / (".v2e-approved-" + "a" * 32 + ".tmp")
        stale.write_bytes(b'{"plan_version":')
        with mock.patch.object(os, "link", wraps=os.link) as publish:
            self.map_text()
        publish.assert_called_once()
        self.assertFalse(stale.exists())
        self.assertEqual(self.approved_copy().stat().st_nlink, 1)

    def test_fix_j3_recovers_approved_copy_after_two_link_hard_stop(self):
        self.seed_approved_copy()
        archive = self.approved_copy()
        stale = self.state / (".v2e-approved-" + "b" * 32 + ".tmp")
        os.link(archive, stale)
        self.assertEqual(archive.stat().st_nlink, 2)

        self.assert_states(self.map_text(), "Waiting", "Waiting")
        self.assertFalse(stale.exists())
        self.assertEqual(archive.stat().st_nlink, 1)
        self.assertEqual(json.loads(archive.read_bytes()), self.specification)

    def test_fix_j3_preserves_look_alike_names_and_nonregular_entries(self):
        for name in (
            ".v2e-approved-abandoned.tmp",
            ".v2e-approved-" + "A" * 32 + ".tmp",
            ".v2e-approved-" + "a" * 31 + ".tmp",
            ".v2e-approved-" + "a" * 32 + ".tmp.keep",
        ):
            (self.state / name).write_bytes(b"keep this file")
        (self.state / (".v2e-approved-" + "c" * 32 + ".tmp")).mkdir()
        linked = self.state / (".v2e-approved-" + "d" * 32 + ".tmp")
        with self.fixture_link(linked, self.mapping):
            before = self.snapshot_state()
            stale = self.state / (".v2e-approved-" + "e" * 32 + ".tmp")
            stale.write_bytes(b"remove this file")
            self.map_text()
            after = self.snapshot_state()
            outputs = {self.html.name, self.pdf.name, self.approved_copy().name}
            self.assertEqual({name: details for name, details in after.items() if name not in outputs}, before)

    def test_fix_h3_failure_before_publish_never_exposes_the_final_copy(self):
        visible_at_fsync = []

        def failed_sync(_fd):
            visible_at_fsync.append(self.approved_copy().exists())
            raise OSError("simulated fsync failure")

        with mock.patch.object(os, "fsync", side_effect=failed_sync):
            self.assert_refuses("simulated fsync failure")
        self.assertEqual(visible_at_fsync, [False])
        self.assertFalse(self.approved_copy().exists())
        self.map_text()
        self.assertEqual(json.loads(self.approved_copy().read_bytes()), self.specification)

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
        self.seed_approved_copy()
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
        self.seed_approved_copy()
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE", "PHASE 2 FAILED", "MIGRATION STOPPED")
        text = self.map_text()
        self.assertRegex(text, r">[^<>]*\bStopped\b[^<>]*<")
        self.assert_states(text, "Done", "Failed")

    def test_completed_phase_displays_actual_lines_with_planned_range(self):
        self.seed_approved_copy()
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
        self.seed_approved_copy()
        planned = self.project / path
        planned.parent.mkdir()
        planned.write_text("# first\n# second\n", encoding="utf-8")
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE")
        card = self.phase_card(self.map_text(), 1).replace("<br>", "")
        self.assertIn(path, card)
        self.assertIn("Actual: 2", card)

    def test_completed_missing_linked_and_nonregular_files_are_missing(self):
        self.seed_approved_copy()
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
        short_hostile_label = "<script>x</script>"
        self.specification["project"] = hostile
        self.specification["sources"][0]["parts"][0]["label"] = short_hostile_label
        self.specification["phases"][0]["title"] = hostile
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()
        text = self.map_text()
        self.assertNotIn(hostile, text)
        self.assertGreaterEqual(text.replace("<br>", "").count(escape(hostile)), 2)
        self.assertNotIn(short_hostile_label, text)
        self.assertIn(f"<b>{escape(short_hostile_label)}</b>", text)
        self.assertEqual(self.renderer.render_pdf.static_problems(text), [])

    def test_hostile_theme_markup_is_refused_before_pdf_rendering(self):
        theme = self.home / ".vibe-to-engineering" / "map-theme.css"
        theme.parent.mkdir()
        theme.write_text('</style><img src="https://example.invalid/fixture.png">', encoding="utf-8")
        self.assert_refuses("theme", saves_approval=True)

    def test_theme_css_must_pass_the_existing_pdf_checks(self):
        theme = self.home / ".vibe-to-engineering" / "map-theme.css"
        theme.parent.mkdir()
        theme.write_text('@import "https://example.invalid/theme.css";', encoding="utf-8")
        self.seed_approved_copy()
        before = self.snapshot_state()
        real_pdf = self.renderer.render_pdf.main
        with mock.patch.object(self.renderer.render_pdf, "require_supported_platform"), \
                mock.patch.object(self.renderer.render_pdf, "find_browser") as browser:
            code, output, _ = self.run_map(renderer=real_pdf)
        self.assertNotEqual(code, 0, output)
        self.assertEqual(self.snapshot_state(), before)
        browser.assert_not_called()

    def test_pdf_failure_preserves_both_previous_outputs(self):
        self.seed_approved_copy()
        self.html.write_bytes(b"previous HTML")
        self.pdf.write_bytes(PDF_FIXTURE)
        before = self.snapshot_state()
        code, output, render = self.run_map(renderer=lambda argv: 1)
        self.assertNotEqual(code, 0, output)
        render.assert_called_once()
        self.assertEqual(self.snapshot_state(), before)

    def test_many_small_source_parts_do_not_add_pages(self):
        source = self.specification["sources"][0]
        source["lines"] = 100
        source["parts"] = [{"id": "flow", "label": "Flow", "from": 1, "to": 67}] + [
            {"id": f"part-{line}", "label": f"Slice {line}", "from": line, "to": line}
            for line in range(68, 101)
        ]
        (self.project / source["path"]).write_bytes(b"# original\n" * 100)
        first, second = self.specification["phases"]
        first["files"][0]["from"] = [{"part": p["id"], "exact": True} for p in source["parts"][:17]]
        second["files"][0]["from"] = [{"part": p["id"], "exact": True} for p in source["parts"][17:]]
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        text = self.map_text()
        self.assertEqual(len(re.findall(r'<section class="sheet\b', text)), 1)
        self.assertEqual(text.count('class="segment '), 34)
        self.assertEqual(text.count('class="source-label '), 1)
        self.assertIn("<b>Flow</b>", text)
        payload = re.search(r'data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)', text)[1]
        paths = ElementTree.fromstring(base64.b64decode(payload, validate=True))
        self.assertEqual(len(paths), 34)
        # File positions are relative to the inside of the card's one-pixel border.
        for number, links in ((1, paths[:17]), (2, paths[17:])):
            card_top = int(re.search(r'id="phase-%d"[^>]+top:(\d+)px' % number, text)[1])
            row = re.search(r'class="file"[^>]+top:(\d+)px;height:(\d+)px', self.phase_card(text, number))
            row_center = card_top + 1 + int(row[1]) + int(row[2]) / 2
            self.assertTrue(all(float(path.attrib["d"].rsplit(" ", 1)[-1]) == row_center for path in links))

    def test_file_rows_display_their_linked_ranges_and_exactness(self):
        first, second = self.specification["phases"]
        first["files"][0]["from"].append({"part": "record", "exact": False})
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        text = self.map_text()
        self.assertIn('class="file-evidence">1–12, part of 13–20<', self.phase_card(text, first["number"]))
        self.assertIn('class="file-evidence">part of 13–20<', self.phase_card(text, second["number"]))

    def test_many_source_headings_leave_room_for_positive_bar_segments(self):
        phase = self.specification["phases"][0]
        phase["files"] = []
        self.specification.update(sources=[], phases=[phase])
        for index in range(20):
            path = f"src/original/substantial-component/source-{index:02d}.py"
            part = f"part-{index}"
            count = 10 + index
            self.specification["sources"].append({"path": path, "lines": count, "parts": [
                {"id": part, "label": "Whole file", "from": 1, "to": count},
            ]})
            parent = self.project / path
            parent.parent.mkdir(parents=True, exist_ok=True)
            parent.write_bytes(b"# original\n" * count)
            phase["files"].append({"path": f"src/target-{index:02d}.py", "lines_low": count, "lines_high": count,
                                   "from": [{"part": part, "exact": True}]})
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        text = self.map_text()
        self.assertIn("Page 1 of 1", text)
        self.assertNotIn("@page extended-", text)
        self.assertEqual(text.count('class="source-range" title='), 20)
        heights = re.findall(r'class="segment [^"]+" style="[^"]+height:([-\d.]+)px', text)
        self.assertEqual(len(heights), 20)
        self.assertTrue(all(float(height) > 0 for height in heights))

    def test_filenames_stay_whole_and_shared_folders_appear_once_per_phase(self):
        first = self.specification["phases"][0]
        name = "AnUnbrokenFileNameThatNeedsTheFullWidthOfTheRow.tsx"
        first["files"][0]["path"] = "src/shared-folder/" + name
        first["files"].append(dict(first["files"][0], path="src/shared-folder/Second.tsx"))
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        card = self.phase_card(self.map_text(), 1)
        self.assertIn(f">{name}</", card)
        self.assertIn(">Second.tsx</", card)
        self.assertEqual(card.count(">src/shared-folder/</"), 1)

    def test_mixed_folders_are_shown_on_their_rows_and_wrap_after_slashes(self):
        first = self.specification["phases"][0]
        parent = "src/specific-eligibility/assessment-implementation/external-result/"
        first["files"][0]["path"] = parent + "First.tsx"
        first["files"].append(dict(first["files"][0], path="packages/reader/Second.tsx"))
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        card = self.phase_card(self.map_text(), 1)
        folders = re.findall(r'class="file-folder">(.*?)</', card)
        self.assertEqual([folder.replace("<br>", "") for folder in folders], [parent, "packages/reader/"])
        self.assertIn("/<br>", folders[0])
        self.assertEqual(folders[0].count("<br>"), folders[0].count("/<br>"))
        self.assertIn(">First.tsx</", card)
        self.assertIn(">Second.tsx</", card)

    def test_equal_estimates_and_line_counts_use_compact_number_format(self):
        source = self.specification["sources"][0]
        source["lines"] = source["parts"][1]["to"] = 3691
        (self.project / source["path"]).write_bytes(b"# original\n" * 3691)
        first, second = self.specification["phases"]
        first["files"][0].update(lines_low=1381, lines_high=1381)
        second["files"][0].update(lines_low=1240, lines_high=1600)
        self.write_plan()
        self.write_ledger(APPROVAL, "PHASE 1 COMPLETE")
        self.write_mapping()
        self.seed_approved_copy()
        (self.project / first["files"][0]["path"]).write_bytes(b"# extracted\n" * 1234)

        text = self.map_text()
        self.assertIn("3,691 lines today", text)
        self.assertIn("~1,381<br>Actual: 1,234", self.phase_card(text, 1))
        self.assertIn("1,240–1,600", self.phase_card(text, 2))

    def test_no_source_page_uses_a_short_message_in_the_source_column(self):
        self.specification["sources"] = []
        for phase in self.specification["phases"]:
            phase["files"][0]["from"] = []
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        text = self.map_text()
        self.assertIn('<p class="source empty">No source ranges.</p>', text)
        self.assertNotIn('class="segment ', text)
        self.assertIn("Page 1 of 1", text)

    def test_long_map_breaks_between_phases_and_keeps_every_file(self):
        for phase in self.specification["phases"]:
            prototype = phase["files"][0]
            phase["files"] = [dict(prototype, path="src/chunk-%d-%02d.py" % (phase["number"], index))
                              for index in range(20)]
        self.write_plan()
        self.write_ledger(APPROVAL)
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

    def test_oversized_phase_continues_on_a4_with_only_page_local_source_parts(self):
        if not os.environ.get("V2E_BROWSER"):
            if os.environ.get("V2E_REQUIRE_MATRIX"):
                self.fail("native validation requires the pinned V2E_BROWSER")
            self.skipTest("set V2E_BROWSER to a native Chrome-family browser")
        first, second = self.specification["phases"]
        prototype = first["files"][0]
        first["files"][0] = dict(prototype, path="src/check.py", **{"from": []})
        second["files"] = [dict(prototype, path=f"src/chunk-{index:02d}.py") for index in range(30)]
        second["files"].append(dict(second["files"][-1], path="src/final.py",
                                    **{"from": [{"part": "record", "exact": False}]}))
        self.write_plan()
        self.write_ledger(APPROVAL)
        self.write_mapping()

        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--project", str(self.project)],
                                env=env, capture_output=True, text=True, timeout=195)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pdf = self.pdf.read_bytes()
        boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
        self.assertEqual(len(boxes), 3)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page(?!s)\b", pdf)), 3)
        for width, height in boxes:
            self.assertAlmostEqual(float(width), 595, delta=1)
            self.assertAlmostEqual(float(height), 842, delta=1)

        first_page, second_page, third_page, _ = self.html.read_text(encoding="utf-8").split("</section>")
        self.assertIn("No source ranges.", first_page)
        self.assertNotIn('class="segment ', first_page)
        self.assertIn("Move records", second_page)
        self.assertIn("Move records", third_page)
        self.assertIn("20 lines today", second_page)
        self.assertIn("20 lines today", third_page)
        self.assertEqual(second_page.count('class="segment '), 1)
        self.assertEqual(third_page.count('class="segment '), 2)
        self.assertNotIn("part of 13–20", second_page)
        self.assertIn("part of 13–20", third_page)
        for file in second["files"]:
            self.assertEqual((second_page + third_page).count(">" + file["path"].split("/")[-1] + "</"), 1)


if __name__ == "__main__":
    unittest.main()
