"""Inventory depth, macOS key privacy, and the boundary between private state and the project's index."""
import contextlib
import io
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from support import Fixture, ROOT, STATE, identities, write

SCRIPTS = ROOT / "skills/vibe-to-engineering/scripts"
with mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
    import checkpoint
    import watched


class TreeInventory(unittest.TestCase):
    def test_default_inventory_opens_every_saved_level_and_only_explicit_depth_shortens_it(self):
        saved = [b"first/second/third/fourth/fifth/visible.py"]
        ignored = [b"dependency/cache/one", b"dependency/cache/two"]
        found = checkpoint.Found(saved, ignored, [], None)
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(checkpoint, "current_survey_read_only", return_value=found):
            for depth in ([], ["--depth", "2"]):
                args = checkpoint.build_parser().parse_args(["tree", "--current", *depth])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(checkpoint.cmd_tree(Path(temp), args), 0)
                text = output.getvalue()
                self.assertIn("[ignored — 2 files]", text)
                self.assertIn("1 file saved · 2 ignored (1 folder)", text)
                if depth:
                    self.assertNotIn("visible.py", text)
                    self.assertIn("shortened", text.splitlines()[0])
                else:
                    self.assertIn("visible.py", text)
                    self.assertNotIn("shortened", text.splitlines()[0])


@unittest.skipUnless(sys.platform == "darwin", "requires native macOS state handling")
class NativeState(Fixture):
    def test_extended_acl_refuses_an_otherwise_private_fingerprint_key(self):
        import pwd
        key = self.tmp / "fingerprint.key"
        original = watched.fingerprint_key(key)
        owner = pwd.getpwuid(os.geteuid()).pw_name
        subprocess.run(["/bin/chmod", "+a", "user:%s allow read" % owner, str(key)], check=True)
        try:
            info = key.stat()
            self.assertEqual((stat.S_IMODE(info.st_mode), info.st_uid, info.st_nlink), (0o600, os.geteuid(), 1))
            listing = subprocess.check_output(["/bin/ls", "-le", str(key)], text=True)
            self.assertIn("allow read", listing)
            with self.assertRaisesRegex(checkpoint.Fail, "access list|exclusive access"):
                watched.fingerprint_key(key)
        finally:
            subprocess.run(["/bin/chmod", "-N", str(key)], check=True)
        self.assertEqual(watched.fingerprint_key(key), original)

    def test_current_and_checkpoint_inventory_show_deep_saved_files(self):
        project = self.plain_project()
        write(project / "a/b/c/d/e/inventory.txt", b"saved\n")
        for args in (("tree", "--current"), ("create", "saved"), ("tree", "saved"),
                     ("tree", "saved", "--saved-only")):
            out, _ = self.tool(project, *args)
            if args[0] == "tree":
                self.assertIn("inventory.txt", out)
                if "--saved-only" not in args:
                    self.assertRegex(out, r"node_modules/\s+\[ignored — 1 file\]")

    def plan(self, project, operation, content=b"synthetic record\n"):
        return subprocess.run([sys.executable, "-IB", str(SCRIPTS / "planstate.py"),
                               "--project", str(project), operation], input=content, env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)

    def test_private_writers_refuse_indexed_state_before_work_and_preserve_the_index(self):
        project = self.git_project()
        state = project / STATE
        existing = state / "Engineering-Migration-Plan.html"
        write(existing, b"<!DOCTYPE html><html><body>existing plan</body></html>")
        write(state / ".gitignore", b"*\n")
        self.git(project, "add", "-f", str(existing))
        before = identities(project)
        commands = [(name, self.plan(project, name)) for name in ("plan", "append-ledger", "map-data")]
        for name, done in commands:
            with self.subTest(writer=name):
                self.assertEqual(done.returncode, 1, done.stderr)
                self.assertIn(b"Git already tracks", done.stderr)
        with mock.patch.dict(os.environ, self.env, clear=True), \
                mock.patch.object(sys, "path", [str(SCRIPTS)] + sys.path):
            import evidence
            import render_map
            import render_pdf
            refused = {"pdf": (render_pdf.main, ["render_pdf", str(existing), str(state / "plan.pdf")]),
                       "map": (render_map.main, ["render_map", "--project", str(project)]),
                       "checkpoint": (checkpoint.main, ["--project", str(project), "create", "baseline"]),
                       "evidence": (evidence.main, ["--project", str(project), "--out",
                                                   str(state / "evidence/proof.txt"), "--", "sh", "-c", ":"])}
            for name, (command, args) in refused.items():
                with self.subTest(writer=name), contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()) as err, \
                        mock.patch.object(render_pdf, "find_browser") as browser, \
                        mock.patch.object(evidence.childenv, "construct") as scratch:
                    self.assertEqual(command(args), evidence.emission.REFUSED if name == "evidence" else 1)
                    self.assertIn("Git already tracks", err.getvalue())
                    browser.assert_not_called()
                    scratch.assert_not_called()
        self.assertEqual(identities(project), before)

    def test_indexed_state_is_scoped_to_the_project_even_if_its_folder_is_ignored(self):
        repo = self.git_project()
        other = repo / STATE / "ledger.md"
        write(other, b"outer ledger\n")
        self.git(repo, "add", "-f", str(other))
        child = repo / "sample"
        child.mkdir()
        # Ignore the entire project directory while retaining a force-added index entry below it.
        with (repo / ".gitignore").open("ab") as target:
            target.write(b"sample/\n")
        original_index = identities(repo / ".git")["index"]
        self.assertEqual(self.plan(child, "plan").returncode, 0)
        self.assertEqual(identities(repo / ".git")["index"], original_index)
        sibling = child / STATE / "legacy.txt"
        write(sibling, b"older record\n")
        self.git(repo, "add", "-f", str(sibling))
        sibling.unlink()  # still indexed even though its working-tree path is missing
        before = identities(repo)
        for options in ({}, {"GIT_LITERAL_PATHSPECS": "1"}):
            with self.subTest(options=options), mock.patch.dict(self.env, options):
                result = self.plan(child, "append-ledger")
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b"Git already tracks", result.stderr)
        self.assertEqual(identities(repo), before)
