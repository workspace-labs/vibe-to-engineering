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
import unicodedata
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


def identities(root):
    """Every name under root, root included, with its inode, modification time and bytes — proves nothing under it was
    written, replaced, created or removed, not even with the same bytes."""
    found = {}
    for folder, dirs, names in os.walk(root):
        for path in [folder] + [os.path.join(folder, name) for name in names]:
            info = os.lstat(path)
            found[os.path.relpath(path, root)] = (info.st_ino, info.st_mtime_ns,
                                                  Path(path).read_bytes() if stat.S_ISREG(info.st_mode) else None)
    return found


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

    def tool(self, project, *args, expect=0, env=None):
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), *args], env=dict(self.env, **(env or {})),
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

    def store(self, project):
        return project / STATE / "checkpoints.git"

    def store_git(self, project, *args, data=None):
        done = subprocess.run(["git", "--git-dir=" + str(self.store(project)), *args], env=self.env, input=data,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.stdout.decode().strip()

    def damage(self, project, label, path, data=None):
        """Delete the stored copy of `path` in checkpoint `label`, or replace its bytes with `data` under the same id."""
        oid = self.store_git(project, "rev-parse", "refs/checkpoints/%s:%s" % (label, path))
        obj = self.store(project) / "objects" / oid[:2] / oid[2:]
        os.chmod(obj, stat.S_IWRITE | stat.S_IREAD)
        if data is None:
            obj.unlink()
        else:
            obj.write_bytes(zlib.compress(b"blob %d\0" % len(data) + data))

    def repository(self, folder, files):
        """A git repository in `folder` whose one commit holds `files` (name -> bytes)."""
        for name, data in files.items():
            write(folder / name, data)
        self.git(folder, "init", "-q")
        self.git(folder, "add", *files)
        self.git(folder, "commit", "-qm", "committed")
        return folder

    def plant(self, project, label, files):
        """Save by hand a checkpoint holding `files` (name -> bytes), the way a store from another disk could hold it."""
        rows = ["100644 blob %s\t%s" % (self.store_git(project, "hash-object", "-w", "--stdin", data=data), name)
                for name, data in files.items()]
        tree = self.store_git(project, "mktree", data=("\n".join(rows) + "\n").encode())
        commit = self.store_git(project, "commit-tree", "-m", "vibe-to-engineering checkpoint: " + label, tree)
        self.store_git(project, "update-ref", "refs/checkpoints/" + label, commit)

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

    # ------------------------------------------------------------ G6 nothing a checkpoint does not hold is touched (F01)

    def test_restore_refuses_to_overwrite_or_remove_what_no_checkpoint_holds(self):
        outside = self.tmp / "outside"
        write(outside / "app.ini", b"outside the project\n")
        conf = lambda p, ignored: (shutil.rmtree(p / "conf"), write(p / ".gitignore", b"node_modules/\n.env\nconf\n"),
                                   write(p / "conf", ignored) if ignored else os.symlink(str(outside), str(p / "conf")))
        cases = {   # name: (before the checkpoint, after it)
            "a file that became ignored": (
                lambda p: write(p / "local.txt", b"an ordinary file\n"),
                lambda p: (write(p / ".gitignore", b"node_modules/\n.env\nlocal.txt\n"),
                           write(p / "local.txt", b"IMPORTANT IGNORED DATA\n"))),
            "a folder holding an ignored database where a file goes": (
                lambda p: write(p / "shape", b"a file\n"),
                lambda p: ((p / "shape").unlink(), write(p / ".gitignore", b"node_modules/\n.env\n*.db\n"),
                           write(p / "shape" / "local.db", b"KEEP THIS DATABASE\n"))),
            "an ignored file where a folder goes": (
                lambda p: write(p / "conf" / "app.ini", b"x=1\n"), lambda p: conf(p, b"ignored data\n")),
            "an ignored link where a folder goes": (
                lambda p: write(p / "conf" / "app.ini", b"x=1\n"), lambda p: conf(p, None)),
            "a nested repository where a folder was": (
                lambda p: write(p / "module" / "app.ini", b"x=1\n"),
                lambda p: ((p / "module" / "app.ini").unlink(), self.git(p / "module", "init", "-q"))),
        }
        if case_insensitive_disk(self.tmp):
            cases["an ignored file whose name differs only in letter case"] = (
                lambda p: write(p / "Notes.txt", b"saved notes\n"),
                lambda p: ((p / "Notes.txt").unlink(), write(p / ".gitignore", b"node_modules/\n.env\nnotes.txt\n"),
                           write(p / "notes.txt", b"IGNORED NOTES\n")))
        for number, (name, (before_checkpoint, after_checkpoint)) in enumerate(cases.items()):
            with self.subTest(case=name):
                p = self.git_project("collision-%d" % number)
                before_checkpoint(p)
                self.tool(p, "create", "00-baseline")
                after_checkpoint(p)
                before, kept = disk_state(p), folder_digest(outside)
                self.tool(p, "restore", "00-baseline", expect=1)            # the dry run already says no
                _, err = self.tool(p, "restore", "00-baseline", "--apply", expect=1)
                self.assertIn("nothing in the project was changed", err.lower())
                self.assertEqual(disk_state(p), before)
                self.assertEqual(folder_digest(outside), kept)

    # ------------------------------------------------------------ G6 both recovery points are proven first (F04)

    def test_restore_changes_nothing_when_the_target_checkpoint_is_damaged(self):
        for damage in (None, b"CORRUPTED\n"):
            with self.subTest(damage="missing" if damage is None else "altered"):
                p = self.git_project("missing" if damage is None else "altered")
                self.tool(p, "create", "00-baseline")
                write(p / "unix.txt", b"current work\n")
                write(p / "added.txt", b"added since the checkpoint\n")
                self.damage(p, "00-baseline", "unix.txt", damage)
                before = disk_state(p)
                _, err = self.tool(p, "restore", "00-baseline", "--apply", expect=1)
                self.assertEqual(disk_state(p), before)
                self.assertIn("00-baseline", err)

    def test_restore_changes_nothing_when_the_saved_current_state_would_not_come_back(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / "unix.txt", b"CURRENT WORK\n")
        self.tool(p, "create", "01-current")                        # the current bytes are in the store now...
        self.damage(p, "01-current", "unix.txt", b"WRONG STORED BYTES\n")   # ...and damaged there
        before = disk_state(p)
        _, err = self.tool(p, "restore", "00-baseline", "--apply", expect=1)
        self.assertIn("pre-restore", err)
        self.assertEqual(disk_state(p), before)

    # ------------------------------------------------------------ G7 the tool writes only inside its own folder (F02)

    def test_every_command_refuses_a_store_whose_files_are_links_and_changes_nothing(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store, outside = self.store(p), self.tmp / "outside.txt"
        write(outside, b"KEEP\n")
        commands = (("create", "01-next"), ("verify", "00-baseline"), ("list",), ("diff", "00-baseline"),
                    ("tree", "00-baseline"), ("extract", "00-baseline", str(self.tmp / "out")),
                    ("restore", "00-baseline"), ("restore", "00-baseline", "--apply"))
        for name, target in (("info/attributes", p / "unix.txt"), ("info/exclude", p / ".env"), ("config", outside)):
            original = (store / name).read_bytes()
            (store / name).unlink()
            os.symlink(str(target), str(store / name))
            for command in commands:
                with self.subTest(link=name, command=command[0]):
                    before, kept = disk_state(p), outside.read_bytes()
                    self.tool(p, *command, expect=1)
                    self.assertEqual(disk_state(p), before)
                    self.assertEqual(outside.read_bytes(), kept)
                    self.assertFalse((self.tmp / "out").exists())
            (store / name).unlink()
            write(store / name, original)

    def test_links_and_redirections_in_the_state_folder_are_refused_before_anything_is_written(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        shapes = {   # name: (made before the first checkpoint?, how)
            "the state folder is a link": (True, lambda p: os.symlink(str(outside), str(p / STATE))),
            "the store is a link to the project's own repository": (
                True, lambda p: ((p / STATE).mkdir(), os.symlink(str(p / ".git"), str(self.store(p))))),
            "the ignore file is a dangling link": (
                True, lambda p: ((p / STATE).mkdir(), os.symlink(str(p / "created.txt"), str(p / STATE / ".gitignore")))),
            "a store folder is a link into the project": (
                False, lambda p: (shutil.rmtree(self.store(p) / "refs" / "checkpoints"),
                                  os.symlink(str(p / "src"), str(self.store(p) / "refs" / "checkpoints")))),
            "the store borrows the project's repository (commondir)": (
                False, lambda p: write(self.store(p) / "commondir", str(p / ".git").encode() + b"\n")),
            "the store borrows the project's objects (alternates)": (
                False, lambda p: write(self.store(p) / "objects" / "info" / "alternates",
                                       str(p / ".git" / "objects").encode() + b"\n")),
        }
        for number, (name, (first, make)) in enumerate(shapes.items()):
            with self.subTest(shape=name):
                p = self.git_project("shape-%d" % number)
                if not first:
                    self.tool(p, "create", "00-baseline")
                make(p)
                before = (disk_state(p), folder_digest(p / ".git"), folder_digest(outside))
                self.tool(p, "create", "01-next", expect=1)
                self.assertEqual((disk_state(p), folder_digest(p / ".git"), folder_digest(outside)), before)

    def test_a_store_file_that_is_another_name_for_a_project_file_is_replaced_not_written_through(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        attributes = self.store(p) / "info" / "attributes"
        attributes.unlink()
        os.link(str(p / "unix.txt"), str(attributes))   # one file under two names
        before = disk_state(p)
        self.tool(p, "verify", "00-baseline")
        self.assertEqual(disk_state(p), before)

    def test_a_store_file_with_a_second_name_outside_is_refused_and_git_appends_to_no_file(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store, outside = self.store(p), self.tmp / "outside.txt"
        with open(store / "config", "a") as config:
            config.write("[core]\n\tlogAllRefUpdates = always\n")   # the store asks git for a reference log
        oid = self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline:unix.txt")
        places = {   # where a second name for the outside file is made inside the store
            "a reference log": store / "logs" / "refs" / "checkpoints" / "01-next",
            "the reference log of HEAD": store / "logs" / "HEAD",
            "a deep reference": store / "refs" / "checkpoints" / "deep" / "er" / "label",
            "packed-refs": store / "packed-refs",
            "an object": store / "objects" / oid[:2] / oid[2:],
        }
        for name, place in places.items():
            with self.subTest(place=name):
                write(outside, b"KEEP THESE BYTES\n")
                kept = place.read_bytes() if place.exists() else None
                if place.exists():
                    os.chmod(place, stat.S_IWRITE | stat.S_IREAD)
                    place.unlink()
                place.parent.mkdir(parents=True, exist_ok=True)
                os.link(str(outside), str(place))
                for command in (("create", "01-next"), ("list",), ("verify", "00-baseline")):
                    before = disk_state(p)
                    _, err = self.tool(p, *command, expect=1)
                    self.assertIn("hard link", err)
                    self.assertEqual(outside.read_bytes(), b"KEEP THESE BYTES\n")
                    self.assertEqual(disk_state(p), before)
                place.unlink()
                if kept is not None:
                    write(place, kept)
        # Without a second name the reference log the store asks for is still never written.
        self.tool(p, "create", "01-next")
        self.assertFalse((store / "logs").exists() and any((store / "logs").rglob("01-next")))

    def test_an_existing_reference_log_takes_an_append_with_one_name_and_is_refused_before_any_write_with_two(self):
        # core.logAllRefUpdates=false only stops git creating a missing log: git still appends to one that exists (G7).
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store, outside = self.store(p), self.tmp / "outside.txt"
        log = store / "logs" / "refs" / "checkpoints" / "01-next"
        write(outside, b"KEEP THESE BYTES\n")
        log.parent.mkdir(parents=True, exist_ok=True)
        os.link(str(outside), str(log))                      # two names: the store's log and an outside file
        before = (disk_state(p), identities(store))
        _, err = self.tool(p, "create", "01-next", expect=1)
        self.assertIn("hard link", err)
        self.assertEqual(outside.read_bytes(), b"KEEP THESE BYTES\n")
        self.assertEqual((disk_state(p), identities(store)), before)   # refused before any write, in the store too
        log.unlink()
        write(log, b"KEEP THESE BYTES\n")                    # one name: the store's own file
        self.tool(p, "create", "01-next")
        self.assertEqual(outside.read_bytes(), b"KEEP THESE BYTES\n")
        appended = log.read_bytes()
        self.assertTrue(appended.startswith(b"KEEP THESE BYTES\n") and len(appended) > 17,
                        "git no longer appends to an existing log — recovery.md G7 can say so")

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX file permissions and a normal user")
    def test_a_store_folder_that_cannot_be_read_stops_every_command_before_a_write(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        store, outside = self.store(p), self.tmp / "outside.gitconfig"
        objects = store / "objects" / self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline:unix.txt")[:2]
        cases = {   # the folder that cannot be read: the link it hides
            "the store": store / "config",   # the config git config --file would write through
            "a deep reference folder": store / "refs" / "checkpoints" / "deep" / "hidden",
            "an object folder": objects / "hidden",
            "a reference log folder": store / "logs" / "refs" / "checkpoints" / "hidden",
        }
        for name, link in cases.items():
            locked = store if name == "the store" else link.parent
            with self.subTest(locked=name):
                write(outside, b"[core]\n\tautocrlf = true\n")
                original = link.read_bytes() if link.exists() else None
                link.parent.mkdir(parents=True, exist_ok=True)
                if original is not None:
                    link.unlink()
                os.symlink(str(outside), str(link))   # hidden once its folder cannot be listed
                os.chmod(locked, 0o300)
                try:
                    for command in (("list",), ("create", "01-next"), ("verify", "00-baseline"), ("diff", "00-baseline")):
                        before = disk_state(p)
                        _, err = self.tool(p, *command, expect=1)
                        self.assertIn("cannot read the folder", err)
                        self.assertEqual(outside.read_bytes(), b"[core]\n\tautocrlf = true\n")
                        self.assertEqual(disk_state(p), before)
                finally:
                    os.chmod(locked, 0o755)
                    link.unlink()
                    if original is not None:
                        write(link, original)
        self.tool(p, "verify", "00-baseline")

    # ------------------------------------------------------------ G11 no hook runs, no git setting bends a checkpoint (F03)

    def hostile_git(self, p):
        """Hooks for the events checkpoint commands could fire — configured globally, through the environment and as
        templates for new repositories — plus environment settings that would redirect git's own writes."""
        marker, hooks = self.tmp / "hook-ran.txt", self.tmp / "hooks"
        hooks.mkdir()
        for name in ("reference-transaction", "post-index-change", "post-checkout", "pre-commit", "post-commit",
                     "pre-auto-gc", "post-rewrite", "fsmonitor-watchman"):
            (hooks / name).write_text("#!/bin/sh\necho %s >> '%s'\n" % (name, marker))
            os.chmod(hooks / name, 0o755)
        shutil.copytree(str(hooks), str(self.tmp / "templates" / "hooks"))
        with open(self.home / "gitconfig", "a") as config:
            config.write("[core]\n\thooksPath = %s\n\tfsmonitor = %s\n[init]\n\ttemplateDir = %s\n"
                         % (hooks, hooks / "fsmonitor-watchman", self.tmp / "templates"))
        env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": str(hooks),
               "GIT_CONFIG": str(p / "unix.txt"), "GIT_TRACE": str(p / "trace.txt"),
               "GIT_TRACE2_EVENT": str(p / "trace2.txt")}
        return marker, env

    def test_no_hook_runs_and_no_git_setting_makes_the_tool_write_anywhere_else(self):
        p = self.git_project()                        # built before the hostile settings exist
        marker, env = self.hostile_git(p)
        before = disk_state(p)
        for command in (("create", "00-baseline"), ("verify", "00-baseline"), ("list",), ("diff", "00-baseline"),
                        ("tree", "00-baseline"), ("tree", "--current"), ("restore", "00-baseline"),
                        ("extract", "00-baseline", str(self.tmp / "out"))):
            with self.subTest(command=command[0]):
                self.tool(p, *command, env=env)
                self.assertFalse(marker.exists(), "a hook ran: %s" % (marker.read_text() if marker.exists() else ""))
                self.assertEqual(disk_state(p), before)
        write(p / "unix.txt", b"changed\n")
        self.tool(p, "restore", "00-baseline", "--apply", env=env)
        self.assertEqual(disk_state(p), before)
        self.assertFalse(marker.exists(), "a hook ran: %s" % (marker.read_text() if marker.exists() else ""))
        self.assertFalse((self.store(p) / "hooks").exists(), "the store was created from a template")

    def test_the_executable_bit_and_links_survive_git_settings_that_would_drop_them(self):
        for setting in ("filemode", "symlinks"):
            with self.subTest(setting=setting):
                p = self.git_project(setting)
                (self.home / "gitconfig").write_text(HOSTILE_GITCONFIG + "[core]\n\t%s = false\n" % setting)
                env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core." + setting, "GIT_CONFIG_VALUE_0": "false"}
                good = disk_state(p)
                self.tool(p, "create", "00-baseline", env=env)
                out = self.tmp / ("extracted-" + setting)
                self.tool(p, "extract", "00-baseline", str(out), env=env)
                self.assertEqual(disk_state(out), self.without(good, ".env", "node_modules"))
                self.tool(p, "verify", "00-baseline", env=env)
                os.chmod(p / "run.sh", 0o644)
                (p / "link.js").unlink()
                write(p / "link.js", b"no longer a link\n")
                self.tool(p, "restore", "00-baseline", "--apply", env=env)
                self.assertEqual(disk_state(p), good)

    # ------------------------------------------------------------ G1 names exactly as the disk spells them (F05)

    def test_a_rename_that_only_changes_letter_case_is_saved_under_its_one_real_name_and_restored(self):
        if not case_insensitive_disk(self.tmp):
            self.skipTest("this file system tells letter cases apart")
        renames = (("Ä.txt", "ä.txt", None), ("Ä", "ä", "x.txt"), ("Guide", "guide", "x.txt"))
        for number, (old, new, inside) in enumerate(renames):
            for kind in ("git", "plain"):
                with self.subTest(rename=old + " -> " + new, project=kind):
                    p = (self.git_project if kind == "git" else self.plain_project)("case-%d-%s" % (number, kind))
                    old_file = p / old / inside if inside else p / old
                    write(old_file, b"the same bytes\n")
                    if kind == "git":
                        self.git(p, "add", str(old_file.relative_to(p)))
                    self.tool(p, "create", "00-baseline")
                    good = disk_state(p)
                    os.rename(p / old, p / "tmp-name")
                    os.rename(p / "tmp-name", p / new)
                    renamed = disk_state(p)
                    self.tool(p, "create", "01-renamed")
                    self.tool(p, "verify", "01-renamed")
                    saved = self.store_git(p, "ls-tree", "-r", "--name-only", "-z", "refs/checkpoints/01-renamed")
                    self.assertEqual(sorted(saved.strip("\0").split("\0")),
                                     sorted(self.without(renamed, ".env", "node_modules", "debug.log", "__pycache__")))
                    self.tool(p, "restore", "00-baseline", "--apply")
                    self.assertEqual(disk_state(p), good)

    def test_a_name_the_disk_keeps_decomposed_is_saved_and_extracted_with_its_exact_bytes(self):
        name = unicodedata.normalize("NFD", "café.txt")   # 'e' followed by a combining accent
        p = self.git_project()
        write(p / name, b"decomposed name\n")
        self.git(p, "add", name)
        self.tool(p, "create", "00-baseline")
        out = self.tmp / "extracted"
        self.tool(p, "extract", "00-baseline", str(out))
        self.assertEqual(sorted(n for n in os.listdir(os.fsencode(str(out))) if n.startswith(b"caf")),
                         sorted(n for n in os.listdir(os.fsencode(str(p))) if n.startswith(b"caf")))

    def test_verify_fails_a_checkpoint_holding_two_names_for_one_file_on_this_disk(self):
        if not case_insensitive_disk(self.tmp):
            self.skipTest("this file system tells letter cases apart")
        p = self.plain_project()
        self.tool(p, "create", "00-baseline")
        # the same bytes under two names: extracted here they become one file that reads back right under either name
        self.plant(p, "01-two-names", {"Ä.txt": b"same\n", "ä.txt": b"same\n"})
        _, err = self.tool(p, "verify", "01-two-names", expect=1)
        self.assertIn("did not come back identical", err)

    # ------------------------------------------------------------ G1 complete, or no checkpoint at all (F06)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX folder permissions and a normal user")
    def test_create_refuses_when_a_folder_or_file_cannot_be_read(self):
        for kind in ("git", "plain"):
            for locked in ("locked", "locked-file.txt"):
                with self.subTest(project=kind, unreadable=locked):
                    p = (self.git_project if kind == "git" else self.plain_project)("%s-%s" % (kind, locked))
                    write(p / "locked" / "unsaved.txt" if locked == "locked" else p / locked, b"important work\n")
                    os.chmod(p / locked, 0o000)
                    try:
                        _, err = self.tool(p, "create", "00-baseline", expect=1)
                    finally:
                        os.chmod(p / locked, 0o755)
                    self.assertIn("locked", err)
                    out, _ = self.tool(p, "list")
                    self.assertIn("no checkpoints yet", out)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX file permissions and a normal user")
    def test_create_refuses_when_git_cannot_read_an_ignore_file(self):
        p = self.git_project()
        excludes = self.home / "excludes"
        write(excludes, b"*.secret\n")
        with open(self.home / "gitconfig", "a") as config:
            config.write("[core]\n\texcludesFile = %s\n" % excludes)
        write(p / "keys.secret", b"SECRET=1\n")   # ignored for this user — unless git cannot read the rule
        os.chmod(excludes, 0o000)
        try:
            _, err = self.tool(p, "create", "00-baseline", expect=1)
        finally:
            os.chmod(excludes, 0o644)
        self.assertIn("excludes", err)

    def test_create_refuses_when_git_leaves_a_file_out_without_saying_so(self):
        if not case_insensitive_disk(self.tmp):
            self.skipTest("this file system tells letter cases apart")
        p = self.git_project()
        write(p / "docs" / ".GIT", b"real work that git treats as its own folder name and skips\n")
        _, err = self.tool(p, "create", "00-baseline", expect=1)
        self.assertIn("docs/.GIT", err)

    def test_nested_repositories_are_named_and_refused_while_they_hold_unsaved_work(self):
        p = self.git_project()
        tracked, untracked = p / "module", p / "tools"
        for nested in (tracked, untracked):
            nested.mkdir()
            self.git(nested, "init", "-q")
            write(nested / "code.txt", b"committed\n")
            self.git(nested, "add", "code.txt")
            self.git(nested, "commit", "-qm", "nested")
        self.git(p, "add", "module")                   # the project tracks one of them (a gitlink)
        self.git(p, "commit", "-qm", "link the module")
        _, err = self.tool(p, "create", "00-clean")
        self.assertIn("module", err)
        self.assertIn("tools", err)
        for nested in (tracked, untracked):
            for unsaved in ("code.txt", "untracked.txt"):
                with self.subTest(nested=nested.name, unsaved=unsaved):
                    original = (nested / unsaved).read_bytes() if (nested / unsaved).exists() else None
                    write(nested / unsaved, b"UNSAVED WORK\n")
                    _, err = self.tool(p, "create", "01-%s-%s" % (nested.name, unsaved.split(".")[0]), expect=1)
                    self.assertIn(nested.name, err)
                    if original is None:
                        (nested / unsaved).unlink()
                    else:
                        write(nested / unsaved, original)
        shutil.rmtree(untracked)                        # a phase deleted a nested repository
        out, _ = self.tool(p, "diff", "00-clean", expect=3)
        self.assertRegex(out, r"gone\s+tools/")

    # ------------------------------------------------------------ G10 every ignored file is watched (F07)

    def test_losing_one_ignored_file_inside_a_kept_ignored_folder_is_reported(self):
        for p in (self.git_project(), self.plain_project()):
            with self.subTest(project=p.name):
                write(p / ".gitignore", b"node_modules/\n.env\n*.log\ndata/\n")
                write(p / "data" / "main.db", b"the database\n")
                write(p / "data" / "keep.txt", b"still here\n")
                self.tool(p, "create", "00-baseline")
                (p / "data" / "main.db").unlink()
                out, _ = self.tool(p, "diff", "00-baseline", expect=3)
                self.assertRegex(out, r"gone\s+data/main\.db")
                self.assertNotIn("keep.txt", out)
                out, _ = self.tool(p, "restore", "00-baseline")
                self.assertIn("cannot bring them back", out)
                self.assertIn("data/main.db", out)

    # ------------------------------------------------------------ G11 checking a nested repository runs nothing (F03)

    def test_checking_a_nested_repository_runs_no_filter_program_yet_finds_a_same_size_edit(self):
        p = self.git_project()
        module = self.repository(p / "module", {"code.txt": b"COMMITTED\n", ".gitattributes": b"*.txt filter=review\n"})
        self.tool(p, "create", "00-clean")
        marker, program = self.tmp / "filter-ran.txt", self.tmp / "review-filter.sh"
        program.write_text("#!/bin/sh\necho ran >> '%s'\ncat\n" % marker)
        os.chmod(program, 0o755)
        with open(self.home / "gitconfig", "a") as config:   # the user's own settings name a filter program
            config.write('[filter "review"]\n\tclean = %s\n' % program)
        write(module / "code.txt", b"OTHERDATA\n")           # the same size as COMMITTED...
        later = os.stat(module / "code.txt").st_mtime + 60
        os.utime(module / "code.txt", (later, later))        # ...and a newer time: git would re-read the file
        before = disk_state(p)
        for command in (("create", "01-dirty"), ("diff", "00-clean"), ("restore", "00-clean"),
                        ("restore", "00-clean", "--apply")):
            with self.subTest(command=" ".join(command)):
                _, err = self.tool(p, *command, expect=1)
                self.assertFalse(marker.exists(), "a filter program from the git settings ran")
                self.assertIn("module/: changed code.txt", err)
                self.assertEqual(disk_state(p), before)

    def test_a_nested_repository_is_compared_with_its_own_index_and_every_kind_of_unsaved_work_is_refused(self):
        def converted(p):   # git writes code.txt back as one\r\ntwo\r\n: bytes that differ from git's copy, unchanged
            module = self.repository(p / "module", {"code.txt": b"one\ntwo\n", "keep.txt": b"keep\n",
                                                    ".gitattributes": b"code.txt text eol=crlf\n"})
            (module / "code.txt").unlink()
            self.git(module, "checkout", "--", "code.txt")
            return module

        def ignored_inside(m):   # a repository nested in the nested one, and ignored there
            write(m / ".gitignore", b"deps/\n")
            self.git(m, "add", ".gitignore")
            self.git(m, "commit", "-qm", "ignore deps")
            write(self.repository(m / "deps" / "lib", {"a.txt": b"a\n"}) / "a.txt", b"changed\n")

        def submodule_moved(m):   # a submodule of the nested one, checked out at another commit than it records
            sub = self.repository(m / "sub", {"s.txt": b"s\n"})
            self.git(m, "add", "sub")
            self.git(m, "commit", "-qm", "add sub")
            write(sub / "s.txt", b"newer\n")
            self.git(sub, "commit", "-qam", "newer")

        def never_committed(m):
            write(m.parent / "fresh" / "a.txt", b"a\n")
            self.git(m.parent / "fresh", "init", "-q")
            self.git(m.parent / "fresh", "add", "a.txt")

        def not_its_own(m):   # the parent tracks it, but its .git is no repository: git would read the parent's
            self.git(m.parent, "add", "module")
            os.rename(m / ".git", self.tmp / ("moved-git-%d" % len(os.listdir(self.tmp))))
            (m / ".git").mkdir()

        p = self.git_project()
        module = converted(p)
        self.assertEqual((module / "code.txt").read_bytes(), b"one\r\ntwo\r\n")
        self.tool(p, "create", "00-clean")                    # nothing changed there: not refused
        cases = {
            "module/: staged changes": lambda m: (write(m / "keep.txt", b"staged\n"), self.git(m, "add", "keep.txt")),
            "module/: deleted keep.txt": lambda m: (m / "keep.txt").unlink(),
            "module/: untracked new.txt": lambda m: write(m / "new.txt", b"new\n"),
            "module/: changed code.txt": lambda m: write(m / "code.txt", b"one\r\ntwo\r\nthree\r\n"),
            "module/deps/lib/: changed a.txt": ignored_inside,
            "module/: sub is not at the commit module/ records": submodule_moved,
            "fresh/: files added but never committed": never_committed,
            "another repository": not_its_own,
        }
        if os.name != "nt":
            cases["module/: changed keep.txt"] = lambda m: os.chmod(m / "keep.txt", 0o755)   # only its executable bit
        for number, (words, unsaved) in enumerate(cases.items()):
            with self.subTest(work=words):
                p = self.git_project("work-%d" % number)
                unsaved(converted(p))
                before = disk_state(p)
                _, err = self.tool(p, "create", "01-work", expect=1)
                self.assertIn(words, err)
                self.assertEqual(disk_state(p), before)

    # ------------------------------------------------------------ G1 an ignored nested repository is checked (F06)

    def test_an_ignored_nested_repository_is_named_recorded_checked_and_watched(self):
        for kind in ("git", "plain"):
            for place in ("module", "vendor/lib"):   # ignored itself, or inside an ignored folder
                with self.subTest(project=kind, repository=place):
                    p = (self.git_project if kind == "git" else self.plain_project)(
                        "%s-%s" % (kind, place.replace("/", "-")))
                    write(p / ".gitignore", (p / ".gitignore").read_bytes() + b"module/\nvendor/\n")
                    module = self.repository(p / place, {"code.txt": b"committed\n"})
                    _, err = self.tool(p, "create", "00-clean")
                    self.assertIn("nested repository %s/" % place, err)
                    message = self.store_git(p, "cat-file", "commit", "refs/checkpoints/00-clean")
                    self.assertIn('nested-repositories: ["%s/"]' % place, message)
                    for unsaved in ("code.txt", "new.txt"):
                        write(module / unsaved, b"UNSAVED WORK\n")
                        before, kept = disk_state(p), folder_digest(module / ".git")
                        _, err = self.tool(p, "create", "01-unsaved", expect=1)
                        self.assertIn("%s/: %s %s" % (place, "changed" if unsaved == "code.txt" else "untracked",
                                                      unsaved), err)
                        self.assertEqual(disk_state(p), before)
                        self.assertEqual(folder_digest(module / ".git"), kept)
                        if unsaved == "code.txt":
                            write(module / unsaved, b"committed\n")
                        else:
                            (module / unsaved).unlink()
                    shutil.rmtree(module)                    # a phase deleted it
                    out, _ = self.tool(p, "diff", "00-clean", expect=3)
                    self.assertEqual(re.findall(r"^\s+gone\s+(\S+)$", out, re.M), [place + "/"])   # once, not twice

    # ------------------------------------------------------------ G1 a repository git will not open is not a plain folder (NEW-1)

    def test_a_repository_git_refuses_to_open_stops_every_command_instead_of_losing_tracked_files(self):
        p = self.git_project()
        write(p / "tracked.log", b"tracked, and matched by an ignore rule added later\n")
        self.git(p, "add", "tracked.log")
        self.git(p, "commit", "-qm", "log")
        write(p / ".gitignore", b"node_modules/\n.env\n*.log\n")
        other_owner = {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}   # git's own switch for "another user's folder"
        before = disk_state(p, skip=())
        for command in (("create", "00-baseline"), ("tree", "--current")):
            with self.subTest(command=command[0]):
                _, err = self.tool(p, *command, expect=1, env=other_owner)
                self.assertIn("dubious ownership", err)
                self.assertEqual(disk_state(p, skip=()), before)
        self.tool(p, "create", "00-baseline")                 # opened normally, the tracked file is saved
        out = self.tmp / "extracted"
        self.tool(p, "extract", "00-baseline", str(out))
        self.assertIn("tracked.log", disk_state(out))
        for command in (("verify", "00-baseline"), ("list",), ("diff", "00-baseline"), ("restore", "00-baseline")):
            with self.subTest(command=command[0]):
                _, err = self.tool(p, *command, expect=1, env=other_owner)
                self.assertIn("dubious ownership", err)


if __name__ == "__main__":
    unittest.main()
