"""Tests for scripts/childenv.py: the constructed environment every check runs with (NEW-5 stage 1, slices
from the accepted design contract) — the synthesized profile, the run-owned scratch root and its strictly
scoped cleanup, --with-path validation, the prohibited-name set and --env validation, and the Windows
name-handling corrective (structural only, never run on native Windows).

Run from the repository root:  python3 -m unittest discover -s tests -p test_childenv.py -v
"""

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))   # the modules beside evidence.py
import childenv  # noqa: E402
from gitrun import Fail  # noqa: E402

SYNTHESIZED = ("PATH", "HOME", "TMPDIR", "LC_ALL", "LANG", "TZ")
PROHIBITED = (   # one or more representatives of each of the seven approved groups (D3)
    "BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS", "BASH_FUNC_run%%",
    "NODE_OPTIONS", "PYTHONPATH", "PYTHONSTARTUP", "PYTHONHOME", "DYLD_INSERT_LIBRARIES", "DYLD_PRINT_LIBRARIES",
    "DOTENV_KEY", "DOTENV_CONFIG_PATH",
    "NPM_CONFIG_REGISTRY", "npm_config_registry", "Npm_Config_Cache", "YARN_REGISTRY", "PNPM_HOME", "PIP_INDEX_URL",
    "GIT_DIR", "GIT_SSH_COMMAND", "GIT_CONFIG_GLOBAL",
    "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
    "LD_PRELOAD", "LD_LIBRARY_PATH",
)
ADMITTED = (   # names that only resemble the prohibited or synthesized sets stay admitted
    "DATABASE_URL", "API_ENDPOINT", "FOO", "_PRIVATE", "x", "my_var",
    "ENVOY", "BASH", "NODE", "GIT", "DOTENV", "DYLD", "PROXY", "PATHWAY", "HOMEBREW_PREFIX", "TMPDIR2",
)


