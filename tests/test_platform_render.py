"""A4 renderer boundary: unsupported hosts refuse before plan or browser operations."""
import contextlib
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "vibe-to-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import platformgate
import render_pdf


class RendererPlatform(unittest.TestCase):
    def test_unsupported_platform_refuses_before_argument_paths_or_io(self):
        for platform in ("win32", "linux", "freebsd"):
            for argv in ([], ["render_pdf.py", "private-plan.html", "existing-plan.pdf"]):
                with self.subTest(platform=platform, argv=argv):
                    error = io.StringIO()
                    with mock.patch.object(platformgate.sys, "platform", platform), \
                            mock.patch.object(render_pdf, "Path", side_effect=AssertionError("path access")), \
                            mock.patch.object(render_pdf, "find_browser", side_effect=AssertionError("browser lookup")), \
                            mock.patch.object(render_pdf.tempfile, "mkdtemp", side_effect=AssertionError("scratch creation")), \
                            mock.patch.object(render_pdf.subprocess, "run", side_effect=AssertionError("child launch")), \
                            contextlib.redirect_stderr(error):
                        self.assertEqual(render_pdf.main(argv), 1)
                    self.assertIn("macOS", error.getvalue())

    def test_supported_platform_reaches_existing_markup_refusal(self):
        # This mocks only the platform predicate; it makes no native macOS claim.
        with tempfile.TemporaryDirectory(prefix="v2e-render-markup-") as folder:
            html, pdf = Path(folder) / "plan.html", Path(folder) / "plan.pdf"
            html.write_text("<!DOCTYPE html><p>{{PROJECT}}</p>", encoding="utf-8")
            error = io.StringIO()
            with mock.patch.object(platformgate.sys, "platform", "darwin"), \
                    mock.patch.object(render_pdf, "find_browser", side_effect=AssertionError("browser lookup")), \
                    contextlib.redirect_stderr(error):
                self.assertEqual(render_pdf.main(["render_pdf.py", str(html), str(pdf)]), 1)
            self.assertIn("unfilled placeholders", error.getvalue())
            self.assertFalse(pdf.exists())

    def test_plain_python_cli_refusal_leaves_no_bytecode_or_output(self):
        with tempfile.TemporaryDirectory(prefix="v2e-render-refusal-") as folder:
            base = Path(folder)
            scripts = base / "scripts"
            scripts.mkdir()
            for name in ("render_pdf.py", "platformgate.py"):
                (scripts / name).write_bytes((SCRIPTS / name).read_bytes())
            html, pdf = base / "plan.html", base / "plan.pdf"
            html.write_bytes(b"<!DOCTYPE html><p>synthetic plan</p>")
            pdf.write_bytes(b"existing PDF must survive")
            (base / "sentinel").write_bytes(b"unrelated file")

            def snapshot():
                return {p.relative_to(base).as_posix():
                        (None if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                        for p in base.rglob("*")}

            before = snapshot()
            # Do not inherit -B's environment equivalent or redirect caches outside
            # the copied script tree: plain invocation must protect itself.
            env = {name: value for name, value in os.environ.items()
                   if name not in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX", "PYTHONPATH")}
            env.update(V2E_BROWSER=str(base / "must-not-run"), HOME=str(base), USERPROFILE=str(base),
                       TMPDIR=str(base), TMP=str(base), TEMP=str(base))
            command = [sys.executable, str(scripts / "render_pdf.py"), str(html), str(pdf)]
            if sys.platform == "darwin":
                # On macOS simulate an unsupported subprocess. Windows/Linux
                # exercise the native boundary without modifying sys.platform.
                # Import only built-in sys before the script disables bytecode;
                # importing runpy first can populate CLT Python's user cache.
                code = ("import sys; sys.path.insert(0,sys.argv[1]); "
                        "script=sys.argv[2]; sys.argv=sys.argv[2:]; sys.platform='linux'; "
                        "exec(compile(open(script, 'rb').read(), script, 'exec'), "
                        "{'__name__': '__main__', '__file__': script})")
                command = [sys.executable, "-c", code, str(scripts)] + command[1:]
            done = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=15)
            self.assertEqual(done.returncode, 1, done.stderr.decode("utf-8", "replace"))
            self.assertIn(b"macOS", done.stderr)
            self.assertEqual(snapshot(), before, "refusal created bytecode or changed files")


if __name__ == "__main__":
    unittest.main()
