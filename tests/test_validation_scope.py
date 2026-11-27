"""Validation refusals use missing groups and synthetic public/private source fixtures."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from unittest import mock

import run_validation
import test_package


class ValidationScope(unittest.TestCase):
    def test_empty_and_partial_native_workers_do_not_claim_success(self):
        with tempfile.TemporaryDirectory() as folder:
            summary = Path(folder) / "summary.json"
            for make_suite in (lambda: unittest.TestSuite(),
                               lambda: unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])):
                with self.subTest(), mock.patch.object(unittest.TestLoader, "discover", return_value=make_suite()):
                    summary.write_text(json.dumps({"prerequisites": {}, "source_privacy": {}}))
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        code = run_validation.worker("macos", summary)
                    report = json.loads(summary.read_text())
                    self.assertNotEqual(code, 0)
                    self.assertFalse(report["passed"])
                    self.assertIn("test_checkpoint.Contract", report["discovery"]["missing_groups"])
                    self.assertIn("test_literal_matrix.DifferentialMatrix", report["discovery"]["missing_groups"])

    def test_omitting_one_native_group_or_duplicating_a_method_breaks_coverage(self):
        import suite_scope
        class Method:
            def __init__(self, group):
                self.group = group

            def id(self):
                return self.group + ".test_example"

        all_groups = [Method(group) for group in sorted(suite_scope.NATIVE_GROUPS)]
        self.assertTrue(suite_scope.discovery("macos", all_groups)["complete"])
        for suite in (all_groups[1:], all_groups + all_groups[:1]):
            self.assertFalse(suite_scope.discovery("macos", suite)["complete"])

    def test_source_archive_checks_ci_and_ordinary_test_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            skill = root / "skills" / "vibe-to-engineering"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("public")
            check = test_package.Package("test_public_text_has_no_personal_paths")
            for rel in (".github/workflows/example.yml", "tests/ordinary.py", "extra/sample.txt"):
                sample = root / rel
                sample.parent.mkdir(parents=True, exist_ok=True)
                sample.write_bytes(b"/Use" + b"rs/synthetic/project")
                with self.subTest(group=rel), mock.patch.object(test_package, "ROOT", root), \
                        mock.patch.object(test_package, "SKILL", skill), self.assertRaises(AssertionError):
                    check.test_public_text_has_no_personal_paths()
                sample.unlink()

    def test_history_and_untracked_sources_report_only_counts(self):
        checker = Path(run_validation.__file__).with_name("package_privacy.py")
        self.assertTrue(checker.is_file(), "missing checkout and reachable-history privacy check")
        with tempfile.TemporaryDirectory() as directory:
            outer = Path(directory)
            root = outer / "repo"
            root.mkdir()
            term = "ExampleCafé" + "PrivateWord"
            names = outer / "names.json"
            names.write_text(json.dumps({term: "private-example"}))
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
            def git(*args):
                subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-c", "user.name=Fixture",
                                "-c", "user.email=fixture@example.invalid", *args], cwd=root, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            def inspect(history=False):
                argv = [sys.executable, "-B", str(checker), "--root", str(root), "--name-map", str(names)]
                if history:
                    argv.append("--history")
                result = subprocess.run(argv, cwd=outer, capture_output=True, text=True)
                self.assertNotIn(term.casefold(), (result.stdout + result.stderr).casefold())
                self.assertNotIn(str(names), result.stdout + result.stderr)
                return result.returncode, json.loads(result.stdout)

            git("init", "-q")
            old = root / (unicodedata.normalize("NFD", term.lower()) + ".txt")
            old.write_text(unicodedata.normalize("NFD", term.upper()))
            git("add", "--all")
            git("commit", "-qm", "earlier " + term)
            old.unlink()
            (root / "public.txt").write_text("public")
            git("add", "--all")
            git("commit", "-qm", "retire old example")
            self.assertEqual(inspect()[0], 0)
            code, report = inspect(history=True)
            self.assertEqual(code, 1)
            history = report["history"]
            self.assertEqual((history["commits"], history["matching_paths"], history["matching_blobs"],
                              history["matching_commits"]), (2, 1, 1, 1))
            old.write_text(term)
            code, report = inspect()
            self.assertEqual(code, 1)
            current = report["current"]
            self.assertEqual((current["matching_paths"], current["matching_contents"]), (1, 1))
            inside = root / "private-map.json"
            inside.write_bytes(names.read_bytes())
            def assert_refuses_map():
                result = subprocess.run([sys.executable, "-B", str(checker), "--root", str(root),
                                         "--name-map", str(inside)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn(term, result.stdout + result.stderr)
            assert_refuses_map()
            inside.unlink()
            try:
                inside.symlink_to(names)
            except OSError as error:
                if os.name != "nt" or getattr(error, "winerror", None) != 1314:
                    raise
            else:
                assert_refuses_map()
