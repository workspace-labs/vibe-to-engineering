"""The NEW-5 stage-1 acceptance suite (the design contract §9, closure condition 2): adversarial paired runs —
a fixed project, command and inputs under varied, hostile parent environments, the child's raw environment and
resolved executable identity inspected and identical across runs; prohibited-name admission attempts, each
refused before anything runs; refusal ⇒ no launch and no evidence; real-reader exercises on this machine's
readers (bash 3.2 as /bin/sh, Node within the registry's version bounds); and counterexample-seeking property
tests over seeded random parent environments, declared values and secret files. macOS, the supported platform.

Run from the repository root:  python3 -m unittest discover -s tests -p test_stage1_acceptance.py -v
"""

import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))
import childenv  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


def scratch_base():
    """The scratch base the tool under test uses: inside the suite's isolated enrolled HOME — the base is
    per-user now (~/.vibe-to-engineering/runs, A3), never /tmp, which the OS reaps on its own schedule."""
    base = Path(str(enrolled.enrolled_home())) / ".vibe-to-engineering" / "runs"
    base.mkdir(parents=True, exist_ok=True)
    return base
SYNTHESIZED = ["HOME", "LANG", "LC_ALL", "PATH", "TMPDIR", "TZ"] + sorted(childenv.PINNED)
SEED = 20260927   # fixed: the property tests are counterexample-seeking, not flaky


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-acceptance-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scratch_roots(self):
        return {name for name in os.listdir(str(scratch_base())) if name.startswith(childenv.SCRATCH_PREFIX)}

    def run_tool(self, name, body, files=(), env=(), with_path=(), parent=None, out_inside=True, command=None):
        """A check run the way an agent runs it, over a project holding `files`, the check marking that it ran
        and then running `body`. `parent` REPLACES the environment the tool itself runs in (the adversarial
        lever); None keeps this process's own. `command` replaces the check's command line. Returns (exit code,
        printed, evidence text or None, report, ran)."""
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        for file, content in (files if files else {".env": "SECRET_KEY=hunter2-not-real\n"}).items():
            (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        (project / "check.py").write_text("from pathlib import Path\nPath('ran').write_text('ran')\n"
                                          + body + "\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt" if out_inside else self.tmp / "x.txt"
        settings = [part for setting in env for part in ("--env", setting)]
        settings += [part for folder in with_path for part in ("--with-path", folder)]
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + settings
                              + ["--"] + (command or [sys.executable, "-B", "check.py"]), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              env=enrolled.environ() if parent is None else parent)
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "ran").exists())

    # ------------------------------------------------------ adversarial paired runs (D7, condition 2)

    ENV_PROBE = ("import os, sys; print(repr(sorted(os.environ.items()))); "
                 "print(os.path.realpath(sys.executable))")

    @staticmethod
    def normalized(text):
        """The child's printed environment with the per-run scratch root folded out, so two runs compare."""
        return re.sub(r"%s[^/']*" % childenv.SCRATCH_PREFIX, "<scratch>", text)

    def hostile_parent(self, rng):
        """This process's environment plus everything that must never reach a check: each prohibited channel,
        the names the profile synthesizes pointed elsewhere, secret-shaped values, and random extras."""
        hostile = {"BASH_ENV": "/tmp/evil-7712", "ENV": "/tmp/evil-7712", "SHELLOPTS": "xtrace",
                   "BASHOPTS": "xpg_echo", "BASH_FUNC_evil%%": "() { echo pwned-7712; }",
                   "NODE_OPTIONS": "--inspect=0.0.0.0:9229", "PYTHONPATH": "/tmp/evil-7712",
                   "PYTHONSTARTUP": "/tmp/evil-7712",
                   "DOTENV_KEY": "dotenv://:deadbeef@x", "DOTENV_CONFIG_PATH": "/tmp/evil-7712",
                   "npm_config_registry": "http://evil-7712.test", "YARN_CONF": "/tmp/evil-7712",
                   "PNPM_HOME": "/tmp/evil-7712", "PIP_INDEX_URL": "http://evil-7712.test",
                   "GIT_DIR": "/tmp/evil-7712", "GIT_CONFIG_GLOBAL": "/tmp/evil-7712",
                   "HTTP_PROXY": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9",
                   "LD_PRELOAD": "/tmp/evil-7712.so", "LD_LIBRARY_PATH": "/tmp/evil-7712",
                   "TMPDIR": "/etc", "LC_ALL": "C", "LANG": "C", "TZ": "Pacific/Auckland",
                   # HOME is no longer a hostile lever (A2): the wrapper legitimately reads its own per-user
                   # runner registry from HOME, so the parent points it at the isolated enrolled home — the
                   # child's HOME independence is proven by the full-environment print the runs make
                   "HOME": str(enrolled.enrolled_home()),
                   "AWS_KEY": "AKIA%s" % "".join(rng.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                                                 for _ in range(16)),
                   "GH_TOKEN": "ghp_%s" % "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                                                  for _ in range(24))}
        # no DYLD_INSERT_LIBRARIES here: it would kill the WRAPPER (a Python process) before main() runs —
        # wrapper startup is outside the guarantee by owner decision D5; that the child can never see DYLD_* is
        # proven by the admission-attempt refusals and the inherits-nothing tests instead
        for i in range(8):   # random names and values too — nothing may leak through, named or not
            hostile["ADV_%d_%s" % (i, "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6)))] = \
                "adv-secret-%s-%d" % ("".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                                              for _ in range(10)), i)
        return dict(os.environ, **hostile)

    def test_paired_runs_identical_child_environment_under_varied_hostile_parents(self):
        rng = random.Random(SEED)
        parents = [enrolled.environ(), self.hostile_parent(rng),
                   self.hostile_parent(rng),   # a second, different hostile roll
                   {"PATH": os.environ["PATH"], "HOME": str(enrolled.enrolled_home())}]   # a near-empty parent
        runs, identity = [], []
        for number, parent in enumerate(parents):
            code, printed, saved, report, ran = self.run_tool("paired %d" % number, self.ENV_PROBE,
                                                              parent=parent)
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            shown = printed.split("\n\n", 1)[1]
            env_line, runs = shown.splitlines()[0], runs + [self.normalized(shown.splitlines()[0])]
            identity.append(shown.splitlines()[1])
            names = re.findall(r"\('(\w+)',", env_line)   # the names the child actually holds
            self.assertEqual(sorted(names), SYNTHESIZED)
            for leaked in ("evil-7712", "pwned-7712", "adv-secret-", "AKIA", "ghp_", "/etc", "Auckland"):
                self.assertNotIn(leaked, env_line)
        self.assertEqual(len(set(runs)), 1, "the child's raw environment differs across parent environments")
        self.assertEqual(len(set(identity)), 1, "the resolved executable identity differs across runs")
        self.assertTrue(all(identity[0] == i for i in identity))

    # ------------------------------------------------------ prohibited-name admission attempts (D3/D4)

    def test_every_admission_attempt_is_refused_before_anything_runs(self):
        before = self.scratch_roots()
        attempts = ["BASH_ENV=/tmp/x-5512", "ENV=/tmp/x-5512", "SHELLOPTS=xtrace", "BASHOPTS=x",
                    "BASH_FUNC_evil%%=() { :; }", "NODE_OPTIONS=--inspect", "PYTHONPATH=/tmp/x-5512",
                    "DYLD_INSERT_LIBRARIES=/tmp/x-5512", "DOTENV_KEY=dotenv://x", "npm_config_registry=http://x",
                    "YARN_CONF=/tmp/x-5512", "PIP_INDEX_URL=http://x", "GIT_DIR=/tmp/x-5512",
                    "https_proxy=http://127.0.0.1:9", "LD_PRELOAD=/tmp/x-5512",
                    "PATH=/tmp/x-5512", "HOME=/tmp/x-5512", "TZ=Pacific/Auckland"]
        for attempt in attempts:
            with self.subTest(attempt=attempt):
                code, printed, saved, report, ran = self.run_tool("attempt", "print('never')", env=[attempt])
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)                            # the check never ran
                self.assertIsNone(saved)                         # no evidence was written
                self.assertNotIn("x-5512", report)               # the refusal never shows the value
        for attempt in (["A=1", "A=2"], ["NO EQUALS-5512"], ["1FOO=x"]):
            with self.subTest(attempt=attempt):
                code, _, saved, report, ran = self.run_tool("attempt2", "print('never')", env=attempt)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
        self.assertEqual(self.scratch_roots(), before)           # a refusal leaves no scratch root

    # ------------------------------------------------------ refusal ⇒ no launch, no evidence (D1/D5)

    def test_every_refusal_means_no_launch_and_no_evidence(self):
        before = self.scratch_roots()
        cases = {
            "a quote never closed": {"files": {".env": "SECRET='never closed\n"}},
            "a vault file": {"files": {".env.vault": '{"vault": "x-6613"}'}},
            "a binary secret file": {"files": {".env": b"SECRET=x-6613\x00\n"}},
            "a prohibited --env": {"env": ["BASH_ENV=/tmp/x-6613"]},
            "a relative --with-path": {"with_path": ["relative/dir"]},
            "an evidence path outside the folder": {"out_inside": False},
        }
        for name, kw in cases.items():
            with self.subTest(case=name):
                code, printed, saved, report, ran = self.run_tool(name, "print('never')", **kw)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)
                self.assertNotIn("6613", printed)
        with self.subTest(case="an unsupported runner"):   # a runner the registry does not know, on a governed
            folder = self.tmp / "foreign-tools"            # folder: the gate refuses before anything launches
            folder.mkdir()
            fake = folder / "foreign-6613"
            fake.write_text("#!/bin/sh\n: > ran\n")
            fake.chmod(0o755)
            code, printed, saved, report, ran = self.run_tool("foreign runner", "", with_path=[str(folder)],
                                                              command=["foreign-6613"])
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
            self.assertIn("supported set", report)
        left = self.scratch_roots() - before   # A3: a refusal PAST construction retains its root — the three
        self.assertEqual(len(left), 4)         # unreadable secret files and the unsupported runner here; the
        for name in left:                      # earlier refusals stop before a root exists, so none appears
            self.assertTrue((scratch_base() / name).is_dir())

    # ------------------------------------------------------ real-reader exercises (version-bounded)

    def test_a_real_shell_reads_only_what_the_model_reads(self):
        # SUPERSEDED in part (A1 literal boundary, 2026-09-27): the "model" is the literal boundary now — a real
        # /bin/sh sources an admitted file and reads exactly the boundary's decode, under a plain and a hostile
        # parent. The arithmetic, ${#NAME} and ~ cases this test used to compare against the ported shell model
        # are refused by the boundary before launch — asserted below, still against the real /bin/sh (bash
        # expands a value-start '~' through the account database even with an empty environment)
        if not os.path.exists("/bin/sh"):
            self.skipTest("NOT VERIFIED: no POSIX shell on this machine")
        version = subprocess.run(["/bin/sh", "--version"], stdout=subprocess.PIPE).stdout.decode()
        self.assertIn("3.2", version)   # the version the boundary's shell evidence is measured against
        body = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', '. ./.env; printf %s "
                "\"$DB_PASSWORD\"'], stdout=subprocess.PIPE).stdout.decode(), end='')")
        source = "A=Horse9137Staple\nDB_PASSWORD=Orbit14Moon-9137\nHOME=/acc-home\nT=/tail6619\n"
        for name, parent in (("plain", None), ("hostile", self.hostile_parent(random.Random(SEED + 1)))):
            with self.subTest(parent=name):
                code, printed, saved, report, ran = self.run_tool("real sh %s" % name, body,
                                                                  files={".env": source}, parent=parent)
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                for secret in ("Horse9137Staple", "Orbit14Moon-9137"):
                    self.assertNotIn(secret, printed)
                    self.assertNotIn(secret, saved)
        for name, refused in (("arithmetic", "A=Horse$((9100+37))Staple\nDB_PASSWORD=Orbit${#A}Moon\n"),
                              ("the length of a value", "A=HorseBattery\nDB_PASSWORD=Orbit${#A}Moon\n"),
                              ("a tilde the account database decides", "HOME=/acc-home\nT=~/tail6619\n")):
            with self.subTest(refused=name):
                code, printed, saved, report, ran = self.run_tool("real sh refused %s" % name, body,
                                                                  files={".env": refused})
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)

    def test_a_real_node_keeps_the_constructed_value_and_the_declared_winner_is_masked(self):
        node = shutil.which("node")
        if not node:
            if os.environ.get("V2E_REQUIRE_NODE"):
                self.fail("NOT VERIFIED: V2E_REQUIRE_NODE is set but no node is on the PATH")
            self.skipTest("NOT VERIFIED: no node on the PATH, so the real Node exercise did not run")
        version = subprocess.run([node, "--version"], stdout=subprocess.PIPE).stdout.decode().strip()
        numbers = tuple(int(part) for part in version.lstrip("v").split("."))
        self.assertTrue((20, 7) <= numbers <= (26, 10),   # the registry's version-bounded loader profiles
                        "%s is outside the revalidated bounds (Node v20.7–v26.10)" % version)
        body = ("import subprocess; print(subprocess.run([%r, '-e', \"process.loadEnvFile('.env'); "
                "process.stdout.write(process.env.DB_PASSWORD)\"], stdout=subprocess.PIPE).stdout.decode())"
                % node)
        code, printed, saved, report, ran = self.run_tool(
            "real node winner", body, files={".env": "DB_PASSWORD=file-secret-5517\n"},
            env=["DB_PASSWORD=declared-winner-5517"], parent=self.hostile_parent(random.Random(SEED + 2)))
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIn("<masked DB_PASSWORD>", printed)   # Node kept the constructed (declared) value
        for text in (printed, saved, report):
            self.assertNotIn("file-secret-5517", text)
            self.assertNotIn("declared-winner-5517", text)

    # ------------------------------------------------------ counterexample-seeking property tests

    def test_property_the_child_environment_never_depends_on_the_parent(self):
        rng = random.Random(SEED + 10)
        seen = set()
        for roll in range(12):
            code, printed, saved, report, ran = self.run_tool("property env %d" % roll, self.ENV_PROBE,
                                                              parent=self.hostile_parent(rng))
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            shown = printed.split("\n\n", 1)[1].splitlines()
            seen.add(self.normalized(shown[0]))
            self.assertNotIn("adv-secret-", shown[0] + report)
        self.assertEqual(len(seen), 1, "a parent environment changed the child's constructed environment")

    def test_property_a_declared_value_never_appears_raw(self):
        rng = random.Random(SEED + 11)
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        for roll in range(12):
            names = ["SEED_%d_%s" % (roll, "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4)))
                     for _ in range(3)]
            values = []
            for _ in names:
                shape = rng.randrange(5)   # adversarial shapes, not one distribution (final-review R1, F2):
                if shape == 0:             # short: one to three characters
                    value = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 3)))
                elif shape == 1:           # all digits, any length
                    value = "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 10)))
                elif shape == 2:           # with '=' or a space inside
                    value = "".join(rng.choice(alphabet) for _ in range(rng.randint(3, 8))) + \
                        rng.choice("= ==") + "".join(rng.choice(alphabet) for _ in range(rng.randint(2, 6)))
                elif shape == 3:           # words with a space
                    value = "".join(rng.choice(alphabet) for _ in range(rng.randint(2, 6))) + " " + \
                        "".join(rng.choice(alphabet) for _ in range(rng.randint(2, 6)))
                else:                      # ordinary, any length
                    value = "".join(rng.choice(alphabet) for _ in range(rng.randint(6, 22)))
                values.append(value + "z9" if len(value) > 3 and not re.search(r"[a-z]", value) else value)
            code, printed, saved, report, ran = self.run_tool(
                "property declared %d" % roll, "import os\nfor n in %r: print('‹' + os.environ[n] + '›')"
                % names, env=["%s=%s" % pair for pair in zip(names, values)])
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            for name, value in zip(names, values):
                self.assertIn("‹<masked %s>›" % name, printed)   # masked wherever it appears, even embedded
                self.assertIn("‹<masked %s>›" % name, saved)
                if len(value) > 3:                                    # never raw, anywhere (short values could
                    for text in (printed, saved, report):             # sit inside a path; the mask is the proof)
                        self.assertNotIn(value, text)

    def test_property_no_simple_secret_file_value_ever_reaches_the_evidence(self):
        rng = random.Random(SEED + 12)
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for roll in range(12):
            secrets = {}
            for i in range(3):
                value = "".join(rng.choice(alphabet) for _ in range(rng.randint(9, 18)))
                secrets["PROP_%d_%s" % (i, "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
                                                   for _ in range(4)))] = value + "q7"
            source = "".join("%s=%s\n" % pair for pair in secrets.items())
            code, printed, saved, report, ran = self.run_tool(
                "property file %d" % roll, "print(open('.env').read(), end='')", files={".env": source},
                parent=self.hostile_parent(rng))
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            self.assertIn("<masked", printed)
            for value in secrets.values():
                for text in (printed, saved, report):
                    self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
