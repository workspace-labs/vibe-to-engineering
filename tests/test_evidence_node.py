"""Tests for the Node-loader readings behind scripts/evidence.py: the keys Node's own .env loader
(process.loadEnvFile(), --env-file, util.parseEnv()) and npm dotenv read, each from its release's own source,
and what a check meets under the constructed environment (NEW-5 stage 1) when the parent environment holds
such a key. Moved out of tests/test_evidence_readings.py to keep each test file under the 1,000-line limit.

Since the A1 literal boundary (2026-09-27) nearly all of these files are outside the literal .env grammar, so
evidence.py refuses the run before the check launches; the tests below are the refusal proofs, with the three
fixtures whose secret text sits in comment lines (inside the grammar) keeping their run-and-masked proofs.

Run from the repository root:  python3 -m unittest discover -s tests -p test_evidence_node.py -v
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
TOOL = Path(os.environ.get("V2E_EVIDENCE", ROOT / "skills" / "vibe-to-engineering" / "scripts" / "evidence.py"))
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


class NodeLoaders(unittest.TestCase):
    # NODE-PRECEDENCE: .env files, and the key Node's own loader reads there — measured with Node 20.20.2 (the
    # round-9 handoff's r9-node-facts.json) — then keys only other Node loaders read, from their source (Node
    # 20.12–22.0 read a key anywhere a regular expression finds one, as npm dotenv does at a line's start, a
    # colon included). The A1 literal boundary (2026-09-27) supersedes the precedence concern: such files are
    # refused before launch, so they no longer reach a check at all
    SECRET = "runtime-secret-99173"   # the round-7 reviewer's synthetic inherited value

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-node-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check_prints(self, name, files, reader, env=None, flags=()):
        """As in tests/test_evidence_readings.py: a project holding `files` whose check marks that it ran, then
        prints what `reader` prints. `env`: added to the environment the tool runs in — which a check must
        never inherit. `flags`: the tool's own options (--env NAME=VALUE)."""
        project = self.tmp / re.sub(r"\W+", "-", name)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        for file, content in files.items():
            (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + reader + "\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        parent = {key: value for key, value in dict(os.environ, **(env or {})).items() if value is not None}
        if not (env and "HOME" in env):
            parent["HOME"] = str(enrolled.enrolled_home())   # the isolated enrolled registry (A2)
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + list(flags)
                              + ["--", sys.executable, "-B", "check.py"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=parent)
        printed, report = done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")
        return (done.returncode, printed.split("\n\n", 1)[-1], out.read_text(encoding="utf-8") if out.exists()
                else None, report, (project / "check-ran").exists())

    # the three fixtures whose secret text sits in '#'-comment lines: a comment and the literal assignments
    # beside it are inside the A1 grammar, so these keep their run-and-masked expectations
    LITERAL_COMMENT_FIXTURES = ("a comment on the last line, no line break after it",
                                "a first-line comment, read by Node 20.12–22.0",
                                "a comment line's text before its '=', read by npm dotenv v0.1.1–v0.2.0")

    def refused(self, name, source, env=None):
        """The file stops the run before the check (A1 literal boundary): exit 2, the check never ran, no
        evidence file, the report names the .env and says 'cannot be masked', and nothing of the file's text
        or of an inherited value is shown."""
        code, shown, saved, report, ran = self.check_prints(name, {".env": source}, "print('unreached')", env)
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        self.assertIsNone(saved)
        self.assertIn(".env", report)
        self.assertIn("cannot be masked", report)
        for text in (shown, report):
            self.assertNotIn("from-file9137", text)
            self.assertNotIn(self.SECRET, text)

    def runs_masked(self, name, source, key):
        """A fixture inside the literal boundary still runs masked: the constructed environment never holds
        such a key, so an inherited value cannot reach the check, and the file's own value is masked."""
        with self.subTest(name, held_by="the parent environment only"):
            code, shown, saved, report, ran = self.check_prints(
                name + " parent", {".env": source}, "import os; print(os.environ.get(%r, ''))" % key,
                {key: self.SECRET})
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            self.assertNotIn("from-file9137", shown + saved)
            for text in (shown, saved, report):
                self.assertNotIn(self.SECRET, text)
        with self.subTest(name, inherited=False):
            code, shown, saved, report, ran = self.check_prints(name + " alone", {".env": source},
                                                                "print('from-file9137')")
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            self.assertEqual(re.sub(r"<masked(?: [^>\n]*)?>|\s+", "", shown), "", "a piece of the value is left")
            for text in (shown, saved):
                self.assertNotIn("from-file9137", text)

    NODE_KEYS = {
        "a quoted key (the reviewer's case)": ("'DB_PASSWORD'=from-file9137\n", "'DB_PASSWORD'"),
        "export and two spaces (the reviewer's case)": ("export  DB_PASSWORD=from-file9137\n", " DB_PASSWORD"),
        "export and a tab (the reviewer's case)": ("export\tDB_PASSWORD=from-file9137\n", "export\tDB_PASSWORD"),
        "a double-quoted key": ('"DB_PASSWORD"=from-file9137\n', '"DB_PASSWORD"'),
        "a tab before the key": ("\tDB_PASSWORD=from-file9137\n", "\tDB_PASSWORD"),
        "a tab after the key": ("DB_PASSWORD\t=from-file9137\n", "DB_PASSWORD\t"),
        "a vertical tab before the key": ("\x0bDB_PASSWORD=from-file9137\n", "\x0bDB_PASSWORD"),
        "a line with no = before the key": ("APP\nDB_PASSWORD=from-file9137\n", "APP\nDB_PASSWORD"),
        "export alone on the line before": ("export\nDB_PASSWORD=from-file9137\n", "export\nDB_PASSWORD"),
        "a comment on the last line, no line break after it": ("APP=x\n#DB_PASSWORD=from-file9137",
                                                               "#DB_PASSWORD"),
        "a key holding a #": ("DB#PASSWORD=from-file9137\n", "DB#PASSWORD"),
        "a key after one of spaces only, which Node reads on past": ("APP=x\n  =x\n'DB_PASSWORD'=from-file9137\n",
                                                                     "'DB_PASSWORD'"),
        "a key running over two lines after a quoted value": ('A= "x\n=y\n"\nAPP\nDB_PASSWORD=from-file9137\n',
                                                              "APP\nDB_PASSWORD")}
    OTHER_NODE_KEYS = {
        "a first-line comment, read by Node 20.12–22.0": ("# DB_PASSWORD=from-file9137\nAPP=x\n", "DB_PASSWORD"),
        "a colon, read by npm dotenv and Node 20.12–22.0": ("DB_PASSWORD: from-file9137\n", "DB_PASSWORD"),
        "a key after an empty one, read by Node 20.7–21.6 and from 22.16": (
            "=x\n'DB_PASSWORD'=from-file9137\n", "'DB_PASSWORD'"),
        "a key inside a value read unquoted (a space before its quote), by Node 20.7–21.6, 20.13–20.16, 22.1–22.5": (
            "A= \"x\n'DB_PASSWORD'=from-file9137\n\"\n", "'DB_PASSWORD'"),
        # measured with npm dotenv v15.0.0's own lib/main.js in Node 20.20.2 (the round-9 handoff's r9_npm15_leak.py)
        "a key inside a `…` value, read by npm dotenv v15 (no `…` values yet)": (
            "X=$'q\nA=`a\nDB_PASSWORD: from-file9137\n`\n'\n", "DB_PASSWORD"),
        # one key each form of Node's own parser alone reads, as its release's own code, compiled, reads it (the
        # round-9 handoff's r9_node_variants.py); inside $'…' where the shell would read something else
        "a key keeping its 'export ', after a line with no '=', read by Node 20.7–21.6 (a line at a time)": (
            "APP\nexport DB_PASSWORD=from-file9137\n", "export DB_PASSWORD"),
        "a key inside a `…` value after a space, read by Node 20.13–20.16 and 22.1–22.5": (
            "X=$'q\nA = `a\n\tDB_PASSWORD=from-file9137\n`\n'\n", "\tDB_PASSWORD"),
        "a key read again after a quote closed with no line break, by Node 20.19.0–20.19.4 and 22.13–23.8": (
            "\t='x\nDB_PASSWORD=from-file9137'", "'x\nDB_PASSWORD"),
        "a key trimmed of its tab before 'export ' goes, read by Node 22.15 and 23.9–23.11": (
            "X=$'q\nexport  DB_PASSWORD\t=from-file9137\n'\n", " DB_PASSWORD"),
        "a key with a space inside, read by Node from 22.16": (
            "X=$'q\nexport  DB PASSWORD=from-file9137\n'\n", "DB PASSWORD"),
        # and each npm dotenv reader no other one matches, run from each release's own lib/main.js in Node (the round-9
        # handoff's r9_npm_dotenv_releases.py)
        "a comment line's text before its '=', read by npm dotenv v0.1.1–v0.2.0": (
            "#DB_PASSWORD=from-file9137\nAPP=x\n", "#DB_PASSWORD"),
        "a key after a quote on the line below its '=', read by npm dotenv 18.0.0–18.0.1's fast parser": (
            "X=$'q\nAPP=\n\"a\nDB_PASSWORD: from-file9137\"\n'\n", "DB_PASSWORD")}

    def test_a_key_a_node_loader_reads_that_the_environment_already_holds_stops_the_run(self):
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the old expectation was that the check runs and the file
        # is masked whether the parent environment holds the key or not (NEW-5 stage 1: these keys — quotes,
        # spaces, tabs — are not shell names, so the loader has no inherited value to keep). Every fixture here
        # except the three comment-only ones is outside the literal grammar — a quoted, tabbed, spaced or
        # '#'-holding name (a NAME is [A-Za-z_][A-Za-z0-9_]*), a bare line with no '=' ('APP', 'export',
        # 'DB_PASSWORD: …', '  =x'), more than one space or a tab after 'export', and whitespace, quotes, '$'
        # or backticks or a control character inside a value — so evidence.py now refuses the run before
        # launch: exit 2, no check, no evidence file. The boundary supersedes the NODE-PRECEDENCE concern
        # because such files no longer reach a check at all. Both subTests are kept per fixture: the inherited
        # one proves the parent's value is not even echoed by the refusal; the three comment fixtures stay
        # inside the boundary and keep their run-and-masked proofs
        for name, (source, key) in dict(self.NODE_KEYS, **self.OTHER_NODE_KEYS).items():
            if name in self.LITERAL_COMMENT_FIXTURES:
                self.runs_masked(name, source, key)
                continue
            with self.subTest(name, held_by="the parent environment only"):
                self.refused(name + " parent", source, {key: self.SECRET})
            with self.subTest(name, inherited=False):
                self.refused(name + " alone", source)
        with self.subTest("a Node key with quotes is not a shell name --env can declare"):
            # D4 rule 1: --env takes a shell's name only, so round 9's redirection of such a key is gone by the
            # owner's decision — the setting is refused before anything runs, and the refusal never shows the value
            code, shown, saved, report, ran = self.check_prints(
                "node key given by --env", {".env": "'DB_PASSWORD'=from-file9137\n"},
                "import os; print(os.environ[\"'DB_PASSWORD'\"])", {"'DB_PASSWORD'": self.SECRET},
                ["--env", "'DB_PASSWORD'=throwaway-4471"])
            self.assertEqual(code, 2, report)
            self.assertFalse(ran)
            self.assertIsNone(saved)
            self.assertIn("NAME=VALUE", report)
            for text in (shown, report):
                self.assertNotIn("throwaway-4471", text)
                self.assertNotIn(self.SECRET, text)

    def test_each_key_the_real_node_keeps_an_inherited_value_for_stops_the_run(self):
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the old expectation probed the real Node on this
        # machine — util.parseEnv() reads each key, process.loadEnvFile() keeps the inherited value for it —
        # then showed that through the tool the check still ran masked (skipped as NOT VERIFIED without Node,
        # a failure with V2E_REQUIRE_NODE set). Every NODE_KEYS fixture is outside the literal grammar under
        # the same rules as the test above, so the run is now refused before any check exists for Node to
        # read: Node is no longer part of what happens to such a file, and the node probing and the skip
        # logic are dropped accordingly. The one fixture inside the boundary (a comment on the last line)
        # keeps its run-and-masked proof, restated without Node
        for name, (source, key) in self.NODE_KEYS.items():
            if name in self.LITERAL_COMMENT_FIXTURES:
                self.runs_masked(name, source, key)
                continue
            with self.subTest(name, held_by="the parent environment only"):
                self.refused(name + " node parent", source, {key: self.SECRET})
            with self.subTest(name, inherited=False):
                self.refused(name + " node alone", source)


if __name__ == "__main__":
    unittest.main()
