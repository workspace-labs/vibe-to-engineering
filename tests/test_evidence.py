"""Tests for scripts/evidence.py: a check's output is kept as evidence with every secret value masked, only inside
the project's evidence folder.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
SECRETS = ("hunter2-not-real", "abcd1234efgh5678", "sk_live_ABCDEFGH12345678", "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC",
           "hunter22", "zzzz9999")
CHECK = r"""
import os
print(open('.env').read())
print('connecting with sk_live_ABCDEFGH12345678')
print('-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----')
print('password: hunter22')
print('{"api_key": "zzzz9999"}')
print('12 passed, 0 failed in', os.getcwd())
raise SystemExit(3)
"""


class Evidence(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-evidence-")).resolve()
        self.project = self.tmp / "project"
        (self.project / ".vibe-to-engineering").mkdir(parents=True)
        (self.project / ".vibe-to-engineering" / ".gitignore").write_text("*\n")
        (self.project / ".env").write_text("SECRET_KEY=hunter2-not-real\nEXCHANGE_API_KEY='abcd1234efgh5678'\n")
        self.folder = self.project / ".vibe-to-engineering" / "evidence"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, out, *command, env=()):
        settings = [part for setting in env for part in ("--env", setting)]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(self.project), "--out", str(out)] + settings
                              + ["--"] + list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")

    def test_no_secret_value_reaches_the_evidence_file_or_the_screen(self):
        out = self.folder / "00-baseline" / "tests.txt"
        code, printed, report = self.run_tool(out, sys.executable, "-c", CHECK)
        self.assertEqual(code, 3, report)                                  # the check's own exit code
        saved = out.read_text(encoding="utf-8")
        for secret in SECRETS:
            self.assertNotIn(secret, saved)
            self.assertNotIn(secret, printed)
        for kept in ("SECRET_KEY=<masked SECRET_KEY>", "EXCHANGE_API_KEY=", "12 passed, 0 failed in " + str(self.project)):
            self.assertIn(kept, saved)                                     # names and ordinary results stay readable
        self.assertEqual(saved, printed)
        self.assertIn("secret values masked", report)

    def test_a_check_is_pointed_at_throwaway_data(self):
        throwaway = self.tmp / "throwaway.db"
        code, printed, _ = self.run_tool(self.folder / "check.txt", sys.executable, "-c",
                                         "import os; print('DB at', os.environ['DB_PATH'])",
                                         env=["DB_PATH=%s" % throwaway])
        self.assertEqual(code, 0)
        self.assertIn("DB at %s" % throwaway, printed)

    def test_evidence_is_written_only_inside_the_evidence_folder(self):
        outside = self.tmp / "outside"
        outside.mkdir()
        self.folder.mkdir(parents=True)
        os.symlink(str(outside), str(self.folder / "link"))
        for out in (self.project / "notes.txt", self.folder / ".." / "escaped.txt", self.folder / "link" / "x.txt",
                    self.tmp / "elsewhere.txt"):
            with self.subTest(out=str(out)):
                code, _, report = self.run_tool(out, sys.executable, "-c", "print('ran')")
                self.assertEqual(code, 2, report)
                self.assertIn("must be inside", report)
                self.assertFalse(out.exists())
        self.assertEqual(os.listdir(str(outside)), [])
        shutil.rmtree(str(self.project / ".vibe-to-engineering"))
        code, _, report = self.run_tool(self.folder / "x.txt", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 2, report)                                  # no plan yet, so no state folder to use
        self.assertIn("not there yet", report)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX file permissions and a normal user")
    def test_a_secret_file_that_cannot_be_read_stops_the_run(self):
        os.chmod(self.project / ".env", 0o000)
        try:
            code, printed, report = self.run_tool(self.folder / "x.txt", sys.executable, "-c", "print('ran')")
        finally:
            os.chmod(self.project / ".env", 0o644)
        self.assertEqual(code, 2, report)
        self.assertNotIn("ran", printed)
        self.assertIn(".env", report)


if __name__ == "__main__":
    unittest.main()