class Childenv(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-childenv-test-")).resolve()
        self.roots = []   # scratch roots a test made, removed in tearDown through the module's own cleanup

    def tearDown(self):
        for root in self.roots:
            if root.exists():
                childenv.cleanup(root)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scratch(self):
        root = childenv.scratch_root()
        self.roots.append(root)
        return root

    def refused(self, call, *args):
        with self.assertRaises(Fail) as caught:
            call(*args)
        return str(caught.exception)

    # ------------------------------------------------------------ the synthesized profile (D2)

    def test_the_synthesized_profile_is_exactly_the_six_names(self):
        root = self.scratch()
        env = childenv.profile(root)
        self.assertEqual(sorted(env), sorted(SYNTHESIZED) + sorted(childenv.PINNED))
        self.assertEqual(env["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin")
        self.assertEqual(env["HOME"], str(root / "home"))
        self.assertEqual(env["TMPDIR"], str(root / "tmp"))
        self.assertEqual(env["LC_ALL"], "en_US.UTF-8")
        self.assertEqual(env["LANG"], "en_US.UTF-8")
        self.assertEqual(env["TZ"], "UTC")

    def test_with_path_folders_are_appended_after_the_system_path(self):
        env = childenv.profile(self.scratch(), ["/usr/local/bin", str(self.tmp)])
        self.assertEqual(env["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin:%s:%s"
                         % (os.path.realpath("/usr/local/bin"), self.tmp))

    # ------------------------------------------------------------ the run-owned scratch root (D2)

    def test_each_run_gets_a_fresh_private_scratch_root(self):
        first, second = self.scratch(), self.scratch()
        self.assertNotEqual(first, second)
        for root in (first, second):
            self.assertTrue(root.name.startswith(childenv.SCRATCH_PREFIX))
            self.assertEqual(root.parent, Path(os.path.realpath(childenv.SCRATCH_BASE)))
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            for name in ("home", "tmp"):
                folder = root / name
                self.assertTrue(folder.is_dir())
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_the_scratch_root_never_comes_from_the_parents_tmpdir(self):
        elsewhere = self.tmp / "parent-tmpdir"
        elsewhere.mkdir()
        with mock.patch.dict(os.environ, {"TMPDIR": str(elsewhere)}):
            root = self.scratch()
        self.assertNotIn(str(elsewhere), str(root))
        self.assertEqual(os.listdir(str(elsewhere)), [])

    # ------------------------------------------------------------ the strictly scoped cleanup (D2)

    def test_cleanup_removes_the_run_owned_scratch_root(self):
        root = self.scratch()
        (root / "home" / "work.txt").write_text("run data\n")
        childenv.cleanup(root)
        self.assertFalse(root.exists())
        self.roots.remove(root)

    def test_cleanup_refuses_anything_but_a_run_owned_scratch_root(self):
        untouched = self.tmp / "keep"
        untouched.mkdir()
        (untouched / "data.txt").write_text("KEEP THESE BYTES\n")
        cases = {
            "the scratch base itself": childenv.SCRATCH_BASE,
            "a folder outside the base": str(untouched),
            "a file outside the base": str(untouched / "data.txt"),
            "the filesystem root": os.sep,
            "a missing run-prefixed folder": os.path.join(childenv.SCRATCH_BASE, childenv.SCRATCH_PREFIX + "gone"),
            "a run-prefixed folder not made by a run": None,   # made below
        }
        manual = Path(childenv.SCRATCH_BASE) / (childenv.SCRATCH_PREFIX + "manual")
        manual.mkdir()
        cases["a run-prefixed folder not made by a run"] = str(manual)
        try:
            for why, path in cases.items():
                with self.subTest(why=why):
                    self.refused(childenv.cleanup, path)
            self.assertEqual((untouched / "data.txt").read_text(), "KEEP THESE BYTES\n")
            self.assertTrue(manual.exists())
        finally:
            manual.rmdir()

    def test_cleanup_refuses_a_link_even_one_naming_a_scratch_root(self):
        root = self.scratch()
        link = self.tmp / ("link-to-" + root.name)
        os.symlink(str(root), str(link))
        self.refused(childenv.cleanup, str(link))
        self.assertTrue(root.exists())   # nothing was deleted through the link

    # ------------------------------------------------------------ --with-path validation (D2)

    def test_with_path_accepts_an_absolute_existing_real_directory(self):
        self.assertEqual(childenv.with_path("/usr/bin"), os.path.realpath("/usr/bin"))
        self.assertEqual(childenv.with_path(str(self.tmp)), str(self.tmp))

    def test_with_path_refuses_what_is_not_an_absolute_existing_real_directory(self):
        a_file = self.tmp / "not-a-folder"
        a_file.write_text("x\n")
        cases = {"a relative path": "usr/bin", "the empty path": "",
                 "a missing folder": str(self.tmp / "missing"), "a plain file": str(a_file)}
        for why, path in cases.items():
            with self.subTest(why=why):
                self.refused(childenv.with_path, path)

    # ------------------------------------------------------------ the prohibited-name set (D3)

    def test_every_prohibited_name_is_matched(self):
        for name in PROHIBITED:
            with self.subTest(name=name):
                self.assertTrue(childenv.prohibited(name), name)

    def test_ordinary_names_are_not_prohibited(self):
        for name in ADMITTED:
            with self.subTest(name=name):
                self.assertFalse(childenv.prohibited(name), name)

    def test_no_prohibited_name_is_admitted_through_env(self):
        for name in PROHIBITED:
            with self.subTest(name=name):
                report = self.refused(childenv.declared, ["%s=a-secret-value-9911" % name])
                self.assertNotIn("a-secret-value-9911", report)   # a refusal names the name, never the value

    # ------------------------------------------------------------ --env validation (D4 rules 1-3)

    def test_valid_settings_are_admitted_values_kept_exactly(self):
        values = childenv.declared(["DATABASE_URL=postgres://throwaway/db", "EMPTY=", "EQUALS=a=b=c",
                                    "_under_score=1"])
        self.assertEqual(values, {"DATABASE_URL": "postgres://throwaway/db", "EMPTY": "", "EQUALS": "a=b=c",
                                  "_under_score": "1"})

    def test_malformed_settings_are_refused(self):
        cases = {"no equals sign": "JUSTNAME", "an empty name": "=value", "a digit first": "1FOO=x",
                 "a dash in the name": "FO-O=x", "a space in the name": "FO O=x", "an empty setting": ""}
        for why, text in cases.items():
            with self.subTest(why=why):
                self.refused(childenv.declared, [text])

    def test_a_name_given_twice_is_refused_even_with_the_same_value(self):
        self.refused(childenv.declared, ["A=1", "A=2"])
        self.refused(childenv.declared, ["A=1", "A=1"])
        self.assertEqual(childenv.declared(["a=1", "A=2"]), {"a": "1", "A": "2"})   # names are case-sensitive

    def test_a_synthesized_name_cannot_be_overridden(self):
        for name in tuple(SYNTHESIZED) + tuple(childenv.PINNED):
            with self.subTest(name=name):
                report = self.refused(childenv.declared, ["%s=/somewhere/else" % name])
                self.assertIn(name, report)
                self.assertNotIn("/somewhere/else", report)

    # ------------------------------------------------------------ the whole mapping, built once (D4 invariant)

    def test_construct_builds_profile_plus_declared_over_one_fresh_root(self):
        env, root, paths = childenv.construct(extra_paths=[str(self.tmp)], settings=["DB_PATH=/throwaway.db"])
        self.roots.append(root)
        self.assertEqual(paths, [str(self.tmp)])   # the validated entries, retained for the header (R2-F4)
        self.assertEqual(env, dict(childenv.profile(root, paths), DB_PATH="/throwaway.db"))
        self.assertEqual(sorted(env), sorted(SYNTHESIZED + ("DB_PATH",)) + sorted(childenv.PINNED))
        self.assertEqual(env["HOME"], str(root / "home"))

    def test_a_refused_setting_leaves_no_scratch_root_behind(self):
        before = set(os.listdir(os.path.realpath(childenv.SCRATCH_BASE)))
        self.refused(childenv.construct, [], ["BASH_ENV=/x"])
        self.refused(childenv.construct, ["/relative"], [])
        self.assertEqual(set(os.listdir(os.path.realpath(childenv.SCRATCH_BASE))), before)

    def test_construct_and_profile_never_resolve_a_mutable_argument_twice(self):
        # R2-F4: validate once, retain the result — a link retargeted after validation changes neither the
        # constructed PATH nor the retained entries a header is recorded from
        one, two = self.tmp / "one", self.tmp / "two"
        one.mkdir()
        two.mkdir()
        link = self.tmp / "link"
        os.symlink(str(one), str(link))
        env, root, paths = childenv.construct(extra_paths=[str(link)])
        self.roots.append(root)
        self.assertEqual(paths, [str(one)])
        os.unlink(str(link))
        os.symlink(str(two), str(link))                # retargeted AFTER validation
        self.assertEqual(paths, [str(one)])            # the retained entries stand
        self.assertIn(":%s" % one, env["PATH"])
        self.assertNotIn(str(two), env["PATH"])
        again = childenv.profile(root, paths)          # recording from the retained entries never re-resolves
        self.assertEqual(again["PATH"], env["PATH"])

    # ------------------------------------------------------------ Windows name handling (the Gate-3
    # corrective). STRUCTURAL ONLY: WINDOWS is patched in, so the rules are exercised, but nothing here was
    # ever run on native Windows — the OS-side collapse these rules refuse is from the Gate-3 investigation
    # (Microsoft's CreateProcessW documentation and CPython's _winapi.c), not from a native run.

    def windows(self):
        return mock.patch.object(childenv, "WINDOWS", True)

    def test_off_windows_case_variants_stay_distinct_names(self):
        # POSIX keeps its case-sensitive names: a lowercase variant of a prohibited or held name is a
        # different, harmless name there — only Windows folds case
        for name in ("pythonpath", "bash_env", "path", "home"):
            with self.subTest(name=name):
                self.assertFalse(childenv.prohibited(name), name)
                self.assertFalse(childenv.held(name), name)
        self.assertEqual(childenv.declared(["path=/elsewhere-3316"]), {"path": "/elsewhere-3316"})

    def test_on_windows_a_case_variant_of_a_prohibited_name_is_refused(self):
        with self.windows():
            for name in ("bash_env", "Bash_Env", "pythonpath", "PythonPath", "dyld_insert_libraries",
                         "dotenv_key", "yarn_registry", "pnpm_home", "pip_index_url", "git_dir",
                         "node_options", "ld_preload", "ld_library_path"):
                with self.subTest(name=name):
                    self.assertTrue(childenv.prohibited(name), name)
                    report = self.refused(childenv.declared, ["%s=x-3317" % name])
                    self.assertNotIn("x-3317", report)

    def test_on_windows_a_case_variant_of_a_held_name_cannot_be_overridden(self):
        with self.windows():
            for name in ("path", "Path", "home", "Home", "tmpdir", "lc_all", "lang", "tz",
                         "systemroot", "SYSTEMROOT", "SystemRoot"):
                with self.subTest(name=name):
                    report = self.refused(childenv.declared, ["%s=/elsewhere-3319" % name])
                    self.assertNotIn("/elsewhere-3319", report)

    def test_on_windows_a_case_variant_duplicate_is_refused(self):
        with self.windows():
            self.refused(childenv.declared, ["a=1", "A=2"])
            self.assertEqual(childenv.declared(["a=1", "B=2"]), {"a": "1", "B": "2"})

    def test_on_windows_the_profile_holds_a_systemroot_valued_by_the_os(self):
        with self.windows(), mock.patch.object(childenv, "system_root", return_value="C:\\Windows"):
            env = childenv.profile(self.scratch())
        self.assertEqual(env["SystemRoot"], "C:\\Windows")   # from the OS, never the parent's environment
        self.assertEqual(sorted(env), sorted(SYNTHESIZED + ("SystemRoot",)) + sorted(childenv.PINNED))

    def test_on_windows_a_systemroot_the_os_cannot_give_refuses_the_run(self):
        before = set(os.listdir(os.path.realpath(childenv.SCRATCH_BASE)))
        with self.windows(), mock.patch.object(
                childenv, "system_root", side_effect=Fail("cannot determine SystemRoot from the OS")):
            self.refused(childenv.construct, [], [])
        self.assertEqual(set(os.listdir(os.path.realpath(childenv.SCRATCH_BASE))), before)   # nothing left


if __name__ == "__main__":
    unittest.main()
