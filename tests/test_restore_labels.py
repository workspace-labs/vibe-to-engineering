"""Automatically named recovery checkpoints must not collide during quick retries."""

import unittest
from unittest import mock

from support import Fixture, write


class RestoreLabels(Fixture):
    def test_restores_in_the_same_second_keep_each_pre_restore_state(self):
        project = self.tmp / "project"
        write(project / "main.txt", b"baseline\n")
        self.tool(project, "create", "00-baseline")
        saved_refs = {}
        expected = (b"first broken state\n", b"second broken state\n", b"third broken state\n")

        with mock.patch("time.strftime", return_value="20261021t000000z"):
            for contents in expected:
                write(project / "main.txt", contents)
                code, error = self.in_process(project, ["restore", "00-baseline", "--apply"], lambda tool: None)
                self.assertEqual(code, 0, error)
                self.assertEqual((project / "main.txt").read_bytes(), b"baseline\n")
                current_refs = dict(line.split(" ", 1) for line in self.store_git(
                    project, "for-each-ref", "--format=%(refname) %(objectname)",
                    "refs/checkpoints/pre-restore-*").splitlines())
                self.assertEqual(len(current_refs), len(saved_refs) + 1)
                for name, commit in saved_refs.items():
                    self.assertEqual(current_refs[name], commit, "an earlier recovery checkpoint was replaced")
                saved_refs = current_refs

        recovered = set()
        for number, ref in enumerate(saved_refs):
            target = self.tmp / ("extracted-%d" % number)
            self.tool(project, "extract", ref[len("refs/checkpoints/"):], str(target))
            recovered.add((target / "main.txt").read_bytes())
        self.assertEqual(recovered, set(expected))


if __name__ == "__main__":
    unittest.main()
