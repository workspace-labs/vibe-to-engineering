"""The R2-F6 full status matrix (owner decision 5.3; release handoff, checklist B's class battery): the
wrapper's exit status is its own namespace, exercised over every transition —

  0  the check ran and the required evidence was produced (the check's own outcome — exit code or
     signal — is recorded as data; 0 never says the check passed)
  1  a wrapper operational failure: the validated launch itself failed, or the evidence could not be
     written (the check ran but its evidence was not saved)
  2  a pre-launch refusal: nothing ran and this attempt produced no check evidence
  3  a post-launch integrity failure: the check ran, but the scratch root could not be confirmed and
     safely removed — never reportable as a pre-launch refusal

The pre-launch refusal and operational-failure rows also pass on the pre-slice candidate (their behavior
is preserved); the post-launch rows fail on it (a post-launch failure came back as exit 2, and a child's
own code or signal leaked into the wrapper's status). Run from the repository root:
  python3 -m unittest discover -s tests -p test_r2_status.py -v
"""

import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import evidence  # noqa: E402

PY = os.path.realpath(sys.executable)


class StatusMatrix(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-r2m-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def enroll(self, home):
        enroll = getattr(evidence, "enroll_runner", None)
        if enroll is None:
            return None
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                enroll(PY, ask=lambda prompt: evidence.APPROVAL, out=quiet)
        return True

    def project(self, name, body):
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + body)
        home = self.tmp / ("home-%d" % self.count)
        home.mkdir()
        self.enroll(home)
        return project, home

    def run_tool(self, project, command, home, extra=(), out="check.txt"):
        out = project / ".vibe-to-engineering" / "evidence" / out
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                              + list(extra) + ["--"] + list(command), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def in_process(self, argv, home, patch=None):
        """The tool inside this process with one of its steps patched — to force a failure at an exact
        boundary (the launch, the moment after the launch, the cleanup)."""
        spec = importlib.util.spec_from_file_location("evidence_status_under_test", str(TOOL))
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {"HOME": str(home)}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            if patch is None:
                code = tool.main(argv)
            else:
                with patch(tool):
                    code = tool.main(argv)
        return code, out.getvalue(), err.getvalue()

    # ---------------------------------------------------- 0: ran + evidence, the child's outcome as data

    def test_every_child_exit_code_is_data_under_wrapper_zero(self):
        for outcome in (0, 1, 2, 3, 7):
            with self.subTest("the check exits %d" % outcome):
                project, home = self.project("exit %d" % outcome,
                                             "import sys\nprint('done-7841')\nsys.exit(%d)\n" % outcome)
                code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                                  home)
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                self.assertIsNotNone(saved)
                self.assertIn("done-7841", saved)
                self.assertIn("the check exited %d" % outcome, report)

    def test_signal_termination_is_recorded_accurately(self):
        for name, signal, number in (("SIGTERM", "SIGTERM", 15), ("SIGKILL", "SIGKILL", 9)):
            with self.subTest(name):
                project, home = self.project(name, "import os, signal\nprint('before-7842', flush=True)\n"
                                                   "os.kill(os.getpid(), signal.%s)\n" % signal)
                code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                                  home)
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                self.assertIsNotNone(saved)
                self.assertIn("before-7842", saved)
                self.assertIn("terminated by signal %d (%s)" % (number, name), report)

    # ---------------------------------------------------- 2: pre-launch refusals (preserved behavior)

    def test_prelaunch_refusals_run_nothing_and_leave_no_evidence(self):
        with self.subTest("a prohibited --env name"):
            project, home = self.project("prohibited", "print('never-7843')\n")
            code, printed, saved, report, ran = self.run_tool(
                project, [sys.executable, "-B", "check.py"], home, extra=["--env", "BASH_ENV=x-7843"])
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
        with self.subTest("a runner outside the supported set"):
            project, home = self.project("unsupported", "print('never-7844')\n")
            code, printed, saved, report, ran = self.run_tool(project, ["/bin/ls", "check.py"], home)
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
            self.assertIn("supported set", report)
        with self.subTest("a runner this user never enrolled"):
            if getattr(evidence, "enroll_runner", None) is None:
                self.skipTest("this candidate predates enrollment — the post-A2 baseline proves this row")
            project = self.tmp / "unenrolled-project"
            (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
            (project / "check.py").write_text("print('never-7845')\n")
            home = self.tmp / "unenrolled-home"   # no enrollment at all
            home.mkdir()
            code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                              home)
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
            self.assertIn("enrolled", report)
        with self.subTest("a refused --with-path folder"):
            project, home = self.project("bad path", "print('never-7846')\n")
            code, printed, saved, report, ran = self.run_tool(
                project, [sys.executable, "-B", "check.py"], home, extra=["--with-path", "relative/dir"])
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)

    # ---------------------------------------------------- 1: wrapper operational failures

    def test_a_launch_that_cannot_start_is_an_operational_failure(self):
        project, home = self.project("spawn", "print('never-7847')\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"

        def broken(tool):
            return mock.patch.object(tool.subprocess, "run",
                                     side_effect=OSError(13, "Permission denied"))

        code, printed, report = self.in_process(
            ["--project", str(project), "--out", str(out), "--", sys.executable, "-B", "check.py"],
            home, broken)
        self.assertEqual(code, 1, report)              # the wrapper could not run the validated launch
        self.assertFalse((project / "check-ran").exists())
        self.assertFalse(out.exists())
        self.assertIn("cannot run", report)

    def test_an_evidence_write_failure_is_an_operational_failure_with_the_outcome_recorded(self):
        project, home = self.project("write fails", "print('ran fine-7848')\n")
        folder = project / ".vibe-to-engineering" / "evidence"
        out = folder / "check.txt"
        os.chmod(str(folder), 0o555)                   # the evidence file cannot be written
        try:
            code, printed, saved, report, ran = self.run_tool(project, [sys.executable, "-B", "check.py"],
                                                              home)
        finally:
            os.chmod(str(folder), 0o755)
        self.assertEqual(code, 1, report)              # the check RAN — but its evidence was not saved
        self.assertTrue(ran)
        self.assertIsNone(saved)
        self.assertIn("cannot write", report)
        self.assertIn("the check ran", report)         # the child's outcome is still reported, as data

    # ---------------------------------------------------- 3: post-launch failures are never refusals

    def test_a_failure_after_the_launch_is_never_a_prelaunch_refusal(self):
        project, home = self.project("post launch", "print('ran first-7849')\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"

        def broken(tool):
            def boom(text, values, everywhere=frozenset()):
                raise tool.Fail("an injected post-launch failure-7849")
            return mock.patch.object(tool, "mask", boom)

        code, printed, report = self.in_process(
            ["--project", str(project), "--out", str(out), "--", sys.executable, "-B", "check.py"],
            home, broken)
        self.assertEqual(code, 3, report)              # the check ran: a post-launch failure, never 2
        self.assertTrue((project / "check-ran").exists())
        self.assertIn("post-launch failure-7849", report)

    def test_an_integrity_failure_after_the_run_is_three_with_the_outcome_standing(self):
        project, home = self.project("integrity", "print('ran fine-7850')\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"

        def broken(tool):
            def boom(root):
                raise tool.Fail("an injected integrity failure-7850")
            return mock.patch.object(tool.childenv, "cleanup", boom)

        code, printed, report = self.in_process(
            ["--project", str(project), "--out", str(out), "--", sys.executable, "-B", "check.py"],
            home, broken)
        self.assertEqual(code, 3, report)
        self.assertTrue((project / "check-ran").exists())
        self.assertTrue(out.exists())                  # the evidence stands
        self.assertIn("integrity failure", report)
        self.assertIn("the check ran", report)


if __name__ == "__main__":
    unittest.main()
