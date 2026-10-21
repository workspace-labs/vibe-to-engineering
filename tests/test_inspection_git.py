"""Forward control for the guarded inventory and committed-history inspection recipe."""

import importlib.util
import os
import shlex
import subprocess
import unittest
from unittest import mock

from support import Fixture, TOOL, identities, write


class InspectionGit(Fixture):
    def test_inventory_and_guarded_history_run_no_callbacks_and_change_no_project_files(self):
        project = self.repository(self.tmp / "project", {
            ".gitattributes": b"sample.txt -text filter=demonstration\n",
            "sample.txt": b"before\n",
        })
        filter_marker = self.tmp / "filter-ran"
        signature_marker = self.tmp / "signature-ran"
        clean = self.tmp / "clean-filter"
        clean.write_text("#!/bin/sh\nprintf ran > %s\ncat\n" % shlex.quote(str(filter_marker)))
        clean.chmod(0o755)
        verifier = self.tmp / "signature-verifier"
        verifier.write_text("#!/bin/sh\nprintf ran > %s\nexit 1\n" % shlex.quote(str(signature_marker)))
        verifier.chmod(0o755)
        self.git(project, "config", "filter.demonstration.clean", str(clean))
        self.git(project, "config", "gpg.program", str(verifier))
        self.git(project, "config", "log.showSignature", "true")

        # A synthetic signed commit exercises signature verification without invoking a signer.
        tree = self.git(project, "rev-parse", "HEAD^{tree}").strip().encode()
        raw = (b"tree " + tree + b"\nauthor Fixture <fixture@example.invalid> 1 +0000\n"
               b"committer Fixture <fixture@example.invalid> 1 +0000\n"
               b"gpgsig -----BEGIN PGP SIGNATURE-----\n ZHVtbXk=\n -----END PGP SIGNATURE-----\n"
               b"\nsynthetic signed fixture\n")
        commit = subprocess.run(["git", "hash-object", "-w", "-t", "commit", "--stdin"],
                                cwd=str(project), env=self.env, input=raw, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip().decode()
        self.git(project, "update-ref", "HEAD", commit)
        write(project / "sample.txt", b"after!\n")  # same size: status must consult the clean filter
        hook_marker, hostile = self.hostile_git(project)
        before = identities(project)

        output, _ = self.tool(project, "tree", "--current", env=hostile)
        self.assertIn("sample.txt", output)
        spec = importlib.util.spec_from_file_location("inspection_checkpoint", str(TOOL))
        checkpoint = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checkpoint)
        from gitrun import git
        from nested import refuse_partial_clone

        with mock.patch.dict(os.environ, dict(self.env, **hostile), clear=True):
            self.assertTrue(checkpoint.is_git_project(project))
            refuse_partial_clone(project, "the project's git repository")
            branch = git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=project, ok=(0, 1))
            self.assertEqual(branch.returncode, 0)
            self.assertEqual(git(["rev-parse", "--verify", "HEAD"], cwd=project).stdout.strip().decode(), commit)
            for command in ("log", "show"):
                result = git([command, "--no-ext-diff", "--no-textconv", "--no-show-signature", "-1", "HEAD"],
                             cwd=project)
                self.assertIn(b"synthetic signed fixture", result.stdout)

        self.assertEqual(identities(project), before, "inspection changed a project or Git file")
        for marker in (filter_marker, signature_marker, hook_marker):
            self.assertFalse(marker.exists(), "inspection ran a configured callback: %s" % marker.name)
        for name in ("trace.txt", "trace2.txt"):
            self.assertFalse((project / name).exists(), "inspection honored an inherited trace destination")

        # Positive controls prove the fixture can detect the exact commands the recipe forbids.
        self.git(project, "--no-optional-locks", "-c", "core.fsmonitor=false", "status", "--porcelain")
        self.assertTrue(filter_marker.exists(), "the status trap did not exercise its clean filter")
        with mock.patch.dict(os.environ, self.env, clear=True):
            git(["log", "--no-ext-diff", "--no-textconv", "-1", "HEAD"], cwd=project)
        self.assertTrue(signature_marker.exists(), "the history trap did not exercise signature verification")


if __name__ == "__main__":
    unittest.main()
