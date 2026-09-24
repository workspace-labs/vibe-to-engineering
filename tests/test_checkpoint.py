"""Conformance tests for the recovery contract (skills/vibe-to-engineering/references/recovery.md): the store,
the snapshots, verify, diff, restore, and what the tool refuses.

Run from the repository root:  python3 -m unittest discover -s tests -v
Nested repositories, the ignored files that are watched, and the tree view have their own test modules.
"""

import os
import re
import shutil
import stat
import unicodedata
import unittest
import zlib
from pathlib import Path
from support import Fixture, HOSTILE_GITCONFIG, STATE, case_insensitive_disk, disk_state, folder_digest, identities, write


class Contract(Fixture):
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

    # ------------------------------------------------------------ the safety checks a change at the wrong moment trips (item 9)

    def test_a_file_that_changes_while_it_is_being_saved_refuses_the_snapshot(self):
        p = self.git_project()

        def inject(tool):
            real = tool.git

            def git(args, **kwargs):
                done = real(args, **kwargs)
                if args[0] == "write-tree":   # saved, not yet compared with the disk
                    write(p / "unix.txt", b"changed while it was being saved\n")
                return done
            tool.git = git
        code, err = self.in_process(p, ["create", "00-baseline"], inject)
        self.assertEqual(code, 1, err)
        self.assertIn("the snapshot does not match the files on disk (unix.txt)", err)
        out, _ = self.tool(p, "list")
        self.assertIn("no checkpoints yet", out)

    def test_a_file_edited_after_a_restore_was_verified_stops_it_before_anything_changes(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / "unix.txt", b"work since the checkpoint\n")

        def inject(tool):
            real, calls = tool.verify_commit, []

            def verify_commit(*args):
                count = real(*args)
                calls.append(args)
                if len(calls) == 2:           # both recovery points proven, the project not yet re-checked
                    write(p / "late.txt", b"written after the restore was verified\n")
                return count
            tool.verify_commit = verify_commit
        code, err = self.in_process(p, ["restore", "00-baseline", "--apply"], inject)
        self.assertEqual(code, 1, err)
        self.assertIn("the project changed while the restore was being prepared", err)
        self.assertEqual((p / "late.txt").read_bytes(), b"written after the restore was verified\n")
        self.assertEqual((p / "unix.txt").read_bytes(), b"work since the checkpoint\n")

    def test_a_store_configured_as_a_partial_clone_is_refused(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        with open(self.store(p) / "config", "a") as config:
            config.write('[extensions]\n\tpartialClone = origin\n[remote "origin"]\n\tpromisor = true\n')
        for command in (("list",), ("verify", "00-baseline"), ("create", "01-next")):
            with self.subTest(command=command[0]):
                _, err = self.tool(p, *command, expect=1)
                self.assertIn("configured as a partial clone", err)

    # ------------------------------------------------------------ G1 a repository git will not open is not a plain folder (NEW-1)

    def test_a_broken_git_pointer_is_refused_not_read_as_a_plain_folder(self):
        p = self.git_project()
        write(p / "tracked.log", b"tracked, and matched by an ignore rule\n")
        self.git(p, "add", "tracked.log")
        self.git(p, "commit", "-qm", "log")
        write(p / ".gitignore", b"node_modules/\n.env\n*.log\n")
        os.rename(p / ".git", self.tmp / "saved-git")
        write(p / ".git", b"gitdir: " + os.fsencode(str(self.tmp / "nonexistent-repository")) + b"\n")
        before = disk_state(p, skip=())
        for command in (("create", "00-baseline"), ("tree", "--current")):
            with self.subTest(command=command[0]):
                _, err = self.tool(p, *command, expect=1)
                self.assertIn("cannot open the repository at", err)
                self.assertEqual(disk_state(p, skip=()), before)
        self.assertFalse((p / STATE).exists(), "a checkpoint store was created")
        write(p / "sub" / "a.txt", b"a\n")                      # a folder inside it: the same broken pointer above
        _, err = self.tool(p / "sub", "tree", "--current", expect=1)
        self.assertIn("cannot open the repository at", err)

    @unittest.skipIf(os.name == "nt", "the stand-in git is a shell script")
    def test_a_failure_to_open_that_is_not_a_missing_repository_stops_a_plain_folder_too(self):
        p = self.plain_project()
        stand_in = self.tmp / "bin" / "git"          # answers the one question itself, hands the rest to real git
        stand_in.parent.mkdir()
        env = {"PATH": str(stand_in.parent) + os.pathsep + self.env["PATH"]}
        for words, expect in (("fatal: unable to read current working directory: Operation not permitted", 1),
                              ("fatal: not a git repository (or any parent up to mount point /)", 0)):
            with self.subTest(words):
                stand_in.write_text('#!/bin/sh\ncase "$*" in *--is-inside-work-tree*) echo "%s" >&2; exit 128;; esac\n'
                                    'exec "%s" "$@"\n' % (words, shutil.which("git")))
                os.chmod(stand_in, 0o755)
                _, err = self.tool(p, "create", "00-baseline", expect=expect, env=env)
                if expect:
                    self.assertIn("cannot open the repository this folder belongs to", err)
                    self.assertFalse((p / STATE).exists())
                else:                                      # git's own words for "no repository": a plain folder
                    self.assertTrue((p / STATE).is_dir())

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
