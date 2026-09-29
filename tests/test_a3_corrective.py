"""Regression tests for the A3 corrective (independent review of 569c8f9, 2026-09-29): the scratch BASE
is as much a boundary as the scratch root — the reviewed candidate's tests tampered with roots only.
Each test fails (or errors) on 569c8f9 and passes after the corrective.

  F1  a base failure after the launch is the governed integrity failure (exit 3) with the recoverable
      record still emitted — never a traceback, an exit 1 or an unmasked emission: retain creates and
      changes nothing at the base (lstat only), and every OSError there becomes a Fail
  F2  the base chain is never followed through a link: a `runs` swapped for a symlink after the launch
      is refused and the stranger is left exactly as found, mode included; a link before the launch is
      refused before any root exists; and a base that would stand inside the project is refused at
      construction
  F3  the "mode 0700" the evidence records is re-asserted on the VERIFIED root (the check can loosen
      its own root during the run), its home/ and tmp/ included — never through a swapped link; the
      header does not word retention as already confirmed
  F4  under umask 000 the first use still leaves every base level at 0700

Run from the repository root:  python3 -m unittest discover -s tests -p test_a3_corrective.py -v
"""

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import childenv  # noqa: E402
import evidence  # noqa: E402
from gitrun import Fail  # noqa: E402

SH = os.path.realpath("/bin/sh")


