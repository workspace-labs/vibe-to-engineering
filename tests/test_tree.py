"""The tree view (recovery.md G9): read-only, every file shown, what checkpoints leave alone marked.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import re
from support import Fixture, STATE, disk_state, folder_digest, write


class Tree(Fixture):
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
                self.assertRegex(out, r"── node_modules/\s+\[ignored — 1 file\]")   # one line, not opened (RA-01)
                self.assertNotIn("index.js", out)

    # ------------------------------------------------------------ G9 the tree shows every file (RA-01)

    def test_the_tree_shows_every_file_and_marks_what_checkpoints_leave_alone(self):
        p = self.git_project()
        write(p / ".gitignore", b"node_modules/\n.env\nexports/\n")
        write(p / "exports" / "expenses-2026-08.csv", b"an ignored export\n")
        self.repository(p / "tools", {"t.txt": b"t\n"})                  # an untracked nested repository
        marks = {".env": "[ignored]", "exports/": "[ignored — 1 file]", "node_modules/": "[ignored — 1 file]",
                 "tools/": "[nested repository]"}
        closing = ["11 files saved · 3 ignored (2 folders) · 1 nested repository",
                   "[ignored], [nested repository]: never touched, not in checkpoints"]
        for command in (("tree", "--current"), ("create", "00-baseline"), ("tree", "--current"), ("tree", "00-baseline")):
            with self.subTest(command=" ".join(command)):
                out, _ = self.tool(p, *command)
                if command[0] == "create":
                    marks[".vibe-to-engineering/"] = "[the skill's own folder]"   # from now on it exists
                    continue
                self.assertEqual(dict(re.findall(r"── (\S+)\s+(\[[^\]]+\])$", out, re.M)), marks)
                self.assertRegex(out, r"── docs/\n│   └── Read Me ü\.md\n")     # saved files as before, unmarked
                self.assertNotIn("expenses-2026-08.csv", out)                   # inside a folder shown as one line
                self.assertEqual(out.splitlines()[-2:], closing)
        out, _ = self.tool(p, "tree", "--current", "--depth", "1")
        self.assertIn("── src/ (2 files)\n", out)
        write(p / "src" / "local.env", b"ignored inside a folder that holds saved files\n")
        write(p / ".gitignore", b"node_modules/\n.env\nexports/\n*.env\n")
        self.repository(p / "src" / "vendored", {"v.txt": b"v\n"})
        out, _ = self.tool(p, "tree", "--current", "--depth", "1")
        self.assertIn("── src/ (2 files · 1 ignored · 1 nested repository)\n", out)
        self.plant(p, "01-recorded-nothing", {"a.txt": b"a\n"})             # a checkpoint without the two lists
        out, _ = self.tool(p, "tree", "01-recorded-nothing")
        self.assertEqual(out.splitlines()[-1], "1 file saved — this checkpoint did not record which files git "
                                               "ignored or which nested repositories there were")

    def test_the_saved_only_tree_is_the_old_output_byte_for_byte(self):
        p = self.plain_project("small")
        out, _ = self.tool(p, "tree", "--current", "--saved-only")
        self.assertEqual(out, "small (current files)\n├── data/\n│   └── notes.txt\n├── lib/\n│   └── calc.py\n"
                              "├── .gitignore\n└── main.py\n\n4 files\n")


if __name__ == "__main__":
    unittest.main()
