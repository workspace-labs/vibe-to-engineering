"""Ignored files: watched, not saved (recovery.md G10) — reported when they disappear or change, with secrets
never read into any output.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import hashlib
import os
import re
import stat
import subprocess
import unittest
from pathlib import Path
from support import Fixture, STATE, write

# Genuine checkpoints two older tools wrote over one project (main.txt, and .env and node_modules/ignored.js ignored):
# the exact bytes of the commit objects, read back from the reviewer's stores with `git cat-file commit`. 8eeba3a wrote
# the first two, before content records existed; 1f35614 the last two, recording .env's modification time.
OLD_TREE = "4a3435b30732c8e8fafd7a1503b85a897fa352a5"
OLD_MTIME = 1790278174664916874
GENUINE_OLD_CHECKPOINTS = (  # the label it gets here, the id the archived tool gave it, its exact bytes
    ("pre-a", "e99e8326d21f8e624d605222a00767c4470c21c9",
     b"tree 4a3435b30732c8e8fafd7a1503b85a897fa352a5\n"
     b"author vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278173 +0400\n"
     b"committer vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278173 +0400\n\n"
     b"vibe-to-engineering checkpoint: old-a\n\n"
     b'ignored-by-git: [".env", "node_modules/ignored.js"]\nnested-repositories: []\n'),
    ("pre-b", "5588718c92d8c748d78a1ce9729061cf2c3b71b6",
     b"tree 4a3435b30732c8e8fafd7a1503b85a897fa352a5\n"
     b"author vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278173 +0400\n"
     b"committer vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278173 +0400\n\n"
     b"vibe-to-engineering checkpoint: old-b\n\n"
     b'ignored-by-git: [".env", "node_modules/ignored.js"]\nnested-repositories: []\n'),
    ("mtime-a", "7a958e18a89ec2fbccaa3c36585ff28851b35fd3",
     b"tree 4a3435b30732c8e8fafd7a1503b85a897fa352a5\n"
     b"author vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278174 +0400\n"
     b"committer vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278174 +0400\n\n"
     b"vibe-to-engineering checkpoint: old-a\n\n"
     b'ignored-by-git: [".env", "node_modules/ignored.js"]\nnested-repositories: []\n'
     b'ignored-contents: {".env": [31, "mtime:1790278174664916874"]}\n'),
    ("mtime-b", "3742c63d63bcc64fe1364804e40b8c895f87c32a",
     b"tree 4a3435b30732c8e8fafd7a1503b85a897fa352a5\n"
     b"author vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278174 +0400\n"
     b"committer vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790278174 +0400\n\n"
     b"vibe-to-engineering checkpoint: old-b\n\n"
     b'ignored-by-git: [".env", "node_modules/ignored.js"]\nnested-repositories: []\n'
     b'ignored-contents: {".env": [31, "mtime:1790278174664916874"]}\n'),
)
# Genuine checkpoints 8eeba3a wrote over one git project holding main.txt, while x/ was a nested repository git did not
# ignore (m-a), one it ignored through .git/info/exclude (n-a), and a plain ignored folder (n-b): the first two list
# only the folder, as one entry, so x/inner.txt was there but not even named.
FOLDER_TREE = "d82c6de209406e287a81e0436aff5641422a93e3"
GENUINE_FOLDER_CHECKPOINTS = tuple(
    (label, genuine, b"tree d82c6de209406e287a81e0436aff5641422a93e3\n"
     b"author vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790293414 +0400\n"
     b"committer vibe-to-engineering <checkpoint@vibe-to-engineering.invalid> 1790293414 +0400\n\n"
     b"vibe-to-engineering checkpoint: " + label.encode() + b"\n\n" + lines)
    for label, genuine, lines in (
        ("m-a", "73aa5fd5e448541507d31293a53727c0774296f0", b'ignored-by-git: []\nnested-repositories: ["x/"]\n'),
        ("n-a", "66dd021c782a526ff046bf2f65ba8fc36f519b3c", b'ignored-by-git: ["x/"]\nnested-repositories: ["x/"]\n'),
        ("n-b", "86462ab61cacc216f62c55453deefded91aae7fd",
         b'ignored-by-git: ["x/inner.txt"]\nnested-repositories: []\n')))


class Watched(Fixture):
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

    # ------------------------------------------------------------ G10 a real-sized ignored folder (found trying a real project)

    def test_a_project_whose_ignored_file_names_run_to_megabytes_is_saved(self):
        p = self.git_project()
        folder = p / "build" / ("d" * 200)   # build/ is ignored below; 4,200 names of about 300 bytes: over 1.2 MB
        folder.mkdir(parents=True)
        for number in range(4200):
            (folder / ("%05d-%s.txt" % (number, "n" * 80))).touch()
        write(p / ".gitignore", b"node_modules/\n.env\nbuild/\n")
        self.tool(p, "create", "00-baseline")      # the list of ignored files is far past one command-line argument
        message = self.store_git(p, "cat-file", "commit", "refs/checkpoints/00-baseline")
        self.assertEqual(message.count("/%s/" % ("d" * 200)), 4200)
        out, _ = self.tool(p, "diff", "00-baseline")
        self.assertIn("no changes", out)

    def test_an_ignored_file_lost_during_a_restore_is_reported(self):
        p = self.git_project()
        self.tool(p, "create", "00-baseline")
        write(p / "unix.txt", b"work since the checkpoint\n")

        def inject(tool):
            real = tool.write_files

            def write_files(store, commit, target, paths=None):
                real(store, commit, target, paths)
                if Path(target) == p:         # the restore wrote the project's files
                    (p / ".env").unlink()
            tool.write_files = write_files
        code, err = self.in_process(p, ["restore", "00-baseline", "--apply"], inject)
        self.assertEqual(code, 1, err)
        self.assertIn("the restore did not complete", err)
        self.assertIn("lost: .env", err)

    # ------------------------------------------------------------ G10 an ignored file whose contents changed is noticed (RA-03)

    def test_an_ignored_file_whose_contents_changed_is_reported_though_no_checkpoint_holds_it(self):
        for p in (self.git_project(), self.plain_project()):
            with self.subTest(project=p.name):
                write(p / ".gitignore", (p / ".gitignore").read_bytes() + b"*.db\n")
                write(p / "data.db", b"ROWS: 5\n")                     # the owner's database, ignored
                self.tool(p, "create", "00-baseline")
                for data, report in ((b"ROWS: 0  (wiped by a check)\n", r"changed\s+data\.db\s+\(28 bytes, was 8\)"),
                                     (b"ROWS: 9\n", r"changed\s+data\.db\s+\(the same size\)")):
                    write(p / "data.db", data)
                    out, _ = self.tool(p, "diff", "00-baseline", expect=3)
                    self.assertRegex(out, report)
                    out, _ = self.tool(p, "restore", "00-baseline")    # reported before a restore changes anything
                    self.assertRegex(out, report)
                    self.assertEqual((p / "data.db").read_bytes(), data)
                write(p / "data.db", b"ROWS: 5\n")                     # the same bytes again: nothing to report
                write(next((p / "node_modules").rglob("index.js")), b"a dependency changed\n")   # not watched
                out, _ = self.tool(p, "diff", "00-baseline")
                self.assertIn("no changes", out)
                watched = self.store_git(p, "cat-file", "commit", "refs/checkpoints/00-baseline").split(
                    "ignored-contents: ")[1]
                self.assertIn('"data.db": [8, "sha256:', watched)
                self.assertNotIn("node_modules", watched)
                if p.name == "project":                                 # a file with secrets: a keyed fingerprint
                    self.assertRegex(watched, r'"\.env": \[9, "hmac:[0-9a-f]{64}"\]')
                    self.assertNotIn(hashlib.sha256(b"SECRET=1\n").hexdigest(), watched)
                    write(p / ".env", b"SECRET=2\n")
                    out, _ = self.tool(p, "diff", "00-baseline", expect=3)
                    self.assertRegex(out, r"changed\s+\.env\s+\(the same size\)")

    def test_a_secret_file_replaced_with_the_same_size_and_time_is_reported_changed_and_never_hashed_plainly(self):
        p = self.git_project()                                   # .env is ignored
        write(p / ".env", b"SECRET_KEY=fixture-first-value\n")
        self.tool(p, "create", "00-baseline")
        info = os.stat(p / ".env")
        write(p / ".env", b"SECRET_KEY=fixture-other-value\n")  # the same size...
        os.utime(p / ".env", ns=(info.st_atime_ns, info.st_mtime_ns))   # ...and the same modification time
        out, _ = self.tool(p, "diff", "00-baseline", expect=3)
        self.assertRegex(out, r"changed\s+\.env\s+\(the same size\)")
        out, _ = self.tool(p, "restore", "00-baseline")
        self.assertRegex(out, r"changed\s+\.env")
        write(p / ".env", b"SECRET_KEY=fixture-first-value\n")
        os.utime(p / ".env", ns=(info.st_atime_ns, info.st_mtime_ns))
        out, _ = self.tool(p, "diff", "00-baseline")
        self.assertIn("no changes", out)
        message = self.store_git(p, "cat-file", "commit", "refs/checkpoints/00-baseline")
        self.assertNotIn("fixture-first-value", message)
        self.assertRegex(message, r'"\.env": \[31, "hmac:[0-9a-f]{64}"\]')       # keyed, so it tells nothing...
        self.assertNotIn(hashlib.sha256(b"SECRET_KEY=fixture-first-value\n").hexdigest(), message)  # ...unlike a hash
        key = p / STATE / "fingerprint.key"
        self.assertTrue(key.is_file())
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(os.stat(key).st_mode), 0o600)
        self.assertNotIn("fingerprint.key", self.store_git(p, "ls-tree", "-r", "--name-only", "refs/checkpoints/00-baseline"))
        key.unlink()                                             # the key file is guarded like the store (G7)
        os.symlink(str(self.tmp / "elsewhere"), str(key))
        _, err = self.tool(p, "diff", "00-baseline", expect=1)
        self.assertIn("fingerprint.key is a link", err)

    def test_an_older_checkpoint_that_cannot_vouch_for_a_secret_file_never_calls_it_unchanged(self):
        p = self.git_project()                                   # .env is ignored and watched; node_modules is not watched
        write(p / ".env", b"SECRET_KEY=fixture-first-value\n")
        self.tool(p, "create", "00-baseline")
        info = os.stat(p / ".env")
        tree = self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline^{tree}")
        # two checkpoints an older tool wrote over the same files: one recorded the secret file's modification time
        # (the store format before keyed fingerprints), one recorded nothing about any file's contents
        for label, record in (("01-mtime", 'ignored-contents: {".env": [31, "mtime:%d"]}\n' % info.st_mtime_ns),
                              ("02-nothing", ""),
                              ("03-mtime-too", 'ignored-contents: {".env": [31, "mtime:%d"]}\n' % info.st_mtime_ns)):
            commit = self.store_git(p, "commit-tree", tree, "-m", "vibe-to-engineering checkpoint: %s\n\n"
                                    'ignored-by-git: [".env", "node_modules/pkg/index.js"]\nnested-repositories: []\n%s'
                                    % (label, record))
            self.store_git(p, "update-ref", "refs/checkpoints/" + label, commit)
        outputs = []
        for data in (b"SECRET_KEY=fixture-first-value\n", b"SECRET_KEY=fixture-other-value\n"):
            write(p / ".env", data)                              # the same bytes, then other bytes of the same size...
            os.utime(p / ".env", ns=(info.st_atime_ns, info.st_mtime_ns))   # ...under the recorded modification time
            for label, why in (("01-mtime", "01-mtime recorded only its modification time"),
                               ("02-nothing", "02-nothing recorded nothing about its contents")):
                with self.subTest(label=label, bytes=data.decode()):
                    out, _ = self.tool(p, "diff", label, expect=3)   # never "no changes": nothing vouches for .env
                    self.assertRegex(out, r"unknown\s+\.env\s+\(%s" % why)
                    self.assertNotIn("node_modules", out)            # an unwatched file is not in question
                    outputs.append(out)
                    for route in ((), ("--apply",)):
                        out, _ = self.tool(p, "restore", label, *route)
                        self.assertRegex(out, r"cannot bring back.*\n.*\n\s+unknown\s+\.env")
                        outputs.append(out)
                    self.assertEqual((p / ".env").read_bytes(), data)
        out, _ = self.tool(p, "diff", "00-baseline", "02-nothing", expect=3)   # whichever side recorded nothing
        self.assertRegex(out, r"unknown\s+\.env\s+\(02-nothing recorded nothing")
        outputs.append(out)
        out, _ = self.tool(p, "diff", "01-mtime", "03-mtime-too", expect=3)   # two equal times prove nothing either
        self.assertRegex(out, r"unknown\s+\.env\s+\(01-mtime recorded only its modification time")
        outputs.append(out)
        for out in outputs + [self.store_git(p, "cat-file", "commit", "refs/checkpoints/00-baseline")]:
            self.assertNotIn("fixture-", out)                       # no secret byte in any output or record

    def test_two_checkpoints_from_an_older_tool_are_never_called_unchanged_in_either_direction(self):
        p = self.tmp / "legacy"                                  # the project the older tools saved (NEW-6)
        write(p / "main.txt", b"source stays the same\n")
        write(p / ".gitignore", b".env\nnode_modules/\n")
        write(p / "node_modules" / "ignored.js", b"dependency\n")          # ignored, not watched
        write(p / ".env", b"SECRET_KEY=fixture-first-value\n")             # ignored and watched
        self.tool(p, "create", "00-baseline")                    # a store holding the tree the older tools saved
        self.assertEqual(self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline^{tree}"), OLD_TREE)

        def raw(commit):                                         # a stored commit's exact bytes
            return subprocess.run(["git", "--git-dir=" + str(self.store(p)), "cat-file", "commit", commit],
                                  env=self.env, check=True, stdout=subprocess.PIPE).stdout
        for label, genuine, data in GENUINE_OLD_CHECKPOINTS:     # the very objects the archived tools wrote
            self.assertEqual(self.store_git(p, "hash-object", "-t", "commit", "-w", "--stdin", data=data), genuine)
            self.store_git(p, "update-ref", "refs/checkpoints/" + label, genuine)
        baseline = raw("refs/checkpoints/00-baseline")
        write(p / ".env", b"SECRET_KEY=fixture-other-value\n")             # other bytes of the same size...
        os.utime(p / ".env", ns=(OLD_MTIME, OLD_MTIME))                    # ...under the time 1f35614 recorded
        outputs = []
        for old, new, why in (("pre-a", "pre-b", "neither pre-a nor pre-b recorded anything about its contents"),
                              ("pre-b", "pre-a", "neither pre-b nor pre-a recorded anything about its contents"),
                              ("mtime-a", "mtime-b", "mtime-a recorded only its modification time"),
                              ("mtime-b", "mtime-a", "mtime-b recorded only its modification time"),
                              ("pre-a", "mtime-b", "pre-a recorded nothing about its contents"),
                              ("mtime-b", "pre-a", "pre-a recorded nothing about its contents"),
                              ("pre-a", None, "pre-a recorded nothing about its contents")):
            with self.subTest(old=old, new=new):
                out, _ = self.tool(p, "diff", old, *([new] if new else []), expect=3)   # never "no changes"
                self.assertRegex(out, r"unknown\s+\.env\s+\(%s" % re.escape(why))
                self.assertNotIn("no changes", out)
                outputs.append(out)
        for route in ((), ("--apply",)):                         # the source already matches pre-a
            out, _ = self.tool(p, "restore", "pre-a", *route)
            self.assertRegex(out, r"cannot bring back.*\n.*\n\s+unknown\s+\.env\s+\(pre-a recorded nothing")
            self.assertIn("already matches pre-a", out)
            outputs.append(out)
        write(p / "main.txt", b"source changed since\n")
        out, _ = self.tool(p, "restore", "pre-a", "--apply")    # a source change the restore brings back
        self.assertRegex(out, r"cannot bring back.*\n.*\n\s+unknown\s+\.env\s+\(pre-a recorded nothing")
        self.assertIn("restored pre-a", out)
        outputs.append(out)
        self.assertEqual((p / "main.txt").read_bytes(), b"source stays the same\n")
        self.assertEqual((p / ".env").read_bytes(), b"SECRET_KEY=fixture-other-value\n")   # the current secret kept
        for label, genuine, data in GENUINE_OLD_CHECKPOINTS:     # no historical record rewritten
            self.assertEqual(self.store_git(p, "rev-parse", "refs/checkpoints/" + label), genuine)
            self.assertEqual(raw(genuine), data)
        self.assertEqual(raw("refs/checkpoints/00-baseline"), baseline)
        records = [self.store_git(p, "cat-file", "commit", commit) for commit in
                   self.store_git(p, "for-each-ref", "--format=%(objectname)", "refs/checkpoints/").split()]
        for out in outputs:
            self.assertNotIn("node_modules", out)               # an unwatched file is not in question
        for out in outputs + records:
            self.assertNotIn("fixture-", out)                   # no secret byte in any output or record

    def test_a_file_inside_a_folder_an_older_tool_listed_as_one_entry_is_never_called_unchanged(self):
        p = self.tmp / "nested"                                  # the project 8eeba3a saved (NEW-6, a folder entry)
        p.mkdir()
        self.git(p, "init", "-q")
        write(p / "main.txt", b"source stays the same\n")
        self.git(p, "add", "main.txt")
        self.git(p, "commit", "-qm", "first")
        write(p / ".git" / "info" / "exclude", b"x/\n")          # an ignore rule no checkpoint holds
        write(p / "x" / "inner.txt", b"inside the nested repository\n")   # a plain ignored folder now
        self.tool(p, "create", "00-baseline")
        self.assertEqual(self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline^{tree}"), FOLDER_TREE)
        for label, genuine, data in GENUINE_FOLDER_CHECKPOINTS:  # the very objects the archived tool wrote
            self.assertEqual(self.store_git(p, "hash-object", "-t", "commit", "-w", "--stdin", data=data), genuine)
            self.store_git(p, "update-ref", "refs/checkpoints/" + label, genuine)
        write(p / "x" / "inner.txt", b"other contents entirely, longer\n")
        for old, new, why in (("n-a", "n-b", "neither n-a nor n-b recorded anything about its contents"),
                              ("n-b", "n-a", "neither n-b nor n-a recorded anything about its contents"),
                              ("m-a", "n-b", "neither m-a nor n-b recorded anything about its contents"),
                              ("n-b", "m-a", "neither n-b nor m-a recorded anything about its contents"),
                              ("n-a", None, "n-a recorded nothing about its contents"),
                              ("m-a", None, "m-a recorded nothing about its contents")):
            with self.subTest(old=old, new=new):
                out, _ = self.tool(p, "diff", old, *([new] if new else []), expect=3)   # never "no changes"
                self.assertRegex(out, r"unknown\s+x/inner\.txt\s+\(%s" % re.escape(why))
                self.assertNotIn("no changes", out)
                self.assertNotRegex(out, r"x/\s")                # the folder entry itself is never listed
        for old, new in (("n-a", "m-a"), ("m-a", "n-a")):       # both list only the folder, a nested repository
            with self.subTest(old=old, new=new):
                out, _ = self.tool(p, "diff", old, new, expect=None)
                self.assertNotRegex(out, r"x/\s")                # which is not watched (G10), so never listed
        for label in ("n-a", "m-a"):                             # the source already matches the checkpoint
            with self.subTest(restore=label):
                out, _ = self.tool(p, "restore", label)
                self.assertRegex(out, r"cannot bring back.*\n.*\n\s+unknown\s+x/inner\.txt\s+\(%s recorded nothing"
                                 % label)
                self.assertIn("already matches " + label, out)
        out, _ = self.tool(p, "diff", "00-baseline", expect=3)  # a current record still tells the change itself
        self.assertRegex(out, r"changed\s+x/inner\.txt\s+\(32 bytes, was 29\)")
        for label, genuine, data in GENUINE_FOLDER_CHECKPOINTS:  # no historical record rewritten
            self.assertEqual(self.store_git(p, "rev-parse", "refs/checkpoints/" + label), genuine)
            self.assertEqual(self.store_git(p, "cat-file", "commit", genuine).encode() + b"\n", data)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX file permissions and a normal user")
    def test_create_refuses_when_a_watched_ignored_file_cannot_be_read(self):
        p = self.git_project()
        write(p / "local.db", b"data\n")
        write(p / ".gitignore", b"node_modules/\n.env\n*.db\n")
        os.chmod(p / "local.db", 0o000)
        try:
            _, err = self.tool(p, "create", "00-baseline", expect=1)
        finally:
            os.chmod(p / "local.db", 0o644)
        self.assertIn("local.db", err)
        self.assertIn("could not be noticed", err)


if __name__ == "__main__":
    unittest.main()
