"""Ignored files: watched, not saved (recovery.md G10) — reported when they disappear or change, with secrets
never read into any output.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import hashlib
import os
import re
import stat
import unittest
from pathlib import Path
from support import Fixture, STATE, write


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
        self.plant(p, "01-recorded-nothing", {"a.txt": b"a\n"})          # older checkpoints recorded no contents
        out, _ = self.tool(p, "diff", "01-recorded-nothing", expect=3)
        self.assertNotIn("contents changed", out)

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
        # a checkpoint from before keyed fingerprints recorded the modification time: it still compares
        tree = self.store_git(p, "rev-parse", "refs/checkpoints/00-baseline^{tree}")
        old = self.store_git(p, "commit-tree", tree, "-m", "vibe-to-engineering checkpoint: 01-older\n\n"
                             'ignored-by-git: [".env", "node_modules/pkg/index.js"]\nnested-repositories: []\n'
                             'ignored-contents: {".env": [31, "mtime:%d"]}' % info.st_mtime_ns)
        self.store_git(p, "update-ref", "refs/checkpoints/01-older", old)
        out, _ = self.tool(p, "diff", "01-older")
        self.assertIn("no changes", out)
        os.utime(p / ".env", ns=(info.st_atime_ns, info.st_mtime_ns + 10**9))
        out, _ = self.tool(p, "diff", "01-older", expect=3)
        self.assertRegex(out, r"changed\s+\.env")
        key.unlink()                                             # the key file is guarded like the store (G7)
        os.symlink(str(self.tmp / "elsewhere"), str(key))
        _, err = self.tool(p, "diff", "00-baseline", expect=1)
        self.assertIn("fingerprint.key is a link", err)

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
