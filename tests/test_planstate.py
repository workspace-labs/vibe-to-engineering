"""Use the public planning command on a disposable project and inspect the published bytes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "vibe-to-engineering" / "scripts"


@unittest.skipUnless(sys.platform == "darwin", "native plan publication requires macOS")
class PlanPublication(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.state = self.project / ".vibe-to-engineering"

    def call(self, operation, data=b"", ok=True):
        result = subprocess.run([sys.executable, "-IB", str(SCRIPTS / "planstate.py"),
                                 "--project", str(self.project), operation], input=data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result.stderr

    def test_current_explicit_fixture_approval_is_required_even_without_a_map(self):
        plan = b"<p>Plan version 1</p>"
        self.call("plan", plan)
        fingerprint = subprocess.check_output(["/usr/bin/git", "hash-object", "--stdin"],
                                              input=plan, cwd=self.project).strip()
        self.call("append-ledger", b"Plan fingerprint: " + fingerprint +
                  "\n## date — PLAN APPROVED v1 — PLAN ONLY\n".encode())
        self.assertIn(b"PLAN ONLY", self.call("check-approval", ok=False))
        self.call("append-ledger", "## date — DISPOSABLE FIXTURE CONFIRMED — ready\n"
                  "Owner: this is disposable and all secrets are synthetic.\n".encode())
        self.call("check-approval")
        self.call("plan", plan + b" ")
        self.assertIn(b"fingerprint", self.call("check-approval", ok=False))
        self.call("plan", plan)
        self.call("append-ledger", "## date — MIGRATION STOPPED — stopped\n".encode())
        self.assertIn(b"ended", self.call("check-approval", ok=False))
        self.assertEqual(sorted(p.name for p in self.state.iterdir()),
                         [".gitignore", "Engineering-Migration-Plan.html", "ledger.md"])

    def test_normal_publication_appends_and_refuses_ambiguous_existing_records(self):
        self.call("plan", b"v1")
        self.call("plan", b"v2")
        self.call("append-ledger", b"first")
        self.call("append-ledger", b"second\n")
        self.assertEqual((self.state / "ledger.md").read_bytes(), b"first\nsecond\n")
        self.assertEqual((self.state / ".gitignore").read_bytes(), b"*\n")
        import fcntl
        directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fcntl.flock(directory, fcntl.LOCK_EX)
            self.assertIn(b"busy", self.call("append-ledger", b"concurrent", ok=False))
        finally:
            os.close(directory)
        self.assertEqual((self.state / "ledger.md").read_bytes(), b"first\nsecond\n")
        for name, operation in (("Engineering-Migration-Plan.html", "plan"),
                                ("ledger.md", "append-ledger"), (".gitignore", "plan")):
            with self.subTest(name=name):
                source = self.state / name
                alias = self.root / name
                os.link(source, alias)
                before = source.read_bytes()
                self.assertIn(b"single", self.call(operation, b"third", ok=False))
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual(alias.read_bytes(), before)
                alias.unlink()

    def test_state_replacement_at_publication_preserves_both_directories(self):
        self.call("plan", b"original")
        sys.path.insert(0, str(SCRIPTS))
        try:
            import planstate
        finally:
            sys.path.pop(0)
        previous = self.root / "previous"
        successor = self.root / "successor"
        successor.mkdir()
        (successor / planstate.PLAN).write_bytes(b"successor")
        real = planstate.exchange
        def change_after_exchange(*args):
            real(*args)
            if not previous.exists():
                self.state.rename(previous)
                successor.rename(self.state)
        with mock.patch.object(planstate, "exchange", side_effect=change_after_exchange):
            with self.assertRaisesRegex(planstate.Fail, "state directory changed"):
                planstate.run(self.project, "plan", b"proposed")
        self.assertEqual((self.state / planstate.PLAN).read_bytes(), b"successor")
        self.assertEqual((previous / planstate.PLAN).read_bytes(), b"original")
        self.assertEqual(sorted(p.name for p in previous.iterdir()), [".gitignore", planstate.PLAN])
