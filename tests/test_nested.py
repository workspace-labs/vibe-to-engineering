"""Nested repositories (recovery.md G1 and G11): named, never saved, refused while they hold unsaved work — and
checked without git running any configured program or fetching anything.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import os
import re
import shutil
from support import Fixture, disk_state, folder_digest, write


class Nested(Fixture):
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
                    ignored_line = next(line for line in message.splitlines() if line.startswith("ignored-by-git: "))
                    self.assertIn('"%s/"' % place, ignored_line)       # recorded, where the store format keeps it:
                    self.assertIn("nested-repositories: []", message)  # so an older tool reads the same checkpoint
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

    def test_a_nested_repository_that_an_ignore_rule_starts_or_stops_matching_is_not_called_gone(self):
        p = self.git_project()
        self.repository(p / "module", {"code.txt": b"committed\n"})
        for number, rules in enumerate((b"node_modules/\n.env\nmodule/\n", b"node_modules/\n.env\n")):
            with self.subTest(module="ignored" if number == 0 else "no longer ignored"):
                self.tool(p, "create", "%02d-before" % number)
                write(p / ".gitignore", rules)                     # a phase changed an ignore rule, nothing else
                out, _ = self.tool(p, "diff", "%02d-before" % number, expect=3)
                self.assertRegex(out, r"M\s+\.gitignore")
                self.assertNotIn("gone", out)

    # ------------------------------------------------------------ G11 a nested partial clone fetches nothing (F03)

    def test_a_nested_partial_clone_missing_an_object_is_refused_before_git_fetches_it(self):
        p = self.git_project()
        module = self.repository(p / "module", {"code.txt": b"committed\n"})
        self.tool(p, "create", "00-clean")
        marker, helper = self.tmp / "helper-ran", self.tmp / "bin"
        helper.mkdir()
        (helper / "git-remote-fixture").write_text("#!/bin/sh\nprintf ran > '%s'\nexit 1\n" % marker)
        os.chmod(helper / "git-remote-fixture", 0o755)
        tree = self.git(module, "rev-parse", "HEAD^{tree}").strip()
        os.rename(module / ".git" / "objects" / tree[:2] / tree[2:], self.tmp / "missing-tree")
        for key, value in (("extensions.partialClone", "origin"), ("remote.origin.promisor", "true"),
                           ("remote.origin.url", "fixture::local-only"), ("protocol.fixture.allow", "always")):
            self.git(module, "config", key, value)       # a partial clone: git fetches what it lacks when it reads it
        env = {"PATH": str(helper) + os.pathsep + self.env["PATH"]}
        before = disk_state(p)                            # module/.git included: nested folders are walked whole
        for command in (("create", "01-changed"), ("diff", "00-clean"), ("restore", "00-clean"),
                        ("restore", "00-clean", "--apply")):
            with self.subTest(command=" ".join(command)):
                _, err = self.tool(p, *command, expect=1, env=env)
                self.assertFalse(marker.exists(), "git fetched through the remote helper")
                self.assertIn("cannot tell whether the nested repository module/", err)
                self.assertEqual(disk_state(p), before, "the nested repository or the project changed")

    # ------------------------------------------------------------ G1 a link that became a plain file is unsaved work (F06)

    def test_a_link_replaced_by_a_plain_file_is_unsaved_work_unless_the_repository_keeps_links_as_files(self):
        for ignored in (False, True):
            for symlinks in ("true", "false"):
                with self.subTest(ignored=ignored, core_symlinks=symlinks):
                    p = self.git_project("link-%d-%s" % (ignored, symlinks))
                    if ignored:
                        write(p / ".gitignore", b"node_modules/\n.env\nmodule/\n")
                    module = self.repository(p / "module", {"keep.txt": b"kept\n"})
                    os.symlink("keep.txt", str(module / "link.txt"))
                    self.git(module, "add", "link.txt")
                    self.git(module, "commit", "-qm", "link")
                    self.git(module, "config", "core.symlinks", symlinks)
                    self.tool(p, "create", "00-clean")                 # a real link: clean either way
                    (module / "link.txt").unlink()
                    write(module / "link.txt", b"keep.txt")            # the link's target, as a plain file's bytes
                    before = disk_state(p)
                    if symlinks == "true":                             # what git calls " T link.txt"
                        for command in (("create", "01-changed"), ("diff", "00-clean"),
                                        ("restore", "00-clean", "--apply")):
                            _, err = self.tool(p, *command, expect=1)
                            self.assertIn("module/: changed link.txt", err)
                            self.assertEqual(disk_state(p), before)
                    else:                                              # this repository keeps links as plain files
                        self.tool(p, "create", "01-same")
                        out, _ = self.tool(p, "diff", "00-clean")
                        self.assertIn("no changes", out)


if __name__ == "__main__":
    unittest.main()