class A3Corrective(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-a3c-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def enroll(self, home):
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            with open(os.devnull, "w") as quiet:
                evidence.enroll_runner(SH, ask=lambda prompt: evidence.APPROVAL, out=quiet)

    def fresh_home(self, name):
        home = self.tmp / ("home-%s" % re.sub(r"\W+", "-", name))
        home.mkdir()
        self.enroll(home)
        return home

    def project(self, name):
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering" / "evidence").mkdir(parents=True)
        return project

    def run_tool(self, project, command, home, extra=()):
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)]
                              + list(extra) + ["--"] + list(command), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(os.environ, HOME=str(home)))
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"))

    def restore_base(self, home):
        """Undo a check's base tampering: put a moved-away runs/ back and drop whatever took its path."""
        runs = home / ".vibe-to-engineering" / "runs"
        if runs.is_symlink() or runs.is_file():
            runs.unlink()
        moved = home / ".vibe-to-engineering" / "runs-moved"
        if moved.is_dir() and not runs.exists():
            moved.rename(runs)

    # ------------------------------------------------------------------ F1: a base failure is governed

    def test_a_base_unreachable_after_launch_is_exit_3_never_a_traceback(self):
        # the reviewer's reproduction: the check chmods the base's parent to 000 — the reviewed candidate
        # crashed in retain's makedirs with a traceback, exit 1, no result record and a raw emission
        home = self.fresh_home("unreachable")
        project = self.project("base unreachable")
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "chmod 000 \"$HOME/../../..\""], home,
            extra=["--env", "K=scratchpad-a3f1"])
        try:
            self.assertEqual(code, 3, report)                    # the governed integrity failure — never 1
            self.assertIn("integrity failure", report)
            self.assertNotIn("Traceback", report)
            self.assertIn('"wrapper":3', report)                 # the recoverable record still emitted
            self.assertIsNotNone(saved)                          # the evidence stands
            self.assertNotIn("scratchpad-a3f1", report + printed)   # and nothing leaks the declared value
        finally:
            os.chmod(str(home / ".vibe-to-engineering"), 0o700)

    def test_a_base_replaced_by_a_file_after_launch_is_exit_3_never_a_traceback(self):
        # the reviewer's second route: runs/ becomes a plain file — the reviewed candidate died in
        # makedirs with FileExistsError
        home = self.fresh_home("replaced by file")
        project = self.project("base replaced")
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "B=$(cd \"$HOME/../..\" && pwd) && mv \"$B\" \"$B-moved\" && : > \"$B\""],
            home, extra=["--env", "K=scratchpad-a3f1b"])
        try:
            self.assertEqual(code, 3, report)
            self.assertIn("integrity failure", report)
            self.assertNotIn("Traceback", report)
            self.assertIn('"wrapper":3', report)
            self.assertIsNotNone(saved)
            self.assertNotIn("scratchpad-a3f1b", report + printed)
        finally:
            self.restore_base(home)

    # ------------------------------------------------------------------ F2: the chain is never followed

    def test_a_swapped_base_link_after_launch_never_chmods_the_stranger(self):
        # the reviewer's reproduction: runs/ becomes a link to a foreign folder — the reviewed candidate
        # reported exit 3 but had already chmodded the stranger to 0700 through the link
        home = self.fresh_home("link swap")
        project = self.project("base link swap")
        foreign = project / "foreign"
        foreign.mkdir()
        (foreign / "data.txt").write_text("precious-a3f2\n")
        os.chmod(str(foreign), 0o755)
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "B=$(cd \"$HOME/../..\" && pwd) && mv \"$B\" \"$B-moved\" && ln -s \"%s\" \"$B\""
                      % foreign], home)
        try:
            self.assertEqual(code, 3, report)                    # refused, as before …
            self.assertEqual(stat.S_IMODE(foreign.stat().st_mode), 0o755)   # … but the stranger's mode
            self.assertEqual((foreign / "data.txt").read_text(), "precious-a3f2\n")   # and bytes stand
        finally:
            self.restore_base(home)

    def test_a_base_link_before_launch_is_refused_and_the_stranger_untouched(self):
        # the reviewer's second route: runs/ is a link into the project before the launch — the reviewed
        # candidate made the root inside the project and chmodded the stranger, then reported exit 0
        home = self.fresh_home("prelaunch link")
        project = self.project("prelaunch base link")
        src = project / "src"
        src.mkdir()
        os.chmod(str(src), 0o755)
        shutil.rmtree(str(home / ".vibe-to-engineering" / "runs"))   # enrollment made one; the test's link
        os.symlink(str(src), str(home / ".vibe-to-engineering" / "runs"))   # takes its place instead
        code, printed, saved, report = self.run_tool(project, [SH, "-c", "echo never-a3f2b"], home)
        self.assertEqual(code, 2, report)                        # a pre-launch refusal: nothing ran
        self.assertIn("not a real directory", report)
        self.assertIsNone(saved)
        self.assertEqual(stat.S_IMODE(src.stat().st_mode), 0o755)   # never chmodded through the link
        self.assertEqual(os.listdir(str(src)), [])               # no root inside the project

    def test_a_base_inside_the_project_is_refused_before_construction(self):
        # unit level: with the project as the user's very home, the base would stand inside it — refused;
        # an ordinary project beside it constructs fine
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            with self.assertRaises(Fail):
                childenv.check_base(self.tmp)
            ordinary = self.tmp / "elsewhere"
            ordinary.mkdir()
            base = childenv.check_base(ordinary)
            self.assertEqual(base, Path(os.path.realpath(str(self.tmp / ".vibe-to-engineering" / "runs"))))

    # ------------------------------------------------------------------ F3: the recorded mode is true

    def test_the_recorded_mode_is_reasserted_on_the_verified_root(self):
        # the reviewer's reproduction: the check loosens its root, home/ and tmp/ to 0777 — the reviewed
        # candidate recorded "mode 0700" over them anyway and pre-claimed "retained" in the header
        home = self.fresh_home("loosened mode")
        project = self.project("loosened mode")
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "chmod 777 \"$HOME/..\" \"$HOME\" \"$TMPDIR\"; echo tok-a3f3 > \"$HOME/out\""],
            home)
        self.assertEqual(code, 0, report)
        root = Path(re.search(r"scratch root is retained at (\S+)", report).group(1))
        for folder in (root, root / "home", root / "tmp"):
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700, str(folder))
        self.assertEqual((root / "home" / "out").read_text(), "tok-a3f3\n")   # the contents stand either way
        self.assertNotIn("retained after the run", saved)        # the header does not pre-claim retention
        self.assertIn("kept after the run and reported on stderr", saved)

    # ------------------------------------------------------------------ F4: the umask never loosens a level

    def test_first_use_leaves_every_base_level_private_under_any_umask(self):
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            previous = os.umask(0)
            try:
                base = childenv.scratch_base()
            finally:
                os.umask(previous)
        chain = self.tmp / ".vibe-to-engineering"
        self.assertEqual(stat.S_IMODE(chain.stat().st_mode), 0o700)        # the intermediate level too
        self.assertEqual(stat.S_IMODE((chain / "runs").stat().st_mode), 0o700)
        self.assertEqual(base, Path(os.path.realpath(str(chain / "runs"))))


if __name__ == "__main__":
    unittest.main()
