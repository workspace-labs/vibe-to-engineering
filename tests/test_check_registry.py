"""Tests for the supported-check gate of scripts/evidence.py (NEW-5 stage 1, D6): a check launches only under a
runner in the supported set — the registry of record is references/supported-checks.md, and the gate implements
exactly that set. An unvalidated check is refused before execution; a link to a supported runner is that runner.

Run from the repository root:  python3 -m unittest discover -s tests -p test_check_registry.py -v
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"
REGISTRY = ROOT / "skills" / "vibe-to-engineering" / "references" / "supported-checks.md"
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))
import evidence  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


class CheckRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-registry-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, name, command, with_path=()):
        """The tool over a minimal project: (exit code, what it printed, the evidence file's text or None, its
        report, whether the check ran)."""
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        settings = [part for folder in with_path for part in ("--with-path", folder)]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + settings
                              + ["--"] + list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=enrolled.environ())
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "ran").exists())

    def test_the_document_and_the_gate_agree(self):
        """The registry of record names exactly the runners the gate implements, and the quarantine list is
        stated."""
        document = REGISTRY.read_text(encoding="utf-8")
        kinds = {kind for kind, _ in evidence.SUPPORTED}
        self.assertEqual(kinds, {"python", "sh", "node"})
        for kind, marker in (("python", "`python3`"), ("sh", "`sh`"), ("node", "`node`")):
            self.assertIn("**%s**" % kind, document)
            self.assertIn(marker, document)
        self.assertIn("Quarantine list: **empty**", document)

    def test_a_supported_runner_runs(self):
        for name, command in (("python", [sys.executable, "-c", "print('ran-6614')"]),
                              ("sh", ["sh", "-c", "printf ran-6615"])):
            with self.subTest(runner=name):
                code, printed, saved, report, _ = self.run_tool(name, command)
                self.assertEqual(code, 0, report)
                self.assertIn("ran-661", printed)
                self.assertEqual(saved.rstrip(), printed.rstrip())

    def test_an_unsupported_runner_is_refused_before_anything_runs(self):
        folder = self.tmp / "tools"
        folder.mkdir()
        fake = folder / "faketool-7717"
        fake.write_text("#!/bin/sh\n: > ran\n")   # if it ever runs, it leaves a mark in the project folder
        fake.chmod(0o755)
        for name, command in (("on the path", ["faketool-7717"]),
                              ("by relative path", ["./faketool-7717"]),
                              ("by absolute path", [str(fake)])):
            with self.subTest(found=name):
                code, printed, saved, report, ran = self.run_tool(
                    "refused %s" % name, command, with_path=[str(folder)])
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)                       # the check never ran
                self.assertIsNone(saved)                    # no evidence was written
                self.assertIn("supported set", report)
        with self.subTest("a command that does not exist"):
            code, _, saved, report, _ = self.run_tool("missing", ["nosuch-command-8819", "-x"])
            self.assertEqual(code, 2, report)
            self.assertIn("supported set", report)
            self.assertIsNone(saved)

    def test_a_link_to_a_supported_runner_is_that_runner(self):
        folder = self.tmp / "linked tools"
        folder.mkdir()
        os.symlink("/bin/sh", str(folder / "mysh-5517"))
        code, printed, saved, report, _ = self.run_tool("a link to sh", ["mysh-5517", "-c", "printf ran-5517"],
                                                        with_path=[str(folder)])
        self.assertEqual(code, 0, report)
        self.assertIn("ran-5517", printed)

    def test_the_gate_judges_the_resolved_name(self):
        """Unit level: names and paths resolve as documented — versioned python3 names count, lookalikes and
        missing files do not; a relative path is judged under the launch's working directory, never this
        process's."""
        folder = self.tmp / "bin"
        folder.mkdir()
        for name in ("python3.11", "sh", "node"):
            tool = folder / name
            tool.write_text("#!/bin/sh\n")
            tool.chmod(0o755)
        path = str(folder)
        self.assertEqual(evidence.supported_runner(["python3.11", "-V"], path, self.tmp)[1], "python")
        self.assertEqual(evidence.supported_runner(["sh"], path, self.tmp)[1], "sh")
        self.assertEqual(evidence.supported_runner(["node", "-e", ""], path, self.tmp)[1], "node")
        self.assertEqual(evidence.supported_runner(["python3.11rc1"], path, self.tmp), (None, None))  # a lookalike
        self.assertEqual(evidence.supported_runner(["python2"], path, self.tmp), (None, None))
        self.assertEqual(evidence.supported_runner(["nosuch-9917"], path, self.tmp), (None, None))  # not on the PATH
        self.assertEqual(evidence.supported_runner(["/not/there-9917"], path, self.tmp), (None, None))
        self.assertEqual(evidence.supported_runner(["sh"], "/not/there-9917", self.tmp), (None, None))
        # a relative executable is resolved under the launch's cwd, and must be an existing executable file
        launch = self.tmp / "launch folder"
        launch.mkdir()
        (launch / "sh").write_text("#!/bin/sh\n")
        (launch / "sh").chmod(0o755)
        resolved, kind = evidence.supported_runner(["./sh", "-c", ":"], "/not/there", launch)
        self.assertEqual(kind, "sh")
        self.assertEqual(resolved, os.path.realpath(str(launch / "sh")))
        self.assertEqual(evidence.supported_runner(["./sh", "-c", ":"], path, self.tmp), (None, None),
                         "the same relative command judged under another folder must not find it")
        (launch / "dir-run").mkdir()
        self.assertEqual(evidence.supported_runner(["./dir-run"], path, launch), (None, None))


if __name__ == "__main__":
    unittest.main()
