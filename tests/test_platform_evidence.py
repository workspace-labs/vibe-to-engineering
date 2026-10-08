"""A4: portable refusal tests. No runner enrollment, check execution or user registry access.

Only the platform identifier is simulated; these tests do not establish native platform support.
"""

import contextlib
import io
import os
import shutil
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
import platformgate


class PlatformEvidence(unittest.TestCase):
    def invoke(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = evidence.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_unsupported_check_refuses_before_every_execution_dependency(self):
        for platform in ("win32", "linux", "freebsd"):
            for secret in ("synthetic-platform-canary", "macOS", "2"):
                with self.subTest(platform=platform, secret=secret), contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(platformgate.sys, "platform", platform))
                    blocked = [stack.enter_context(mock.patch.object(module, name,
                               side_effect=AssertionError("execution boundary reached: " + name)))
                               for module, name in ((evidence, "resolve_project"),
                                                    (evidence, "evidence_path"),
                                                    (evidence, "load_registry"),
                                                    (childenv, "construct"),
                                                    (childenv, "scratch_root"),
                                                    (evidence.subprocess, "run"),
                                                    (evidence, "write_lf"))]
                    code, printed, report = self.invoke([
                        "--project", "absent-" + secret, "--out", "absent.txt",
                        "--env", "TOKEN=" + secret, "--", "python3", "check.py"])
                    self.assertEqual(code, emission.REFUSED)
                    self.assertEqual(printed, "")
                    self.assertNotIn(secret, report)
                    self.assertEqual(emission.read_result(report), {
                        "v": 1, "wrapper": 2, "launched": False, "saved": False, "child": None})
                    for dependency in blocked:
                        dependency.assert_not_called()

    def test_unsupported_enrollment_never_resolves_asks_probes_or_reads_registry(self):
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform), contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(platformgate.sys, "platform", platform))
                blocked = [stack.enter_context(mock.patch.object(evidence, name,
                           side_effect=AssertionError(name)))
                           for name in ("enroll_runner", "resolve_candidate", "probe", "load_registry")]
                code, _, report = self.invoke(["--enroll-runner", "python3"])
                self.assertEqual(code, 2)
                self.assertFalse(emission.read_result(report)["launched"])
                for dependency in blocked:
                    dependency.assert_not_called()

    def test_imported_execution_apis_cannot_bypass_the_platform_gate(self):
        calls = (
            lambda: evidence.enroll_runner("python3", ask=mock.Mock()),
            lambda: evidence.enrolled_identity("python3", "python", Path("absent")),
            lambda: evidence.probe("python3", "python", {}, Path("absent")),
            lambda: childenv.construct(),
            childenv.scratch_root,
        )
        with mock.patch.object(platformgate.sys, "platform", "win32"), \
                mock.patch.object(evidence, "load_registry", side_effect=AssertionError("registry")), \
                mock.patch.object(evidence, "resolve_candidate", side_effect=AssertionError("candidate")), \
                mock.patch.object(evidence.subprocess, "run", side_effect=AssertionError("spawn")), \
                mock.patch.object(childenv.tempfile, "mkdtemp", side_effect=AssertionError("write")):
            for call in calls:
                with self.subTest(call=call), self.assertRaises(platformgate.PlatformRefusal):
                    call()

    def test_macos_reaches_admission_and_help_stays_read_only(self):
        with mock.patch.object(platformgate.sys, "platform", "darwin"), \
                mock.patch.object(childenv, "declared", side_effect=evidence.Fail("admission reached")) as admission:
            code, _, report = self.invoke(["--out", "unused.txt", "--", "python3"])
            self.assertEqual(code, 2)
            self.assertIn("admission reached", report)
            admission.assert_called_once()
        with mock.patch.object(platformgate.sys, "platform", "win32"), \
                mock.patch.object(evidence, "resolve_project", side_effect=AssertionError("project")):
            code, printed, report = self.invoke(["--help"])
            self.assertEqual(code, 0)
            self.assertIn("usage:", printed)
            self.assertEqual(report, "")

    def test_unsupported_subprocess_leaves_fixture_and_registry_unchanged(self):
        # Native on Windows/Linux; macOS explicitly simulates Linux in the child. All potential scratch
        # and registry access is redirected into this fixture even if the boundary regresses.
        with tempfile.TemporaryDirectory(prefix="v2e-platform-test-") as raw:
            root = Path(raw).resolve()
            project = root / "project"
            (project / ".vibe-to-engineering/evidence").mkdir(parents=True)
            scratch = root / "scratch"
            scratch.mkdir()
            registry = root / "runners.json"
            registry.write_text('{"version":1,"runners":{}}\n', encoding="utf-8")
            out = project / ".vibe-to-engineering/evidence/check.txt"
            script = ("import sys; sys.path.insert(0, sys.argv.pop(1)); import evidence; "
                      "evidence.childenv.SCRATCH_BASE = sys.argv.pop(1); "
                      "registry = sys.argv.pop(1); evidence.registry_path = lambda: registry; "
                      "sys.platform = 'linux' if sys.platform == 'darwin' else sys.platform; "
                      "sys.exit(evidence.main(sys.argv[1:]))")
            env = dict(os.environ, HOME=str(root), USERPROFILE=str(root),
                       APPDATA=str(root), LOCALAPPDATA=str(root), TMP=str(root), TEMP=str(root))
            for args in (["--project", str(project), "--out", str(out), "--", "python3"],
                         ["--enroll-runner", "python3"]):
                with self.subTest(command=args):
                    done = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                                           str(Path(evidence.__file__).parent), str(scratch), str(registry)] + args,
                                          env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                    self.assertEqual(done.returncode, 2, done.stderr)
                    self.assertIn(b"macOS-only", done.stderr)
                    self.assertFalse(emission.read_result(done.stderr.decode("utf-8"))["launched"])
                    self.assertEqual(list(scratch.iterdir()), [])
                    self.assertFalse(out.exists())
                    self.assertEqual(registry.read_text(encoding="utf-8"), '{"version":1,"runners":{}}\n')

    def test_plain_python_unsupported_startup_writes_no_sibling_bytecode(self):
        # No -B or PYTHONDONTWRITEBYTECODE: the installed entry point must establish this itself.
        # macOS simulates Linux before run_path; unsupported hosts execute their native platform.
        with tempfile.TemporaryDirectory(prefix="v2e-startup-test-") as raw:
            root = Path(raw).resolve()
            scripts = root / "scripts"
            shutil.copytree(Path(evidence.__file__).parent, scripts,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            home = root / "home"
            home.mkdir()
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            argv = ["--project", str(root / "absent"), "--out", str(root / "absent.txt"), "--", "python3"]
            if sys.platform == "darwin":
                launcher = ["-c", "import sys, runpy; sys.platform='linux'; "
                            "sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')",
                            str(scripts / "evidence.py")]
            else:
                launcher = [str(scripts / "evidence.py")]
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), APPDATA=str(home),
                       LOCALAPPDATA=str(home), TMP=str(home), TEMP=str(home))
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            done = subprocess.run([sys.executable, "-I"] + launcher + argv, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(done.returncode, 2, done.stderr)
            self.assertIn(b"macOS-only", done.stderr)
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(after, before)
            self.assertFalse(list(root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
