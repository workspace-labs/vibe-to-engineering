"""A completed check cannot redirect the wrapper's evidence into another directory."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills/vibe-to-engineering/scripts/evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence
import childenv
import emission


@unittest.skipUnless(sys.platform == "darwin", "native evidence execution is macOS-only")
class EvidenceDestination(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="v2e-destination-")).resolve()
        self.project = self.root / "project"
        self.state = self.project / ".vibe-to-engineering"
        self.folder = self.state / "evidence"
        self.folder.mkdir(parents=True)
        self.home = self.root / "home"
        self.home.mkdir()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.output = self.folder / "check.txt"
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)})
        self.env.start()
        self.base = mock.patch.object(childenv, "SCRATCH_BASE", str(self.scratch))
        self.base.start()
        evidence.enroll_runner("/bin/sh", ask=lambda _: evidence.APPROVAL, out=io.StringIO())

    def tearDown(self):
        self.base.stop()
        self.env.stop()
        shutil.rmtree(self.root)

    def run_check(self, script, *args):
        printed, report = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(report):
            code = evidence.main(["--project", str(self.project), "--out", str(self.output),
                                  "--", "/bin/sh", "-c", script, "fixture", *map(str, args)])
        return code, printed.getvalue(), report.getvalue(), emission.read_result(report.getvalue())

    def assert_integrity(self, result, child=0):
        code, printed, report, record = result
        self.assertEqual(code, 3, report)
        self.assertEqual(record, dict(v=1, wrapper=3, launched=True, saved=False, child={"exit": child}))
        self.assertEqual(printed, "")

    def test_preexisting_nonregular_output_is_refused_before_the_check(self):
        for kind in ("directory", "fifo"):
            with self.subTest(kind=kind):
                self.output = self.folder / kind
                self.output.mkdir() if kind == "directory" else os.mkfifo(self.output)
                before = self.output.lstat()
                code, printed, report, record = self.run_check("printf ran > check-ran; printf synthetic")
                self.assertEqual(code, 2, report)
                self.assertEqual(record, dict(v=1, wrapper=2, launched=False, saved=False, child=None))
                self.assertEqual(printed, "")
                self.assertFalse((self.project / "check-ran").exists())
                after = self.output.lstat()
                self.assertEqual((after.st_dev, after.st_ino, after.st_mode),
                                 (before.st_dev, before.st_ino, before.st_mode))

    def test_swapped_evidence_parent_cannot_overwrite_an_outside_file(self):
        sentinel = self.outside / self.output.name
        sentinel.write_text("outside sentinel")
        result = self.run_check('mv .vibe-to-engineering/evidence .vibe-to-engineering/old; '
                                'ln -s "$1" .vibe-to-engineering/evidence; printf synthetic; exit 7', self.outside)
        self.assert_integrity(result, child=7)
        self.assertEqual(sentinel.read_text(), "outside sentinel")

    def test_swapped_state_parent_cannot_write_outside(self):
        (self.outside / "evidence").mkdir()
        result = self.run_check('mv .vibe-to-engineering .vibe-original; '
                                'ln -s "$1" .vibe-to-engineering; printf synthetic', self.outside)
        self.assert_integrity(result)
        self.assertFalse((self.outside / "evidence/check.txt").exists())

    def test_link_to_another_in_tree_directory_is_still_a_changed_parent(self):
        target = self.state / "other"
        target.mkdir()
        result = self.run_check('mv .vibe-to-engineering/evidence .vibe-to-engineering/old; '
                                'ln -s other .vibe-to-engineering/evidence; printf synthetic')
        self.assert_integrity(result)
        self.assertFalse((target / self.output.name).exists())

    def test_replaced_regular_parent_is_refused(self):
        result = self.run_check('mv .vibe-to-engineering/evidence .vibe-to-engineering/old; '
                                'mkdir .vibe-to-engineering/evidence; printf synthetic')
        self.assert_integrity(result)
        self.assertFalse(self.output.exists())

    def test_new_output_ancestor_cannot_become_a_link(self):
        self.output = self.folder / "new/check.txt"
        result = self.run_check('ln -s "$1" .vibe-to-engineering/evidence/new; printf synthetic', self.outside)
        self.assert_integrity(result)
        self.assertFalse((self.outside / "check.txt").exists())

    def test_ordinary_nested_missing_directories_are_created(self):
        self.output = self.folder / "phase/checks/check.txt"
        code, printed, report, record = self.run_check("printf synthetic")
        self.assertEqual(code, 0, report)
        self.assertEqual(record, dict(v=1, wrapper=0, launched=True, saved=True, child={"exit": 0}))
        self.assertEqual(self.output.read_text(), printed)
        self.assertIn("synthetic", printed)

    def test_ordinary_existing_evidence_is_replaced(self):
        self.output.write_text("old evidence")
        code, printed, report, record = self.run_check("printf synthetic")
        self.assertEqual(code, 0, report)
        self.assertTrue(record["saved"])
        self.assertEqual(self.output.read_text(), printed)
        self.assertNotIn("old evidence", printed)

    def test_missing_evidence_directory_is_created_under_existing_state(self):
        self.folder.rename(self.state / "prior-evidence")
        code, printed, report, record = self.run_check("printf synthetic")
        self.assertEqual(code, 0, report)
        self.assertTrue(record["saved"])
        self.assertEqual(self.output.read_text(), printed)

    def test_temporary_name_collision_never_deletes_an_unowned_file(self):
        sentinel = self.folder / ".v2e-evidence-collision"
        sentinel.write_text("unowned sentinel")
        with mock.patch("evidencefile.secrets.token_hex", return_value="collision"):
            code, printed, report, record = self.run_check("printf synthetic")
        self.assertEqual(code, 1, report)
        self.assertEqual(record, dict(v=1, wrapper=1, launched=True, saved=False, child={"exit": 0}))
        self.assertEqual(sentinel.read_text(), "unowned sentinel")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
