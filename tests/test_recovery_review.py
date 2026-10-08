"""Focused recovery regressions using disposable projects and an isolated profile.

The positive cases bypass only the release platform guard to exercise portable
recovery logic; they do not establish native macOS release readiness.
"""

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "vibe-to-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import checkpoint


# Only built-in sys is imported before the entry point can disable bytecode.
# Interpreter-owned startup effects are measured separately in the Mac test.
MAC_UNSUPPORTED_BOOTSTRAP = (
    "import sys; sys.platform='linux'; sys.argv=sys.argv[1:]; "
    "exec(compile(open(sys.argv[0], 'rb').read(), sys.argv[0], 'exec'), "
    "{'__name__':'__main__', '__file__':sys.argv[0]})"
)


class RecoveryReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v2e-recovery-review-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        home = self.root / "home"
        home.mkdir()
        config = home / "gitconfig"
        config.write_bytes(b"[user]\n\tname = Recovery Test\n\temail = recovery@example.invalid\n")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(HOME=str(home), USERPROFILE=str(home),
                        GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1",
                        PYTHONDONTWRITEBYTECODE="1")
        self.environment = mock.patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git("init", "--quiet", "--template=", str(self.project))
        (self.project / "source.txt").write_bytes(b"baseline\n")
        (self.project / ".gitignore").write_bytes(b"local.db\n")
        (self.project / "local.db").write_bytes(b"database before\n")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.project), env=self.env,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def run_tool(self, *args):
        out, err = io.StringIO(), io.StringIO()
        # create=True lets these defect tests reproduce against the prior implementation.
        with mock.patch.object(checkpoint, "require_supported_platform", create=True), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = checkpoint.main(["--project", str(self.project), *args])
        return code, out.getvalue(), err.getvalue()

    def create_baseline(self):
        code, out, err = self.run_tool("create", "00-baseline")
        self.assertEqual(code, 0, out + err)

    def test_an_edited_state_ignore_file_refuses_before_store_writes(self):
        self.create_baseline()
        state = self.project / checkpoint.STATE_DIR
        ignore = state / ".gitignore"
        ignore.write_bytes(b"")
        before = {str(path.relative_to(state)): (path.stat().st_mtime_ns, path.read_bytes())
                  for path in state.rglob("*") if path.is_file()}
        code, out, err = self.run_tool("create", "01-next")
        self.assertEqual(code, 1, out + err)
        self.assertIn("ignore file", err)
        self.assertEqual(before, {str(path.relative_to(state)): (path.stat().st_mtime_ns, path.read_bytes())
                                  for path in state.rglob("*") if path.is_file()})

    def test_ignored_content_changed_during_preparation_stops_restore_before_writes(self):
        self.create_baseline()
        source = self.project / "source.txt"
        source.write_bytes(b"work after baseline\n")
        verify = checkpoint.verify_commit
        calls = []

        def change_after_verification(*args):
            result = verify(*args)
            calls.append(args)
            if len(calls) == 2:
                (self.project / "local.db").write_bytes(b"database changed\n")
            return result

        with mock.patch.object(checkpoint, "verify_commit", side_effect=change_after_verification):
            code, out, err = self.run_tool("restore", "00-baseline", "--apply")
        self.assertEqual(code, 1, out + err)
        self.assertIn("project changed while the restore was being prepared", err)
        self.assertEqual(source.read_bytes(), b"work after baseline\n")
        self.assertEqual((self.project / "local.db").read_bytes(), b"database changed\n")

    def test_ignored_content_changed_during_restore_is_reported_afterwards(self):
        self.create_baseline()
        (self.project / "source.txt").write_bytes(b"work after baseline\n")
        write_files = checkpoint.write_files

        def change_after_write(store, commit, target, paths=None):
            result = write_files(store, commit, target, paths)
            if Path(target) == self.project:
                (self.project / "local.db").write_bytes(b"database changed\n")
            return result

        with mock.patch.object(checkpoint, "write_files", side_effect=change_after_write):
            code, out, err = self.run_tool("restore", "00-baseline", "--apply")
        self.assertEqual(code, 1, out + err)
        self.assertIn("changed ignored file: local.db", err)
        self.assertEqual((self.project / "source.txt").read_bytes(), b"baseline\n")

    def test_an_ordinary_restore_still_preserves_ignored_contents(self):
        self.create_baseline()
        (self.project / "source.txt").write_bytes(b"work after baseline\n")
        code, out, err = self.run_tool("restore", "00-baseline", "--apply")
        self.assertEqual(code, 0, out + err)
        self.assertEqual((self.project / "source.txt").read_bytes(), b"baseline\n")
        self.assertEqual((self.project / "local.db").read_bytes(), b"database before\n")

    def test_unsupported_platforms_refuse_before_project_access(self):
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform):
                err = io.StringIO()
                with mock.patch("sys.platform", platform), \
                        mock.patch.object(checkpoint, "resolve_project") as resolve, \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    code = checkpoint.main(["--project", str(self.project), "create", "00-baseline"])
                self.assertEqual(code, 1, err.getvalue())
                self.assertIn("macOS-only", err.getvalue())
                resolve.assert_not_called()
                self.assertFalse((self.project / checkpoint.STATE_DIR).exists())

    def test_unsupported_cli_leaves_project_untouched(self):
        before = {str(path.relative_to(self.project)): path.read_bytes()
                  for path in self.project.rglob("*") if path.is_file()}
        command = [sys.executable]
        if sys.platform == "darwin":
            # Keep this refusal regression active in the macOS release suite too.
            command += ["-c", MAC_UNSUPPORTED_BOOTSTRAP]
        command += [str(SCRIPTS / "checkpoint.py"), "--project", str(self.project), "create", "00-baseline"]
        done = subprocess.run(command, env=self.env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(b"macOS-only", done.stderr)
        self.assertEqual(before, {str(path.relative_to(self.project)): path.read_bytes()
                                  for path in self.project.rglob("*") if path.is_file()})
        self.assertFalse((self.project / checkpoint.STATE_DIR).exists())

    def test_plain_python_refusal_adds_no_files_beyond_interpreter_startup(self):
        scripts = self.root / "scripts"
        shutil.copytree(str(SCRIPTS), str(scripts), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        env = dict(self.env)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env.pop("PYTHONPYCACHEPREFIX", None)
        command = [sys.executable]
        if sys.platform == "darwin":
            # Apple's CLT interpreter can create HOME/Library/Caches before any
            # script starts. Measure that startup alone before the Mac simulation;
            # the candidate must add no files beyond this measured baseline.
            initial = {str(path.relative_to(self.root))
                       for path in self.root.rglob("*") if path.is_file()}
            startup = subprocess.run([sys.executable, "-c", "pass"], env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(startup.returncode, 0, startup.stdout + startup.stderr)
            started = {str(path.relative_to(self.root))
                       for path in self.root.rglob("*") if path.is_file()}
            print("macOS bare-interpreter startup additions (recovery): %r" % sorted(started - initial))
            command += ["-c", MAC_UNSUPPORTED_BOOTSTRAP]
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}
        command += [str(scripts / "checkpoint.py"), "--project", str(self.project), "create", "00-baseline"]
        done = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(b"macOS-only", done.stderr)
        self.assertEqual(before, {str(path.relative_to(self.root)): path.read_bytes()
                                  for path in self.root.rglob("*") if path.is_file()})
        self.assertFalse(any(scripts.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
