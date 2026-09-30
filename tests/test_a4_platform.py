"""A4 — macOS-only platform refusal at the execution boundary.

Staged platform releases (owner-frozen): macOS → Linux → Windows; no platform is release-validated
until the revised implementation passes its release exam on it, and Linux/Windows details live in
the roadmap only. For each entry point — scripts/evidence.py, scripts/checkpoint.py and
scripts/render_pdf.py — and for linux, win32 and one other value (freebsd14), these tests prove:

- the refusal exit code follows the script's own convention (evidence.py 2, checkpoint.py 1,
  render_pdf.py 1), with a plain-language message that names the platform it saw, says this release
  supports macOS only and that Linux and Windows are on the roadmap — never a traceback;
- nothing is written: the disposable project's tree is byte-identical before/after and the isolated
  HOME has no ~/.vibe-to-engineering/ (no registry, no runs/), no evidence file, no checkpoint
  store, no PDF;
- nothing ran: a check that would write a sentinel never ran, and no browser launched;
- evidence.py's refusal carries the usual wrapper status record (wrapper 2, launched false, saved
  false), so an agent reading it sees a refusal;
- and darwin still runs normally.

A platform is simulated WITHOUT any production switch — there is none to switch: a child process
sets sys.platform and then runs the script with runpy. A simulated sys.platform is not a native
Linux/Windows run; these tests prove the refusal boundary, not those platforms' behavior.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "vibe-to-engineering" / "scripts"
PLATFORMS = ("linux", "win32", "freebsd14")

# Run one entry point as __main__ with sys.platform replaced — the simulation the brief names:
# no production flag or environment variable takes part.
HARNESS = "\n".join((
    "import runpy, sys",
    "script, platform = sys.argv[1], sys.argv[2]",
    "sys.argv = [script] + sys.argv[3:]",
    "sys.platform = platform",
    "try:",
    "    runpy.run_path(script, run_name='__main__')",
    "except SystemExit as quit_:",
    "    code = quit_.code",
    "    sys.exit(code if isinstance(code, int) else (0 if code is None else 1))",
    "sys.exit(0)",
))


class PlatformRefusal(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-a4-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.project = self.tmp / "project"
        (self.project / "src").mkdir(parents=True)
        (self.project / "src" / "app.js").write_bytes(b"console.log('app');\n")
        (self.project / "notes.txt").write_bytes(b"one\ntwo\n")
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env["HOME"] = str(self.home)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_as(self, script, platform, *args, env=None):
        done = subprocess.run([sys.executable, "-B", "-c", HARNESS, str(SCRIPTS / script), platform] +
                              [str(arg) for arg in args], env=dict(self.env, **(env or {})),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")

    def snapshot(self):
        """Everything under the disposable project: name -> kind and bytes, to prove it untouched."""
        state = {}
        for folder, dirs, names in os.walk(self.project):
            for name in dirs + names:
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, self.project)
                if os.path.islink(path):
                    state[rel] = ("link", os.readlink(path))
                elif os.path.isdir(path):
                    state[rel] = ("dir",)
                else:
                    state[rel] = ("file", Path(path).read_bytes())
        return state

    def assert_refusal(self, code, out, err, script, platform, expect, before):
        self.assertEqual(code, expect, "exit %d\n%s%s" % (code, out, err))
        self.assertEqual(out, "")
        self.assertIn("%s: error: this release supports macOS only" % script, err)
        self.assertIn("Linux and Windows are on the roadmap and not yet validated", err)
        self.assertIn("Nothing was run or written", err)
        self.assertIn("(platform seen: %s)" % platform, err)   # the platform it saw is named
        self.assertNotIn("Traceback", err)
        self.assertEqual(self.snapshot(), before)              # the project's tree is byte-identical
        self.assertFalse((self.home / ".vibe-to-engineering").exists())   # no registry, no runs/

    def test_evidence_py_refuses_before_any_write_or_launch(self):
        out_file = self.project / ".vibe-to-engineering" / "evidence" / "step" / "check.txt"
        sentinel = self.tmp / "check-ran"
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                before = self.snapshot()
                code, out, err = self.run_as("evidence.py", platform, "--project", self.project,
                                             "--out", out_file, "--", "/bin/sh", "-c",
                                             "echo ran >> '%s'" % sentinel)
                self.assert_refusal(code, out, err, "evidence.py", platform, 2, before)
                record = json.loads(err.strip().splitlines()[-1])   # the usual wrapper status record
                self.assertEqual((record["v"], record["wrapper"], record["launched"], record["saved"]),
                                 (1, 2, False, False))
                self.assertFalse(sentinel.exists())    # the check never ran
                self.assertFalse(out_file.exists())    # no evidence file

    def test_checkpoint_py_refuses_before_any_write_or_check(self):
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                before = self.snapshot()
                code, out, err = self.run_as("checkpoint.py", platform, "--project", self.project,
                                             "create", "a4-probe")
                self.assert_refusal(code, out, err, "checkpoint.py", platform, 1, before)
                self.assertFalse((self.project / ".vibe-to-engineering").exists())   # no checkpoint store

    def test_render_pdf_py_refuses_before_any_browser_or_pdf(self):
        plan = self.project / "plan.html"
        plan.write_text("<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"><title>t</title></head>"
                        "<body><p>hi</p></body></html>\n")
        launched = self.tmp / "browser-ran"
        browser = self.tmp / "browser"   # a browser that records its launch, so a launch cannot pass unseen
        browser.write_text("#!/bin/sh\necho launched >> '%s'\nexit 1\n" % launched)
        os.chmod(browser, 0o755)
        pdf = self.project / "plan.pdf"
        for platform in PLATFORMS:
            with self.subTest(platform=platform):
                before = self.snapshot()
                code, out, err = self.run_as("render_pdf.py", platform, plan, pdf,
                                             env={"V2E_BROWSER": str(browser)})
                self.assert_refusal(code, out, err, "render_pdf.py", platform, 1, before)
                self.assertFalse(launched.exists())   # no browser launched
                self.assertFalse(pdf.exists())        # no PDF

    def test_darwin_still_runs_normally(self):
        (self.project / ".vibe-to-engineering").mkdir()   # the state folder a planned project has
        out_file = self.project / ".vibe-to-engineering" / "evidence" / "step" / "check.txt"
        code, out, err = self.run_as("evidence.py", "darwin", "--project", self.project,
                                     "--out", out_file, "--", "/bin/sh", "-c", "true")
        self.assertEqual(code, 2, "exit %d\n%s%s" % (code, out, err))   # the ordinary pre-launch refusal:
        self.assertIn("no runners are enrolled for this user", err)     # an unenrolled runner, before launch
        self.assertNotIn("macOS only", err)
        self.assertNotIn("Traceback", err)

        code, out, err = self.run_as("checkpoint.py", "darwin", "--project", self.project,
                                     "create", "a4-darwin")
        self.assertEqual(code, 0, "exit %d\n%s%s" % (code, out, err))
        self.assertIn("created checkpoint a4-darwin", out + err)
        self.assertTrue((self.project / ".vibe-to-engineering" / "checkpoints.git").is_dir())

        plan = self.project / "bad-plan.html"
        plan.write_text("<!DOCTYPE html>\n<html><body><p>{{TODO}}</p></body></html>\n")
        code, out, err = self.run_as("render_pdf.py", "darwin", plan, self.project / "bad-plan.pdf")
        self.assertEqual(code, 1, "exit %d\n%s%s" % (code, out, err))   # the ordinary plan refusal
        self.assertIn("unfilled placeholders", err)
        self.assertNotIn("macOS only", err)


if __name__ == "__main__":
    unittest.main()
