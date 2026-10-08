"""A3 retention and governed-path regression tests over disposable, synthetic fixtures.

Runner identity and subprocess results are fixtures: no real runner is enrolled or executed. On Windows
the permission-success cases supply a POSIX mode in lstat; native mode enforcement remains a macOS gate.
The tests themselves remove only their TemporaryDirectory after retention assertions have completed.
"""

import contextlib
import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/vibe-to-engineering/scripts"))
import childenv
import emission
import evidence


class ScratchRetention(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory(prefix="v2e-retention-test-")
        self.addCleanup(self.fixture.cleanup)
        self.tmp = Path(self.fixture.name).resolve()
        self.base = self.tmp / "scratch"
        self.base.mkdir()
        self.project = self.tmp / "project"
        (self.project / ".vibe-to-engineering/evidence").mkdir(parents=True)
        self.outfile = self.project / ".vibe-to-engineering/evidence/check.txt"
        self.registry = self.tmp / "unused-registry.json"
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        for patch in (
                mock.patch.object(childenv, "SCRATCH_BASE", str(self.base)),
                mock.patch.object(childenv, "_ROOTS", {}),
                mock.patch.object(childenv, "WINDOWS", False),
                mock.patch.object(childenv, "require_supported_platform"),
                mock.patch.object(evidence, "require_supported_platform"),
                mock.patch.object(evidence, "registry_path", return_value=str(self.registry)),
                mock.patch.object(evidence, "load_registry", side_effect=AssertionError("registry read"))):
            self.stack.enter_context(patch)
        self.native_lstat = os.lstat
        if os.name == "nt":
            def private_lstat(path, *args, **kwargs):
                info = self.native_lstat(path, *args, **kwargs)
                if str(path) in childenv._ROOTS:
                    return os.stat_result((stat.S_IFDIR | 0o700,) + tuple(info)[1:])
                return info
            self.stack.enter_context(mock.patch.object(childenv.os, "lstat", side_effect=private_lstat))

    def root(self):
        root = childenv.scratch_root()
        (root / "home/data.txt").write_text("scratch-synthetic-data", encoding="utf-8")
        return root

    def test_original_and_foreign_contents_are_retained_without_any_delete(self):
        root = self.root()
        foreign = self.tmp / "foreign.txt"
        foreign.write_text("foreign-sentinel", encoding="utf-8")
        foreign.rename(root / "foreign.txt")
        neighbor = self.base / "neighbor.txt"
        neighbor.write_text("neighbor-sentinel", encoding="utf-8")
        with mock.patch.object(childenv.os, "unlink", side_effect=AssertionError("unlink")), \
                mock.patch.object(childenv.os, "rmdir", side_effect=AssertionError("rmdir")), \
                mock.patch.object(childenv.os, "chmod", side_effect=AssertionError("chmod")):
            childenv.cleanup(root)
        self.assertEqual((root / "foreign.txt").read_text(), "foreign-sentinel")
        self.assertEqual((root / "home/data.txt").read_text(), "scratch-synthetic-data")
        self.assertEqual(neighbor.read_text(), "neighbor-sentinel")
        self.assertTrue((root / "tmp").is_dir())
        if os.name != "nt":
            for folder in (root, root / "home", root / "tmp"):
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_replacement_and_moved_roots_are_both_left_untouched(self):
        root = self.root()
        moved = self.tmp / "moved"
        root.rename(moved)
        root.mkdir()
        (root / "foreign.txt").write_text("replacement-sentinel")
        with self.assertRaisesRegex(evidence.Fail, "did not make"):
            childenv.cleanup(root)
        self.assertEqual((root / "foreign.txt").read_text(), "replacement-sentinel")
        self.assertEqual((moved / "home/data.txt").read_text(), "scratch-synthetic-data")

    def test_missing_root_and_changed_mode_are_integrity_failures_without_repairs(self):
        root = self.root()
        info = self.native_lstat(root)
        exposed = os.stat_result((stat.S_IFDIR | 0o755,) + tuple(info)[1:])
        with mock.patch.object(childenv.os, "lstat", return_value=exposed), \
                mock.patch.object(childenv.os, "chmod", side_effect=AssertionError("chmod")):
            with self.assertRaisesRegex(evidence.Fail, "no longer private"):
                childenv.cleanup(root)
        moved = self.tmp / "moved"
        root.rename(moved)
        with self.assertRaisesRegex(evidence.Fail, "no longer at its path"):
            childenv.cleanup(root)
        self.assertEqual((moved / "home/data.txt").read_text(), "scratch-synthetic-data")

    def invoke(self, exitcode=0, failure=None, secret=None, alter=None):
        self.roots = []

        def check(command, **kwargs):
            root = Path(kwargs["env"]["HOME"]).parent
            self.roots.append(root)
            (root / "tmp/output.txt").write_text("retained-check-data", encoding="utf-8")
            if failure == "spawn":
                raise OSError(13, "synthetic spawn failure")
            if alter:
                alter(root)
            return subprocess.CompletedProcess(command, exitcode, b"checked synthetic fixture\n")

        out, err = io.StringIO(), io.StringIO()
        self.captured_stdout, self.captured_stderr = out, err
        identity = ("unused-enrolled-runner", {
            "path": "unused-enrolled-runner", "sha256": "a" * 64, "pin": "copy"})
        argv = ["--project", str(self.project), "--out", str(self.outfile)]
        if secret:
            argv += ["--env", "TOKEN=" + secret]
        argv += ["--", "python3", "synthetic.py"]
        with contextlib.ExitStack() as stack:
            for patch in (
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err),
                    mock.patch.object(evidence, "supported_runner", return_value=("unused", "python")),
                    mock.patch.object(evidence, "enrolled_identity", return_value=identity),
                    mock.patch.object(evidence, "secret_values", return_value=[]),
                    mock.patch.object(evidence.subprocess, "run", side_effect=check)):
                stack.enter_context(patch)
            if failure == "refusal":
                stack.enter_context(mock.patch.object(evidence, "supported_runner", return_value=(None, None)))
            elif failure == "write":
                stack.enter_context(mock.patch.object(evidence, "write_lf", side_effect=OSError("write failed")))
            code = evidence.main(argv)
        report = err.getvalue()
        return code, out.getvalue(), report, emission.read_result(report)

    def test_success_and_child_failure_keep_scratch_and_record_the_path(self):
        for exitcode in (0, 2):
            with self.subTest(exitcode=exitcode):
                code, printed, report, result = self.invoke(exitcode=exitcode)
                root = self.roots[0]
                self.assertEqual(code, 0)
                self.assertEqual(result["child"], {"exit": exitcode})
                self.assertEqual(self.outfile.read_text(encoding="utf-8"), printed)
                self.assertIn(str(root), printed)
                self.assertIn(str(root), report)
                self.assertIn("may contain sensitive output", printed)
                self.assertEqual((root / "tmp/output.txt").read_text(), "retained-check-data")
                self.assertNotIn(self.project, root.parents)
                self.assertFalse(self.registry.exists())

    def test_refusal_spawn_and_write_failures_keep_allocated_roots(self):
        for failure, expected, launched in (("refusal", 2, False), ("spawn", 1, False), ("write", 1, True)):
            with self.subTest(failure=failure):
                before = set(self.base.iterdir())
                code, _, report, result = self.invoke(failure=failure)
                allocated = set(self.base.iterdir()) - before
                self.assertEqual(code, expected)
                self.assertEqual(result["launched"], launched)
                self.assertFalse(result["saved"])
                self.assertEqual(len(allocated), 1)
                self.assertIn(str(allocated.pop()), report)
                self.assertIn("deletion remains the human's act", report)

    def test_postlaunch_replacement_preserves_result_and_foreign_sentinel(self):
        def replace(root):
            root.rename(self.tmp / "moved-check-root")
            root.mkdir()
            (root / "foreign.txt").write_text("foreign-after-check")
        code, _, report, result = self.invoke(alter=replace)
        self.assertEqual(code, 3)
        self.assertTrue(result["launched"])
        self.assertTrue(result["saved"])
        self.assertEqual(result["child"], {"exit": 0})
        self.assertIn("integrity failure", report)
        self.assertEqual((self.roots[0] / "foreign.txt").read_text(), "foreign-after-check")
        self.assertEqual((self.tmp / "moved-check-root/tmp/output.txt").read_text(), "retained-check-data")

    def test_new_path_and_warning_text_still_obey_complete_emission_masking(self):
        for secret in (self.tmp.name, "scratch", "2"):
            with self.subTest(secret=secret):
                code, printed, report, result = self.invoke(exitcode=2, secret=secret)
                self.assertEqual(code, 0)
                self.assertEqual(result["child"], {"exit": 2})
                self.assertNotIn(secret, printed)
                self.assertNotIn(secret, report)
                self.assertNotIn(secret, self.outfile.read_text(encoding="utf-8"))
                self.assertTrue((self.roots[0] / "tmp/output.txt").exists())

    def test_partial_scratch_preparation_is_retained_and_reported(self):
        mkdir = Path.mkdir

        def fail_home(folder, *args, **kwargs):
            if folder.name == "home":
                raise OSError("synthetic preparation failure")
            return mkdir(folder, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", fail_home):
            code, _, report, result = self.invoke()
        roots = list(self.base.iterdir())
        self.assertEqual(code, 1)
        self.assertFalse(result["launched"])
        self.assertEqual(len(roots), 1)
        self.assertIn(str(roots[0]), report)
        self.assertTrue(roots[0].is_dir())

    def test_project_containing_scratch_base_refuses_before_allocation(self):
        (self.tmp / ".vibe-to-engineering/evidence").mkdir(parents=True)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(childenv, "construct", side_effect=AssertionError("allocated")):
            code = evidence.main(["--project", str(self.tmp), "--out",
                                  str(self.tmp / ".vibe-to-engineering/evidence/check.txt"), "--", "python3"])
        self.assertEqual(code, 2)
        self.assertIn("outside the project", err.getvalue())
        self.assertEqual(list(self.base.iterdir()), [])

    def test_enrollment_probe_scratch_is_retained_on_success_and_refusal(self):
        for refusal in (False, True):
            with self.subTest(refusal=refusal), contextlib.ExitStack() as stack:
                for patch in (
                        mock.patch.object(evidence, "resolve_candidate", return_value=("fixture-python3", "python")),
                        mock.patch.object(evidence, "hashed", return_value=("a" * 64, 123)),
                        mock.patch.object(evidence, "location_pin", return_value="path"),
                        mock.patch.object(evidence, "load_registry", return_value={"version": 1, "runners": {}},
                                          side_effect=None)):
                    stack.enter_context(patch)

                def probe(_runner, _kind, _env, scratch):
                    (scratch / "tmp/probe.txt").write_text("synthetic-probe-data")
                    if refusal:
                        raise evidence.Fail("synthetic probe refusal")

                stack.enter_context(mock.patch.object(evidence, "probe", side_effect=probe))
                before = set(self.base.iterdir())
                shown = io.StringIO()
                if refusal:
                    with self.assertRaisesRegex(evidence.Fail, "synthetic probe refusal"):
                        evidence.enroll_runner("fixture-python3", ask=lambda _: "enroll", out=shown)
                else:
                    evidence.enroll_runner("fixture-python3", ask=lambda _: "enroll", out=shown)
                allocated = set(self.base.iterdir()) - before
                self.assertEqual(len(allocated), 1)
                root = allocated.pop()
                self.assertEqual((root / "tmp/probe.txt").read_text(), "synthetic-probe-data")
                self.assertIn(str(root), shown.getvalue())
                self.assertIn("may contain sensitive output", shown.getvalue())

    def test_interruption_discloses_retained_scratch_without_inventing_result_facts(self):
        def interrupt(_root):
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            self.invoke(alter=interrupt, secret=self.tmp.name)
        report = self.captured_stderr.getvalue()
        self.assertIn(self.roots[0].name, report)
        self.assertIn("may contain sensitive output", report)
        self.assertNotIn(self.tmp.name, report)
        self.assertEqual(self.captured_stdout.getvalue(), "")
        self.assertTrue((self.roots[0] / "tmp/output.txt").exists())
        self.assertFalse(self.outfile.exists())
        with self.assertRaises(ValueError):
            emission.read_result(report)


if __name__ == "__main__":
    unittest.main()
