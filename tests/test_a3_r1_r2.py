"""Regression tests for A3's three Low leftovers (owner's R1–R3, 2026-09-30): the reviewer accepted
46114bc, but the owner wants the skill completely clean before A3 closes. Each test here fails on
46114bc and passes after the fix; R3's Q1 hygiene repair lives in test_a3_corrective.py (the test now
fails — never errors — on 87709ab) and its registry-pop repair in test_final_review_r1.py.

  R1  retain called verify_base() BEFORE _ROOTS.pop, so a failed base check left the root's held
      descriptor open and registered until the process exited: the pop now comes first, and the
      descriptor is closed exactly once on this path too (the companion proof in
      test_a3_corrective.py gained the "a failed base check" case)
  R2  any Fail raised after the root's mkdir in scratch_root left a real root in the base that was
      neither registered nor reported — and the tool never deletes. The refusal now names what the
      human needs to find it: the confirmed root path once the identity check has passed, and before
      it only the root's NAME — not even the base's path, which the same swap can point into a
      stranger (L1, review of 89d8151). Covered below: the preparation refusal (path printed), the
      stat-confirmation and the TRUE Q2 "resolves away" mismatch refusals (name only — the mismatch
      one plants a same-named folder in the stranger so os.stat succeeds on a different inode, L2),
      and the open refusal with and without a preceding swap

Run from the repository root:  python3 -m unittest discover -s tests -p test_a3_r1_r2.py -v
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import childenv  # noqa: E402
from gitrun import Fail  # noqa: E402


class A3R1R2(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-a3r-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def base(self):
        return Path(os.path.realpath(str(self.tmp / ".vibe-to-engineering" / "runs")))

    def made_roots(self, folder):
        return [name for name in os.listdir(str(folder)) if name.startswith(childenv.SCRATCH_PREFIX)]

    # ------------------------------------------------------- R1: a failed base check closes the descriptor

    def test_a_failed_base_check_closes_and_unregisters_the_held_descriptor(self):
        # R1: on 46114bc verify_base ran before the registry pop, so an injected base failure left
        # the held descriptor open and the root registered until the process exited. The pop now
        # comes first and the descriptor is closed exactly once on this path too.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            root = childenv.scratch_root()
            held = childenv._ROOTS[str(root)][0]
            real_close, closes = os.close, []

            def counting(fd):
                if fd == held:
                    closes.append(fd)
                return real_close(fd)

            with mock.patch.object(childenv, "verify_base",
                                   side_effect=Fail("injected base failure (R1)")), \
                    mock.patch.object(childenv.os, "close", counting):
                with self.assertRaises(Fail):
                    childenv.retain(root)
            self.assertEqual(closes, [held])                    # closed exactly once …
            self.assertNotIn(str(root), childenv._ROOTS)        # … and no longer registered

    # ------------------------------------------------------- R2: a refusal names the root it leaves behind

    def test_the_stat_confirmation_refusal_names_the_root_without_pointing_into_the_stranger(self):
        # R2, the swap case that lands on the STAT-CONFIRMATION branch (renamed 2026-09-30, L2 — it
        # never reached the Q2 mismatch branch): a base level is swapped between the root's creation
        # and the string's resolution, so os.stat of the root string finds NOTHING and the refusal is
        # "cannot be confirmed at its path". It must name the root so the human can find it — but
        # must NEVER print the recorded path, which now resolves into the stranger. The hook MUST fire.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            foreign = self.tmp / "foreign"
            (foreign / "runs").mkdir(parents=True)
            chain = self.tmp / ".vibe-to-engineering"
            moved = self.tmp / "chain-moved"
            real_close, fired = os.close, []

            def close_hook(fd):
                if not fired and sys._getframe(1).f_code.co_name == "scratch_root":
                    fired.append(True)
                    os.rename(str(chain), str(moved))
                    os.symlink(str(foreign), str(chain))
                return real_close(fd)

            with mock.patch.object(childenv.os, "close", close_hook):
                with self.assertRaises(Fail) as caught:
                    childenv.scratch_root()
            self.assertTrue(fired, "the swap hook never fired — the test proves nothing (P5)")
            made = self.made_roots(moved / "runs")           # the root stands where the run really
            self.assertEqual(len(made), 1)                   # made it: inside the pinned base, moved
            message = str(caught.exception)                  # away with the chain by the swap
            self.assertIn("cannot be confirmed at its path", message)   # the stat-failure branch
            self.assertIn(made[0], message)                  # named, so the human can find it …
            self.assertNotIn(str(foreign / "runs" / made[0]), message)   # … never via the stranger
            self.assertEqual(os.listdir(str(foreign / "runs")), [])      # the stranger stands untouched

    def test_the_mismatch_refusal_names_the_root_without_pointing_into_the_stranger(self):
        # R2, the TRUE Q2 identity-mismatch branch ("resolves away", L2): the stranger holds a folder
        # with the SAME name, so os.stat of the root string succeeds on a different inode. The refusal
        # must name the root, never print the stranger's path, and leave the stranger untouched. The
        # hook MUST fire. (Documents already-correct behavior on 89d8151 — the branch was never
        # covered before; it fails on 46114bc, where the message names nothing.)
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            foreign = self.tmp / "foreign"
            (foreign / "runs").mkdir(parents=True)
            chain = self.tmp / ".vibe-to-engineering"
            moved = self.tmp / "chain-moved"
            real_close, fired = os.close, []

            def close_hook(fd):
                if not fired and sys._getframe(1).f_code.co_name == "scratch_root":
                    fired.append(True)
                    name = self.made_roots(chain / "runs")[0]
                    (foreign / "runs" / name).mkdir()        # the same-named stand-in, so os.stat
                    (foreign / "runs" / name / "precious.txt").write_text("keep-l2\n")   # succeeds
                    os.rename(str(chain), str(moved))        # on a different inode
                    os.symlink(str(foreign), str(chain))
                return real_close(fd)

            with mock.patch.object(childenv.os, "close", close_hook):
                with self.assertRaises(Fail) as caught:
                    childenv.scratch_root()
            self.assertTrue(fired, "the swap hook never fired — the test proves nothing (P5)")
            made = self.made_roots(moved / "runs")           # the run's real root stands in the
            self.assertEqual(len(made), 1)                   # pinned base, moved away with the chain
            message = str(caught.exception)
            self.assertIn("resolves away", message)          # the true mismatch branch …
            self.assertIn(made[0], message)                  # … names the root …
            self.assertNotIn(str(foreign), message)          # … never the stranger's path
            standin = foreign / "runs" / made[0]
            self.assertEqual((standin / "precious.txt").read_text(), "keep-l2\n")   # untouched
            self.assertFalse(any(made[0] in key for key in childenv._ROOTS))        # never registered

    def test_an_open_refusal_after_a_base_swap_never_points_into_the_stranger(self):
        # R2/L1: the open fails AFTER a base level is swapped — the base path string now resolves
        # into the stranger, so the refusal must name the root only and print NO path (on 89d8151 it
        # printed the base path, which resolved into the stranger). The hook MUST fire.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            foreign = self.tmp / "foreign"
            (foreign / "runs").mkdir(parents=True)
            chain = self.tmp / ".vibe-to-engineering"
            moved = self.tmp / "chain-moved"
            real_open, fired = os.open, []

            def open_hook(path, flags, *args, **kwargs):
                if isinstance(path, str) and path.startswith(childenv.SCRATCH_PREFIX) and not fired:
                    fired.append(True)
                    os.rename(str(chain), str(moved))
                    os.symlink(str(foreign), str(chain))
                    raise PermissionError(13, "Permission denied")
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(childenv.os, "open", open_hook):
                with self.assertRaises(Fail) as caught:
                    childenv.scratch_root()
            self.assertTrue(fired, "the swap hook never fired — the test proves nothing (P5)")
            made = self.made_roots(moved / "runs")           # the root stands in the real base …
            self.assertEqual(len(made), 1)
            message = str(caught.exception)
            self.assertIn(made[0], message)                  # … named, so the human can find it …
            self.assertNotIn(str(chain / "runs"), message)   # … but the base string — which now
            self.assertNotIn(str(foreign), message)          # resolves into the stranger — is never
            self.assertEqual(os.listdir(str(foreign / "runs")), [])   # printed; the stranger stands

    def test_an_open_refusal_names_the_root_it_leaves_behind(self):
        # R2: the fresh root cannot be opened — the folder just made is left in the base, and the
        # refusal names it (name only, no path: the identity check has not passed) so the human can
        # find and remove it.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            real_open = os.open

            def open_hook(path, flags, *args, **kwargs):
                if isinstance(path, str) and path.startswith(childenv.SCRATCH_PREFIX):
                    raise PermissionError(13, "Permission denied")
                return real_open(path, flags, *args, **kwargs)

            with mock.patch.object(childenv.os, "open", open_hook):
                with self.assertRaises(Fail) as caught:
                    childenv.scratch_root()
            made = self.made_roots(self.base())
            self.assertEqual(len(made), 1)                   # the root stands, left behind …
            self.assertIn(made[0], str(caught.exception))    # … and the refusal names it

    def test_a_preparation_refusal_names_the_root_it_leaves_behind(self):
        # R2: home/ cannot be prepared — the identity check has already passed, so the confirmed
        # root string honestly names the folder and the refusal prints it.
        with mock.patch.dict(os.environ, {"HOME": str(self.tmp)}):
            real_mkdir = os.mkdir

            def mkdir_hook(path, mode=0o777, **kwargs):
                if path == "home":
                    raise PermissionError(13, "Permission denied")
                return real_mkdir(path, mode, **kwargs)

            with mock.patch.object(childenv.os, "mkdir", mkdir_hook):
                with self.assertRaises(Fail) as caught:
                    childenv.scratch_root()
            made = self.made_roots(self.base())
            self.assertEqual(len(made), 1)                        # the root stands, left behind …
            root = self.base() / made[0]
            self.assertIn(str(root), str(caught.exception))       # … and the refusal names its path
            self.assertNotIn(str(root), childenv._ROOTS)          # never registered


if __name__ == "__main__":
    unittest.main()
