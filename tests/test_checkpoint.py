"""Conformance tests for the recovery contract (skills/vibe-to-engineering/references/recovery.md).

Every test builds throwaway projects in a temporary folder and runs the checkpoint tool the way an
agent does: as a separate process. The git settings the tests use are isolated and deliberately
hostile (line-ending conversion on, commit signing on), so a pass also shows the tool does not depend
on the user's own git configuration.

Run from the repository root:  python3 -m unittest discover -s tests -v
To test another implementation of the contract, point V2E_CHECKPOINT at it.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_CHECKPOINT", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "checkpoint.py"))
STATE = ".vibe-to-engineering"
HOSTILE_GITCONFIG = """\
[user]
\tname = Fixture Author
\temail = fixture@example.invalid
[core]
\tautocrlf = true
[commit]
\tgpgsign = true
[gpg]
\tprogram = /nonexistent/gpg
[init]
\tdefaultBranch = main
"""


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def disk_state(root, skip=(".git", STATE)):
    """Every file and link under root: path -> ("link", target) or ("file", executable, bytes)."""
    state = {}
    for folder, dirs, names in os.walk(root):
        rel_folder = os.path.relpath(folder, root)
        if rel_folder == ".":
            dirs[:] = [d for d in dirs if d not in skip]
        for name in names + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
            path = os.path.join(folder, name)
            rel = os.path.normpath(os.path.join(rel_folder, name)).replace(os.sep, "/")
            if os.path.islink(path):
                state[rel] = ("link", os.readlink(path))
            else:
                state[rel] = ("file", bool(os.stat(path).st_mode & 0o111), Path(path).read_bytes())
    return state


def folder_digest(root):
    """One hash over every name and byte under root — proves a folder was not touched."""
    digest = hashlib.sha256()
    for folder, dirs, names in sorted(os.walk(root)):
        dirs.sort()
        for name in sorted(names):
            path = os.path.join(folder, name)
            digest.update(os.path.relpath(path, root).encode())
            if not os.path.islink(path):
                digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def case_insensitive_disk(folder):
    probe = Path(folder) / "CaseProbe"
    probe.write_text("x")
    try:
        return (Path(folder) / "caseprobe").exists()
    finally:
        probe.unlink()


class Contract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-test-")).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        (self.home / "gitconfig").write_text(HOSTILE_GITCONFIG)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update({"HOME": str(self.home), "GIT_CONFIG_GLOBAL": str(self.home / "gitconfig"),
                         "GIT_CONFIG_NOSYSTEM": "1", "USERPROFILE": str(self.home)})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------ helpers

    def git(self, cwd, *args):
        return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=str(cwd), env=self.env,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode()

    def tool(self, project, *args, expect=0):
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), *args], env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")
        if expect is not None:
            self.assertEqual(done.returncode, expect, "exit %d\n%s\n%s" % (done.returncode, out, err))
        return out, err

    def git_project(self, name="project"):
        """A repository holding every kind of file and every kind of uncommitted work."""
        p = self.tmp / name
        p.mkdir()
        self.git(p, "init", "-q")
        write(p / ".gitignore", b"node_modules/\n.env\n")
        write(p / ".gitattributes", b"* text=auto eol=crlf\n")
        write(p / "src" / "app.js", b"console.log('app');\n")
        write(p / "src" / "util.js", b"export const x = 1;\n")
        write(p / "windows.txt", b"one\r\ntwo\r\n")
        write(p / "unix.txt", b"one\ntwo\n")
        write(p / "run.sh", b"#!/bin/sh\necho hi\n")
        os.chmod(p / "run.sh", 0o755)
        os.symlink("src/app.js", str(p / "link.js"))
        write(p / "docs" / "Read Me ü.md", b"# read me\n")
        self.git(p, "add", "-A")
        self.git(p, "commit", "-qm", "first")
        write(p / "src" / "util.js", b"export const x = 2;\n")      # changed, not staged
        write(p / "staged.txt", b"staged\n")
        self.git(p, "add", "staged.txt")                              # staged, not committed
        write(p / "untracked.txt", b"new\n")                          # untracked
        write(p / ".env", b"SECRET=1\n")                              # ignored
        write(p / "node_modules" / "pkg" / "index.js", b"module.exports = 1;\n")  # ignored
        return p

    def plain_project(self, name="plain"):
        """A folder with no git at all."""
        p = self.tmp / name
        write(p / "main.py", b"print('hi')\n")
        write(p / "lib" / "calc.py", b"def add(a, b):\n    return a + b\n")
        write(p / "data" / "notes.txt", b"one\r\ntwo\r\n")
        write(p / ".gitignore", b"*.log\n")
        write(p / "debug.log", b"noise\n")
        write(p / "node_modules" / "dep" / "index.js", b"x\n")
        write(p / "__pycache__" / "main.cpython-39.pyc", b"\x00\x01")
        return p

    def without(self, state, *prefixes):
        return {k: v for k, v in state.items() if not any(k == p or k.startswith(p + "/") for p in prefixes)}

    # ------------------------------------------------------------ G2 hands off

    def test_create_leaves_the_project_and_its_own_repository_untouched(self):
        p = self.git_project()
        before_git, before_files = folder_digest(p / ".git"), disk_state(p)
        self.tool(p, "create", "00-baseline")
        self.assertEqual(folder_digest(p / ".git"), before_git, "the project's own .git changed")
        self.assertEqual(disk_state(p), before_files, "project files changed")
        self.assertEqual((p / STATE / ".gitignore").read_text(), "*\n")
        self.assertNotIn(STATE, self.git(p, "status", "--porcelain"))

    # ------------------------------------------------------------ G1 complete and byte-exact

    def test_a_checkpoint_holds_uncommitted_work_byte_for_byte_and_skips_ignored_files(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        out = self.tmp / "extracted"
        self.tool(p, "extract", "00-baseline", str(out))
        got = disk_state(out)
        self.assertEqual(got, self.without(disk_state(p), ".env", "node_modules"))
        self.assertEqual(got["windows.txt"][2], b"one\r\ntwo\r\n")
        self.assertEqual(got["unix.txt"][2], b"one\ntwo\n")
        self.assertEqual(got["src/util.js"][2], b"export const x = 2;\n")
        self.assertEqual(got["link.js"], ("link", "src/app.js"))
        self.assertTrue(got["run.sh"][1], "the executable bit was lost")
        for name in ("staged.txt", "untracked.txt", "docs/Read Me ü.md"):
            self.assertIn(name, got)
        self.assertNotIn(".env", got)

    def test_a_project_without_git_is_saved_minus_ignored_and_default_excluded_folders(self):
        p = self.plain_project()
        self.tool(p, "create", "00-baseline")
        self.assertFalse((p / ".git").exists(), "a .git folder appeared in the project")
        out = self.tmp / "extracted"
        self.tool(p, "extract", "00-baseline", str(out))
        self.assertEqual(disk_state(out), self.without(disk_state(p), "debug.log", "node_modules", "__pycache__"))

    def test_a_subfolder_project_follows_its_enclosing_repository_rules(self):
        repo = self.tmp / "monorepo"
        repo.mkdir()
        self.git(repo, "init", "-q")
        write(repo / ".gitignore", b"node_modules/\n")
        write(repo / "app" / "src" / "a.js", b"a\n")
        write(repo / "app" / "node_modules" / "x.js", b"x\n")
        write(repo / "other" / "b.js", b"b\n")
        self.tool(repo / "app", "create", "00-baseline")
        out = self.tmp / "extracted"
        self.tool(repo / "app", "extract", "00-baseline", str(out))
        self.assertEqual(sorted(disk_state(out)), ["src/a.js"])

    def test_the_state_folder_is_never_saved_even_when_the_project_tracks_it(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / STATE / "Engineering-Migration-Plan.html", b"<html></html>")
        write(p / STATE / "ledger.md", b"# ledger\n")
        self.git(p, "add", "-f", STATE + "/ledger.md")   # someone added the ledger to the project's own index
        (p / STATE / ".gitignore").unlink()
        self.tool(p, "create", "01-after")
        self.assertEqual((p / STATE / ".gitignore").read_text(), "*\n", "the ignore file was not put back")
        out, _ = self.tool(p, "diff", "00-baseline", "01-after")
        self.assertIn("no changes", out)

    # ------------------------------------------------------------ G3 permanent labels

    def test_a_label_can_never_be_reused(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store = p / STATE / "checkpoints.git"
        first = self.git(p, "--git-dir=" + str(store), "rev-parse", "refs/checkpoints/00-baseline")
        write(p / "unix.txt", b"changed\n")
        _, err = self.tool(p, "create", "00-baseline", expect=1)
        self.assertIn("already exists", err)
        self.assertEqual(self.git(p, "--git-dir=" + str(store), "rev-parse", "refs/checkpoints/00-baseline"), first)
        self.tool(p, "create", "Bad Label", expect=1)

    # ------------------------------------------------------------ G4 proven restorable

    def test_verify_passes_and_catches_a_damaged_store(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        out, _ = self.tool(p, "verify", "00-baseline")
        self.assertIn("byte for byte", out)
        store = p / STATE / "checkpoints.git"
        blob = self.git(p, "--git-dir=" + str(store), "rev-parse", "refs/checkpoints/00-baseline:unix.txt").strip()
        obj = store / "objects" / blob[:2] / blob[2:]
        os.chmod(obj, stat.S_IWRITE | stat.S_IREAD)
        obj.unlink()
        self.tool(p, "verify", "00-baseline", expect=1)

    def test_verify_catches_a_saved_file_whose_bytes_were_altered(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store = p / STATE / "checkpoints.git"
        blob = self.git(p, "--git-dir=" + str(store), "rev-parse", "refs/checkpoints/00-baseline:unix.txt").strip()
        obj = store / "objects" / blob[:2] / blob[2:]
        altered = b"one\nTWO\n"
        os.chmod(obj, stat.S_IWRITE | stat.S_IREAD)
        obj.write_bytes(zlib.compress(b"blob %d\0" % len(altered) + altered))
        _, err = self.tool(p, "verify", "00-baseline", expect=1)
        self.assertIn("unix.txt", err)

    # ------------------------------------------------------------ G5 honest comparison

    def test_diff_reports_moves_edits_additions_and_deletions(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        out, _ = self.tool(p, "diff", "00-baseline")
        self.assertIn("no changes", out)
        (p / "src" / "core").mkdir()
        os.rename(p / "src" / "app.js", p / "src" / "core" / "app.js")
        write(p / "unix.txt", b"one\ntwo\nthree\n")
        write(p / "added.txt", b"added\n")
        (p / "untracked.txt").unlink()
        out, _ = self.tool(p, "diff", "00-baseline", expect=3)
        self.assertRegex(out, r"R\d*\s+src/app\.js -> src/core/app\.js")
        self.assertRegex(out, r"M\s+unix\.txt")
        self.assertRegex(out, r"A\s+added\.txt")
        self.assertRegex(out, r"D\s+untracked\.txt")
        self.tool(p, "create", "01-phase-1")
        self.tool(p, "diff", "00-baseline", "01-phase-1", expect=3)
        out, _ = self.tool(p, "diff", "00-baseline", "--patch", "--path", "unix.txt", expect=3)
        self.assertIn("+three", out)

    # ------------------------------------------------------------ G6 safe restore

    def test_restore_without_apply_changes_nothing(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / "unix.txt", b"broken\n")
        before = disk_state(p)
        out, _ = self.tool(p, "restore", "00-baseline")
        self.assertIn("--apply", out)
        self.assertEqual(disk_state(p), before)
        listed, _ = self.tool(p, "list")
        self.assertNotIn("pre-restore", listed)

    def test_restore_brings_back_the_exact_checkpoint_saves_the_broken_state_and_spares_ignored_files(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        good = disk_state(p)
        (p / "src" / "core").mkdir()
        os.rename(p / "src" / "app.js", p / "src" / "core" / "app.js")   # a move
        write(p / "unix.txt", b"edited\n")                                # an edit
        write(p / "src" / "feature" / "new.js", b"new\n")                 # a new folder
        (p / "untracked.txt").unlink()                                    # a deletion
        os.chmod(p / "run.sh", 0o644)                                     # a lost executable bit
        write(p / "node_modules" / "pkg" / "index.js", b"changed dependency\n")  # ignored: must stay
        write(p / "node_modules" / "later.js", b"ignored, added later\n")        # ignored: must stay
        broken = disk_state(p)
        self.tool(p, "restore", "00-baseline", "--apply")
        expected = dict(good)
        for name in ("node_modules/pkg/index.js", "node_modules/later.js"):
            expected[name] = broken[name]
        self.assertEqual(disk_state(p), expected)
        self.assertFalse((p / "src" / "core").exists(), "an emptied folder was left behind")
        self.assertFalse((p / "src" / "feature").exists(), "an emptied folder was left behind")
        listed, _ = self.tool(p, "list")
        saved = re.search(r"pre-restore-\S+", listed).group(0)
        out = self.tmp / "broken"
        self.tool(p, "extract", saved, str(out))
        self.assertEqual(disk_state(out), self.without(broken, ".env", "node_modules"))

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX folder permissions and a normal user")
    def test_a_restore_that_cannot_finish_says_so_and_keeps_the_saved_state(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / "locked" / "extra.txt", b"added after the checkpoint\n")
        os.chmod(p / "locked", 0o555)   # the file inside can no longer be deleted
        try:
            _, err = self.tool(p, "restore", "00-baseline", "--apply", expect=1)
        finally:
            os.chmod(p / "locked", 0o755)
        self.assertIn("did not complete", err)
        self.assertRegex(err, r"saved as checkpoint pre-restore-\S+")
        self.assertTrue((p / "locked" / "extra.txt").exists())

    def test_restore_puts_back_a_name_whose_only_change_was_letter_case(self):
        if not case_insensitive_disk(self.tmp):
            self.skipTest("this file system tells letter cases apart")
        for p in (self.git_project("with-git"), self.plain_project("without-git")):
            with self.subTest(project=p.name):
                write(p / "src" / "Utils.js", b"export const u = 1;\n")
                if (p / ".git").exists():
                    self.git(p, "add", "src/Utils.js")
                self.tool(p, "create", "00-baseline")
                os.rename(p / "src" / "Utils.js", p / "src" / "tmp-name.js")
                os.rename(p / "src" / "tmp-name.js", p / "src" / "utils.js")
                out, _ = self.tool(p, "diff", "00-baseline", expect=3)
                self.assertIn("src/utils.js", out)
                self.tool(p, "restore", "00-baseline", "--apply")
                names = os.listdir(p / "src")
                self.assertIn("Utils.js", names)
                self.assertNotIn("utils.js", names)

    def test_a_full_cycle_works_without_git(self):
        p = self.plain_project()
        self.tool(p, "create", "00-baseline")
        self.tool(p, "verify", "00-baseline")
        good = disk_state(p)
        (p / "lib" / "math").mkdir()
        os.rename(p / "lib" / "calc.py", p / "lib" / "math" / "calc.py")
        out, _ = self.tool(p, "diff", "00-baseline", expect=3)
        self.assertRegex(out, r"R\d*\s+lib/calc\.py -> lib/math/calc\.py")
        self.tool(p, "restore", "00-baseline", "--apply")
        self.assertEqual(disk_state(p), good)
        self.assertFalse((p / ".git").exists())

    # ------------------------------------------------------------ G10 ignored files are watched

    def test_diff_and_restore_report_ignored_files_that_disappeared(self):
        for p, ignored in ((self.git_project(), ".env"), (self.plain_project(), "debug.log")):
            with self.subTest(project=p.name):
                self.tool(p, "create", "00-baseline")
                (p / "config").mkdir()
                os.rename(p / ignored, p / "config" / ignored)   # a careless phase moved an ignored file
                out, _ = self.tool(p, "diff", "00-baseline", expect=3)
                self.assertRegex(out, r"gone\s+%s" % re.escape(ignored))
                out, _ = self.tool(p, "restore", "00-baseline")
                self.assertIn("cannot bring them back", out)
                os.rename(p / "config" / ignored, p / ignored)
                (p / "config").rmdir()
                out, _ = self.tool(p, "diff", "00-baseline")
                self.assertIn("no changes", out)

    def test_an_ignored_file_is_not_called_gone_when_git_lists_its_whole_folder_instead(self):
        p = self.plain_project()
        write(p / "out" / "run.log", b"ignored\n")
        write(p / "out" / "keep.txt", b"kept\n")
        self.tool(p, "create", "00-baseline")
        write(p / ".gitignore", b"*.log\nout/\n")   # the whole folder is now ignored, so git lists only "out/"
        out, _ = self.tool(p, "diff", "00-baseline", expect=3)
        self.assertRegex(out, r"M\s+\.gitignore")
        self.assertNotIn("gone", out)
        self.assertTrue((p / "out" / "run.log").exists())

    # ------------------------------------------------------------ G9 read-only tree

    def test_tree_of_the_current_files_writes_nothing(self):
        for p in (self.git_project(), self.plain_project()):
            with self.subTest(project=p.name):
                before = disk_state(p, skip=())
                before_git = folder_digest(p / ".git") if (p / ".git").exists() else None
                out, _ = self.tool(p, "tree", "--current")
                self.assertEqual(disk_state(p, skip=()), before)
                if before_git:
                    self.assertEqual(folder_digest(p / ".git"), before_git)
                self.assertFalse((p / STATE).exists(), "tree --current created the state folder")
                self.assertNotIn("node_modules", out)

    # ------------------------------------------------------------ refusals

    def test_refuses_a_home_folder_a_file_system_root_and_unsafe_extract_targets(self):
        self.tool(self.home, "tree", expect=1)
        self.tool(Path(self.tmp.anchor), "tree", expect=1)
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        self.tool(p, "extract", "00-baseline", str(p / "inside"), expect=1)
        full = self.tmp / "full"
        write(full / "x.txt", b"x")
        self.tool(p, "extract", "00-baseline", str(full), expect=1)
        self.tool(p, "restore", "no-such-label", expect=1)


if __name__ == "__main__":
    unittest.main()
