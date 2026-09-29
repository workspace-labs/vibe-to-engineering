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

The re-review of that corrective (9204241) found five more, inside the corrective itself; the N tests
below fail on 9204241 and pass after:

  N1  the identity check and the chmod were two path operations with a swap window between them —
      everything is now done through one descriptor: open (O_DIRECTORY|O_NOFOLLOW), fstat, fchmod,
      and home//tmp/ opened through it (dir_fd); scratch_base's levels likewise
  N2  a check removing its own $TMPDIR got exit 3 (a regression from 569c8f9's exit 0): a missing or
      non-directory home/ or tmp/ is skipped — only a failure on the verified root itself is exit 3
  N3  the inside-the-project check compared strings and a different letter case walked past it —
      containment is now judged by device and inode, walking the base's ancestors
  N4  check_base ran before --env/--with-path validation, so an early refusal still created the base
      folders — it now runs inside construct, after every validation, just before the root
  N5  the evidence header still said "kept after the run … mode 0700" even when the root was gone —
      it now points at the stderr retention report without claiming it

The third review (of cc5b862) closed N2–N5, found N1 only half-closed and four more defects; the P
tests below fail on cc5b862 and pass after, every injection hook asserting it actually fired (P5):

  P1  the base levels were opened by full path — a swap of .vibe-to-engineering after it was judged
      redirected the root into a stranger: levels are now chained by descriptor (dir_fd), the base
      descriptor stays open, and the root is created with mkdir(dir_fd=) and registered from fstat
  P2  a foreign real folder moved in as home/ or tmp/ was chmodded, no race needed: home/ and tmp/
      are registered by device and inode at creation, and only a matching inner descriptor is fchmodded
  P3  a check stripping its own root's read permission got "did not make" and exit 3 where 9204241
      restored it and exited 0: identity confirmed by lstat, permission restored never through a link,
      the root re-opened and re-verified
  P4  fstat calls sat outside the OSError handling — a failure escaped raw: both are wrapped into Fail

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
        self.assertIn("its retention is reported on stderr", saved)

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

    # ------------------------------------------------------- N1: no swap between check and chmod (re-review)

    def test_a_swap_between_identity_and_chmod_never_touches_the_stranger(self):
        # the re-reviewer's reproduction (N1), re-hooked per the P5 review note — the old lstat hook
        # could never fire on the descriptor-pinned retain, so the test passed vacuously. Now the swap
        # fires when retain performs its chmod — os.chmod by path on 9204241 (follows the link onto the
        # stranger) or os.fchmod on the descriptor-pinned corrective (harmless: the descriptor pins the
        # real root). The hook MUST fire, or the test proves nothing.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            root = childenv.scratch_root()
            foreign = self.tmp / "foreign"
            (foreign / "home").mkdir(parents=True)
            (foreign / "tmp").mkdir()
            for folder in (foreign, foreign / "home", foreign / "tmp"):
                os.chmod(str(folder), 0o755)
            moved = self.tmp / "moved-root"
            fired = []

            def swap_now():
                if not fired:
                    fired.append(True)
                    os.rename(str(root), str(moved))       # the injected swap: the root away, a link to
                    os.symlink(str(foreign), str(root))    # the stranger at its path

            real_chmod, real_fchmod = os.chmod, os.fchmod

            def chmod_hook(path, mode, *args, **kwargs):
                if sys._getframe(1).f_code.co_name == "retain":
                    swap_now()
                return real_chmod(path, mode, *args, **kwargs)

            def fchmod_hook(fd, mode, *args, **kwargs):
                if sys._getframe(1).f_code.co_name == "retain":
                    swap_now()
                return real_fchmod(fd, mode, *args, **kwargs)

            try:
                with mock.patch.object(childenv.os, "chmod", chmod_hook), \
                        mock.patch.object(childenv.os, "fchmod", fchmod_hook):
                    childenv.retain(root)
            except Fail:
                pass   # refusing the swapped object is safe too — what matters is the stranger stands
            self.assertTrue(fired, "the swap hook never fired — the test proves nothing (P5)")
            for folder in (foreign, foreign / "home", foreign / "tmp"):
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o755, str(folder))

    def test_a_link_swapped_in_before_retention_is_refused_and_never_opened(self):
        # the companion guard: with the root already replaced by a link when retain starts, the
        # O_NOFOLLOW open itself refuses — the stranger is never even opened, let alone chmodded
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            root = childenv.scratch_root()
            foreign = self.tmp / "foreign"
            foreign.mkdir()
            (foreign / "data.txt").write_text("precious-a3n1\n")
            os.chmod(str(foreign), 0o755)
            moved = self.tmp / "moved-root"
            os.rename(str(root), str(moved))
            os.symlink(str(foreign), str(root))
            try:
                with self.assertRaises(Fail):
                    childenv.retain(root)
                self.assertEqual(stat.S_IMODE(foreign.stat().st_mode), 0o755)
                self.assertEqual((foreign / "data.txt").read_text(), "precious-a3n1\n")
            finally:
                os.unlink(str(root))
                moved.rename(root)

    # ------------------------------------------------------- N2: a missing home/ or tmp/ is not a failure

    def test_a_check_removing_its_own_tmpdir_is_not_an_integrity_failure(self):
        # the re-reviewer's reproduction: rmdir $TMPDIR gave exit 3 on 9204241 — a regression from
        # 569c8f9's exit 0. The root was confirmed; a missing home/ or tmp/ is simply skipped
        home = self.fresh_home("removed tmpdir")
        project = self.project("removed tmpdir")
        code, printed, saved, report = self.run_tool(project, [SH, "-c", "rmdir \"$TMPDIR\""], home)
        self.assertEqual(code, 0, report)
        self.assertIn("scratch root is retained at", report)
        self.assertIsNotNone(saved)
        with self.subTest("a non-directory in its place is skipped the same way"):
            home = self.fresh_home("file tmpdir")
            project = self.project("file tmpdir")
            code, printed, saved, report = self.run_tool(
                project, [SH, "-c", "rmdir \"$TMPDIR\" && : > \"$TMPDIR\""], home)
            self.assertEqual(code, 0, report)

    # ------------------------------------------------------- N3: containment is judged by identity

    def test_a_base_inside_the_project_is_refused_even_in_another_letter_case(self):
        # the re-reviewer's reproduction: HOME=…/PROJ2/sub with project …/Proj2 slipped past the string
        # comparison on this case-insensitive filesystem — the run exited 0 with the root in the project
        upper = self.tmp / "PROJ2" / "sub"
        upper.mkdir(parents=True)
        if os.stat(str(self.tmp / "PROJ2")).st_ino != os.stat(str(self.tmp / "Proj2")).st_ino:
            self.skipTest("a case-sensitive filesystem keeps these distinct — nothing to launder")
        with mock.patch.dict(os.environ, {"HOME": str(upper)}):
            with self.assertRaises(Fail):
                childenv.check_base(self.tmp / "Proj2")

    # ------------------------------------------------------- N4: an early refusal creates nothing

    def test_a_refusal_on_the_arguments_creates_not_even_the_base(self):
        # the re-reviewer's reproduction: --with-path /nonexistent on a fresh HOME gave exit 2 but left
        # ~/.vibe-to-engineering/runs behind on 9204241, because check_base ran before the validation
        home = self.tmp / "home-fresh"
        home.mkdir()
        project = self.project("fresh home refusal")
        code, printed, saved, report = self.run_tool(project, [SH, "-c", "echo never-a3n4"], home,
                                                     extra=["--with-path", "/nonexistent-a3n4"])
        self.assertEqual(code, 2, report)
        self.assertFalse((home / ".vibe-to-engineering").exists())   # nothing — not even the base chain

    # ------------------------------------------------------- N5: the header never claims retention

    def test_the_evidence_header_reports_retention_not_claims_it(self):
        # the re-reviewer's reproduction: a check that moves its root away exits 3, but the evidence
        # still said "kept after the run … mode 0700". The header now points at the stderr report
        home = self.fresh_home("header honesty")
        project = self.project("header honesty")
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "R=$(cd \"$HOME/..\" && pwd) && mv \"$R\" moved-scratch"], home)
        self.assertEqual(code, 3, report)                    # the integrity failure stands …
        self.assertIsNotNone(saved)                          # … and so does the evidence …
        self.assertNotIn("kept after the run", saved)        # … but it never claimed the root was kept
        self.assertIn("its retention is reported on stderr", saved)

    # ------------------------------------------- P1: the base levels are chained by descriptor (third review)

    def test_a_swap_between_base_levels_cannot_redirect_the_root(self):
        # the third reviewer's reproduction: after level 1 was judged and closed, .vibe-to-engineering
        # becomes a link to a foreign folder holding a 0755 runs/. On cc5b862 the next level was opened
        # by re-walking the path — the root landed inside the stranger and the stranger's runs became
        # 0700. The descriptor-chained base ignores the swapped path entirely. The hook MUST fire.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            foreign = self.tmp / "foreign"
            (foreign / "runs").mkdir(parents=True)
            os.chmod(str(foreign / "runs"), 0o755)
            chain = self.tmp / ".vibe-to-engineering"
            moved = self.tmp / "chain-moved"
            real_close, fired = os.close, []

            def close_hook(fd):
                if not fired and sys._getframe(1).f_code.co_name in ("scratch_base", "open_base"):
                    fired.append(True)
                    os.rename(str(chain), str(moved))      # level 1 was judged and closed; the path now
                    os.symlink(str(foreign), str(chain))   # becomes a link into the stranger
                return real_close(fd)

            with mock.patch.object(childenv.os, "close", close_hook):
                childenv.scratch_root()
            self.assertTrue(fired, "the swap hook never fired — the test proves nothing (P5)")
            self.assertEqual(os.listdir(str(foreign / "runs")), [])        # no root inside the stranger
            self.assertEqual(stat.S_IMODE((foreign / "runs").stat().st_mode), 0o755)   # never chmodded

    # ------------------------------------------- P2: a foreign folder as home/ is a stranger too

    def test_a_foreign_folder_moved_in_as_home_is_never_chmodded(self):
        # the third reviewer's reproduction: the check moves its home/ aside and a foreign 0755 folder
        # in as home/ — no race needed. Since 9204241 the stranger was chmodded; only an inner
        # descriptor whose fstat matches the registered identity may be fchmodded.
        home = self.fresh_home("foreign home")
        project = self.project("foreign home")
        foreign = project / "foreign"
        foreign.mkdir()
        (foreign / "data.txt").write_text("precious-a3p2\n")
        os.chmod(str(foreign), 0o755)
        code, printed, saved, report = self.run_tool(
            project, [SH, "-c", "mv \"$HOME\" \"$HOME-aside\" && mv foreign \"$HOME\""], home)
        self.assertEqual(code, 0, report)
        root = Path(re.search(r"scratch root is retained at (\S+)", report).group(1))
        moved_in = root / "home"
        self.assertEqual(stat.S_IMODE(moved_in.stat().st_mode), 0o755)     # the stranger stands as found
        self.assertEqual((moved_in / "data.txt").read_text(), "precious-a3p2\n")
        self.assertTrue((root / "home-aside").is_dir())                    # the run's own home, untouched

    # ------------------------------------------- P3: an unreadable own root is restored, not blamed

    def test_a_check_making_its_own_root_unreadable_is_restored_not_blamed(self):
        # the third reviewer's reproduction: chmod 300 on the root — 9204241 restored it and exited 0;
        # cc5b862 reported a stranger ("did not make") with exit 3 and left the root d-wx------.
        home = self.fresh_home("unreadable root")
        project = self.project("unreadable root")
        code, printed, saved, report = self.run_tool(project, [SH, "-c", "chmod 300 \"$HOME/..\""], home)
        self.assertEqual(code, 0, report)
        root = Path(re.search(r"scratch root is retained at (\S+)", report).group(1))
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)         # restored, not left d-wx
        self.assertIsNotNone(saved)

    # ------------------------------------------- P4: an fstat failure is a governed Fail

    def test_an_fstat_failure_is_a_governed_fail_never_a_raw_error(self):
        # P4: an fstat failing inside scratch_base or retain must surface as Fail — a raw OSError in
        # main's finally would be a traceback and exit 1. The hook MUST fire in both halves.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            root = childenv.scratch_root()
            real_fstat, fired = os.fstat, []

            def boom(fd, *args, **kwargs):
                caller = sys._getframe(1).f_code.co_name
                if caller in ("retain", "scratch_base", "open_base"):
                    fired.append(caller)
                    raise PermissionError(13, "Permission denied")
                return real_fstat(fd, *args, **kwargs)

            with mock.patch.object(childenv.os, "fstat", boom):
                with self.assertRaises(Fail):
                    childenv.retain(root)
            self.assertIn("retain", fired)
            fired.clear()
            with mock.patch.object(childenv.os, "fstat", boom):
                with self.assertRaises(Fail):
                    childenv.scratch_base()
            self.assertTrue(fired)


if __name__ == "__main__":
    unittest.main()
