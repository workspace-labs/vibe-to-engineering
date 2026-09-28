"""F3-R1: ambiguous attached env values must stay private while parsing still refuses.

Run against the reviewed baseline with V2E_EVIDENCE pointing at its evidence.py. Tests use existing
APIs and real CLI refusals, private HOMEs and synthetic values. Positive controls preserve accepted
options and the command boundary; no new parser grammar or enrollment behavior is prescribed.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills/vibe-to-engineering/scripts/evidence.py"))
sys.path.insert(0, str(TOOL.parent))
import emission
import enrolled
from result_record import read

PY = os.path.realpath(sys.executable)


class AmbiguousCollection(unittest.TestCase):
    def test_attached_ambiguous_env_values_are_collected(self):
        for prefix in ("--e", "--en", "--"):
            for setting, value in (("A=AmbiguousCanary961", "AmbiguousCanary961"),
                                   ("A=space canary962", "space canary962"),
                                   ("A=a=b=canary963", "a=b=canary963"),
                                   ("MalformedCanary964", "MalformedCanary964"),
                                   ("A=2", "2")):
                with self.subTest(prefix=prefix, setting=setting):
                    self.assertIn(value, emission.collect([prefix + "=" + setting, "--", "cmd"]))

    def test_ambiguous_attached_value_does_not_hide_later_declarations(self):
        for prefix in ("--e", "--en"):
            with self.subTest(prefix=prefix):
                got = emission.collect([prefix + "=A=first value965", "--env", "B=LaterCanary965",
                                        "--", "cmd"])
                self.assertIn("LaterCanary965", got)
                self.assertIn("first value965", got)

    def test_actual_candidates_and_exact_options_are_respected(self):
        options = {"--env": 1, "--engine": 1}
        self.assertEqual(emission.collect(["--en=A=canary966"], options), ["canary966"])
        for options in ({"--engine": 1, "--entry": 1},
                        {"--env": 1, "--enroll-runner": 1, "--en": 1}):
            with self.subTest(options=options):
                self.assertEqual(emission.collect(["--en=A=notEnv966"], options), [])
        self.assertEqual(emission.collect(["--enr=A=notEnv966"]), [])

    def test_command_boundary_excludes_ambiguous_child_tokens(self):
        for tail in (["--", "cmd", "--e=A=childOnly967"], ["cmd", "--en=A=childOnly967"],
                     ["--command with space", "--e=A=childOnly967"]):
            with self.subTest(tail=tail):
                self.assertEqual(emission.collect(["--env", "A=ours967"] + tail), ["ours967"])


class AmbiguousRefusal(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="v2e-f3-ambiguous-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.env = enrolled.environ()
        self.registry = Path(self.env["HOME"]) / ".vibe-to-engineering/runners.json"
        self.registry_bytes = self.registry.read_bytes()
        self.number = 0

    def tearDown(self):
        self.assertEqual(self.registry.read_bytes(), self.registry_bytes)

    def run_case(self, flags, first=True, body="print('ordinary check')\n", tail=()):
        self.number += 1
        project = self.root / ("p%d" % self.number)
        out = project / ".vibe-to-engineering/evidence/check.txt"
        out.parent.mkdir(parents=True)
        (project / "check.py").write_text("from pathlib import Path\nPath('ran').write_text('yes')\n" + body)
        paths = ["--project", str(project), "--out", str(out)]
        args = (list(flags) + paths if first else paths + list(flags)) + ["--", PY, "-B", "check.py"] + list(tail)
        done = subprocess.run([PY, "-B", str(TOOL)] + args, env=self.env, capture_output=True, timeout=30)
        return done, project, out

    def assert_private_refusal(self, observed, values):
        done, project, out = observed
        stdout, stderr = (data.decode("utf-8", "replace") for data in (done.stdout, done.stderr))
        self.assertEqual(done.returncode, 2, stderr)
        self.assertFalse((project / "ran").exists())
        self.assertFalse(out.exists())
        self.assertEqual(self.registry.read_bytes(), self.registry_bytes)
        self.assertNotIn("Traceback", stderr)
        for value in values:
            self.assertNotIn(value, stdout)
            self.assertNotIn(value, stderr)
        self.assertEqual(read(stderr), dict(v=1, wrapper=2, launched=False, saved=False, child=None))

    def test_ambiguous_attached_refusals_protect_every_output(self):
        for prefix in ("--e", "--en", "--"):
            for value in ("AmbiguousCanary961", "café with space968", "a=b=canary969", "error", "2"):
                for first in (True, False):
                    with self.subTest(prefix=prefix, value=value, first=first):
                        observed = self.run_case([prefix + "=A=" + value], first=first)
                        self.assert_private_refusal(observed, [value])

    def test_malformed_prohibited_and_later_values_are_private(self):
        cases = [(["--e=MalformedCanary970"], ["MalformedCanary970"]),
                 (["--en=BASH_ENV=ProhibitedCanary971"], ["ProhibitedCanary971"]),
                 (["--e=LaterCanary972_X=first value972", "--env", "A=LaterCanary972"],
                  ["LaterCanary972", "first value972"]),
                 (["--env=A=EarlierCanary973", "--en=A=EarlierCanary973"], ["EarlierCanary973"])]
        for flags, values in cases:
            with self.subTest(flags=flags):
                self.assert_private_refusal(self.run_case(flags), values)

    def test_child_tail_stays_literal_and_exact_env_still_works(self):
        body = "import os, sys\nprint(os.environ['A'])\nprint(sys.argv[1:])\n"
        done, project, out = self.run_case(["--env=A=WrapperCanary974"], body=body,
                                          tail=["--e=A=ChildCanary974", "--en=A=SecondChild974"])
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((project / "ran").exists())
        self.assertEqual(done.stdout, out.read_bytes())
        self.assertIn(b"ChildCanary974", done.stdout)
        self.assertIn(b"SecondChild974", done.stdout)
        self.assertNotIn(b"WrapperCanary974", done.stdout + done.stderr)
        self.assertEqual(read(done.stderr.decode("utf-8")),
                         dict(v=1, wrapper=0, launched=True, saved=True, child={"exit": 0}))


if __name__ == "__main__":
    unittest.main()
