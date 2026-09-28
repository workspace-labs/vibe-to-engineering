"""The v0.1 literal .env boundary's differential matrix (A1 evidence): the implemented grammar and masking logic
(scripts/envliteral.py, the .env reader of secretformats.py) against every claimed reader, live — bash 3.2 as
/bin/sh; Node --env-file v20.7.0, v20.20.2 (local), v22.0.0, v22.16.0, v24.21.0, v26.10.0; npm dotenv
0.4.0–18.0.4 (87 releases, driven per era exactly as each release's own code exposes itself); python-dotenv
1.2.3 — proving (a) on every admitted form, every claimed reader's decoded value is inside the masked set (the
line's single unanimous decode, plus dotenv-15.0.0's quoted-empty forms), and (b) every divergent form refuses.

This test runs NO downloads: the reader artifacts must be prepared first —
    python3 tests/reader_matrix_prepare.py            (into /tmp/v2e-reader-matrix, or V2E_READER_MATRIX_DIR)
which reuses the 2026-09-27 experiment's hash-verified copies or fetches the exact recorded versions. The test
re-verifies archive sha256, every extracted file/link, the entry path and harness before running readers.
Reader crashes, malformed/missing observations and harness failures are NOT VERIFIED failures, never empty passes. A
missing or unverified reader means the boundary is NOT VERIFIED here — the test skips, saying so, and fails
outright when V2E_REQUIRE_MATRIX=1 is set: verification is then incomplete, never passed.

Run from the repository root:  python3 -m unittest discover -s tests -p test_literal_matrix.py -v
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))
import envliteral  # noqa: E402
from reader_artifacts import verified_entries

MATRIX_DIR = Path(os.environ.get("V2E_READER_MATRIX_DIR", "/tmp/v2e-reader-matrix"))
PROVENANCE = json.loads((ROOT / "tests" / "reader_matrix_provenance.json").read_text())["artifacts"]
UNSET = "__UNSET__"

# The admitted corpus: (name, bytes) — the experiment's admitted fixtures under the corrected grammar, the
# boundary's edge cases, and the combination cases (with and without export) the owner directed after Codex's
# brace case: per-character probing is necessary but not sufficient.
ADMITTED = [
    ("simple", b"A=abc\n"), ("empty", b"A=\n"), ("punct", b"A=abc-def_123./:@x\n"),
    ("trailing-spaces", b"A=abc   \n"), ("leading-spaces", b"  A=abc\n"), ("export", b"export A=abc\n"),
    ("single-quoted", b"A='a b'\n"), ("single-empty", b"A=''\n"), ("single-specials", b"A='p@ss#w ord'\n"),
    ("single-backslash", b"A='a\\nb'\n"), ("double-quoted", b'A="a b"\n'), ("double-empty", b'A=""\n'),
    ("comment-line", b"# just a comment\nA=x\n"), ("no-trailing-lf", b"A=abc"),
    ("single-tab", b"A='a\tb'\n"), ("double-tab", b'A="a\tb"\n'),
    ("single-eq", b"A='x=y'\n"), ("double-eq", b'A="x=y"\n'),
    ("double-inner-squote", b'A="it\'s"\n'), ("single-inner-dquote", b"A='say \"hi\"'\n"),
    ("unquoted-eq", b"A=x=y\n"), ("leading-bang", b"A=!cmd\n"), ("tilde-mid", b"A=x~y\n"),
    ("quoted-utf8", "A=\"café\"\n".encode()),   # non-ASCII inside quotes: admitted by the grammar, proven live
    ("three-names", b"A=one\nB='two 2'\nC=a:b@c\n# a note\n"),
    ("combo-glob", b"A=f*?[0-9]x\n"), ("combo-glob-export", b"export A=f*?[0-9]x\n"),
    ("combo-globs", b"A=*?[]^_*\n"), ("combo-globs-export", b"export A=*?[]^_*\n"),
    ("combo-bang", b"A=!cmd!rm\n"), ("combo-bang-export", b"export A=!cmd!rm\n"),
    ("combo-colons", b"A=a::b::c\n"), ("combo-colons-export", b"export A=a::b::c\n"),
    ("combo-equals", b"A=a==b=c\n"), ("combo-equals-export", b"export A=a==b=c\n"),
    ("combo-punct", b"A=pre_FIX-01./:@x=y\n"), ("combo-punct-export", b"export A=pre_FIX-01./:@x=y\n"),
    ("combo-tildes", b"A=x~y~z\n"), ("combo-tildes-export", b"export A=x~y~z\n"),
    ("single-backslash-export", b"export A='a\\nb'\n"),
    ("quoted-utf8-single", "A='café'\n".encode()),
    ("quoted-utf8-export", "export A='café'\n".encode()),
    ("combo-brace-quoted", b"A='a{b}c'\n"), ("combo-brace-quoted-export", b"export A=\"a{b}c\"\n"),
]

# The divergent corpus: every form the boundary must refuse (grammar-level; the real-reader divergence behind
# each is the 2026-09-27 experiment's record — bash's brace and tilde expansions are re-proven live in
# tests/test_env_literal.py).
REFUSED = [
    ("inline-comment", b"A=abc # comment\n"), ("hash-midvalue", b"A=ab#c\n"),
    ("double-backslash-n", b'A="a\\nb"\n'), ("dollar-in-single", b"A='$HOME'\n"),
    ("plain-reference", b"B=x\nA=$B\n"), ("operator-unset", b"A=${MISSING:-fallback}\n"),
    ("tilde-start", b"A=~/x\n"), ("tilde-after-colon", b"A=x:~y\n"),
    ("backticks", b"A=`true`\n"), ("duplicate", b"A=one\nA=two\n"),
    ("multiline-dq", b'A="line1\nline2"\n'), ("crlf", b"A=abc\r\n"),
    ("spaces-around-eq", b"A = abc\n"), ("single-adjacent", b"A='a''b'\n"),
    ("quoted-edge-ws", b'A="  spaced  "\n'), ("unquoted-tab", b"A=a\tb\n"), ("unquoted-space", b"A=a b\n"),
    ("brace", b"A=x{a,b}\n"), ("brace-export", b"export A=x{a,b}\n"),
    ("brace-range", b"A=v{1..3}\n"), ("brace-range-export", b"export A=v{1..3}\n"),
    ("bare-line", b"frob\n"), ("second-assignment", b"APP=demo DB_PASSWORD=x\n"),
    ("quoted-name", b"'DB_PASSWORD'=x\n"), ("colon-separator", b"DB_PASSWORD: x\n"),
    ("plus-equals", b"A+=x\n"), ("control-in-quotes", b"A='a\x01b'\n"),
    ("text-after-quote", b"A='x' extra\n"), ("non-ascii-unquoted", "A=café\n".encode()),
    ("bom", b"\xef\xbb\xbfA=abc\n"),
]
# A1-F01/F02: combinations and Unicode absent from the first grammar's corpus.
for prefix in ("", "export "):
    for count in range(2, 7):
        REFUSED.append(("backslashes-%s-%s" % (bool(prefix), count),
                        (prefix + "A='Horse" + "\\" * count + "9137Staple'\n").encode()))
    for mark in ("'", '"'):
        for char in ("\u0085", "\u009f", "\u00a0", "\u2003", "\ufeff"):
            REFUSED.append(("unicode-edge-%s-%s-%x" % (bool(prefix), ord(mark), ord(char)),
                            (prefix + "A=" + mark + char + "Horse9137Staple" + mark + "\n").encode()))



def sha256(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DifferentialMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="v2e-matrix-")).resolve()
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.fixtures = cls.tmp / "fixtures"
        cls.fixtures.mkdir()
        cls.masked = {}
        for name, content in ADMITTED:
            path = cls.fixtures / (name + ".env")
            path.write_bytes(content)
            text = content.decode("utf-8")
            parsed = envliteral.assignments(text.replace("\r\n", "\n").replace("\r", "\n"), text)
            masked = {}
            for key, value, quoted_empty in parsed:
                masked.setdefault(key, set()).add(value)
                if quoted_empty:
                    masked[key].add(quoted_empty)   # dotenv 15.0.0 alone reads ''/"" literally
            cls.masked[name] = masked
        missing = cls.what_is_missing()
        if missing:
            if os.environ.get("V2E_REQUIRE_MATRIX"):
                raise AssertionError("NOT VERIFIED: V2E_REQUIRE_MATRIX is set but %s" % "; ".join(missing))
            raise unittest.SkipTest("NOT VERIFIED: %s — the differential matrix did not run (prepare readers "
                                    "with tests/reader_matrix_prepare.py; verification is incomplete, not "
                                    "passed)" % "; ".join(missing))

    @classmethod
    def what_is_missing(cls):
        """Every prerequisite of a full pass, as a list of what is absent (empty when the matrix can run)."""
        missing = []
        if not os.path.exists("/bin/sh"):
            missing.append("no /bin/sh (bash 3.2) on this machine")
        local = shutil.which("node")
        if not local:
            missing.append("no local Node (the v20.20.2 claimed point)")
        else:
            version = subprocess.run([local, "--version"], stdout=subprocess.PIPE).stdout.decode().strip()
            if version != "v20.20.2":
                missing.append("the local Node is %s, not the claimed v20.20.2" % version)
            cls.local_node = local
        manifest_path = MATRIX_DIR / "manifest.json"
        if not manifest_path.exists():
            return missing + ["no prepared reader directory at %s (run tests/reader_matrix_prepare.py)"
                              % MATRIX_DIR]
        try:
            cls.entries = verified_entries(MATRIX_DIR, PROVENANCE, ROOT / "tests/reader_matrix_harness.js")
        except (OSError, ValueError, KeyError, TypeError) as error:
            missing.append("unverified reader artifacts: %s" % error)
        return missing

    # ------------------------------------------------------------------ readers (the experiment's drivers)

    def invoke(self, cmd, **kw):
        try:
            done = subprocess.run(cmd, capture_output=True, timeout=30, **kw)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.fail("NOT VERIFIED: reader invocation failed: %s" % type(error).__name__)
        if done.returncode != 0:
            self.fail("NOT VERIFIED: reader process exited %s" % done.returncode)
        return done

    def values(self, value):
        if (not isinstance(value, dict) or set(value) != {"A", "B", "C"}
                or any(v is not None and not isinstance(v, str) for v in value.values())):
            self.fail("NOT VERIFIED: malformed reader observation")
        return value

    def json_values(self, data):
        try:
            value = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            self.fail("NOT VERIFIED: reader did not return valid JSON")
        return self.values(value)

    def read_bash(self, path):
        script = ('. "$1"; rc=$?; printf "SRC=%s\\n" "$rc" >&2; '
                  'for v in A B C; do eval "val=\\${$v-' + UNSET + '}"; '
                  'printf %s "$val" | /usr/bin/base64 | tr -d "\\n"; printf "\\n"; done')
        done = self.invoke(["env", "-i", "/bin/sh", "-c", script, "_", str(path)], cwd=str(self.tmp))
        if done.stderr.strip() != b"SRC=0":
            self.fail("NOT VERIFIED: shell source did not succeed")
        lines = done.stdout.decode().splitlines()
        if len(lines) != 3:
            self.fail("NOT VERIFIED: malformed shell observation")
        vals = {}
        for key, line in zip(("A", "B", "C"), lines):
            decoded = base64.b64decode(line, validate=True).decode("utf-8") if line else ""
            vals[key] = None if decoded == UNSET else decoded
        return vals

    def read_node(self, nodebin, path):
        done = self.invoke(["env", "-i", nodebin, "--env-file=" + os.path.basename(str(path)), "-e",
                         "const o={};for(const k of['A','B','C'])o[k]=process.env[k]??null;"
                         "process.stdout.write(JSON.stringify(o))"], cwd=str(path.parent))
        return self.json_values(done.stdout)

    def read_dotenv(self, version, path):
        entry = self.entries["dotenv-" + version]
        rundir = self.tmp / ("run-" + version)
        rundir.mkdir(exist_ok=True)
        result = rundir / "result.json"
        if result.exists():
            result.unlink()
        if [int(x) for x in version.split(".")] <= [0, 5, 1]:   # the cwd era: load() reads ./.env
            shutil.copyfile(str(path), rundir / ".env")
            if version == "0.5.0":   # its recorded limitation: empty state without .env.<NODE_ENV> —
                (rundir / ".env.development").write_bytes(b"")   # decodes normally in its two-file setup
            self.invoke(["env", "-i", self.entries["node-v24.21.0"], str(MATRIX_DIR / "harness.js"),
                      entry, str(rundir / ".env"), str(result), "cwd"], cwd=str(rundir))
        else:
            self.invoke(["env", "-i", self.entries["node-v24.21.0"], str(MATRIX_DIR / "harness.js"),
                      entry, str(path), str(result), "path"], cwd=str(rundir))
        try:
            report = json.loads(result.read_text())
        except (OSError, ValueError):
            self.fail("NOT VERIFIED: missing or malformed dotenv result")
        if not isinstance(report, dict) or report.get("failed") is not False:
            self.fail("NOT VERIFIED: dotenv harness failed (partial state is not verified coverage)")
        return self.values(report.get("env", report.get("parsed")))

    def read_pydotenv(self, path):
        code = ("import dotenv, json; v = dotenv.dotenv_values(%r); "
                "print(json.dumps({k: v.get(k) for k in ('A','B','C')}))" % str(path))
        done = self.invoke(["env", "-i", "PYTHONPATH=" + self.entries["python-dotenv-1.2.3"],
                         "/usr/bin/python3", "-B", "-c", code])
        return self.json_values(done.stdout)

    def assert_covered(self, reader, fixture, vals):
        vals = self.values(vals)
        if fixture == "simple":
            self.assertEqual(vals, {"A": "abc", "B": None, "C": None},
                             "NOT VERIFIED: reader failed its known nonempty control")
        for key, value in vals.items():
            if value in (None, ""):
                continue   # reading less can never leak (the export prefix's old readers; empty reads)
            self.assertIn(value, self.masked[fixture].get(key, set()),
                          "%s reads %s=%r for %s — outside the masked set %s"
                          % (reader, key, value, fixture, self.masked[fixture].get(key)))

    # ------------------------------------------------------------------ (b) every divergent form refuses

    def test_every_divergent_form_refuses(self):
        for name, content in REFUSED:
            with self.subTest(form=name):
                text = content.decode("utf-8")
                with self.assertRaises(envliteral.NotLiteral):
                    envliteral.assignments(text.replace("\r\n", "\n").replace("\r", "\n"), text)

    # ---------------------------------------------------------- (a) admitted forms stay in the masked set

    def test_every_claimed_reader_stays_inside_the_masked_set(self):
        dotenv_versions = sorted((name[len("dotenv-"):] for name in self.entries if name.startswith("dotenv-")),
                                 key=lambda v: [int(x) for x in v.split(".")])
        readers = [("bash-3.2(/bin/sh)", None), ("node-envfile-v20.20.2(local)", None)] + [
            ("node-envfile-%s" % name[len("node-"):], name) for name in sorted(self.entries)
            if name.startswith("node-")] + [("dotenv-%s" % v, v) for v in dotenv_versions] + [
            ("python-dotenv-1.2.3", None)]
        self.assertEqual(len(readers), 95, "the claimed reader set changed — update the claim or the matrix")
        for fixture, content in ADMITTED:
            path = self.fixtures / (fixture + ".env")
            for reader, key in readers:
                with self.subTest(fixture=fixture, reader=reader):
                    if reader.startswith("bash"):
                        self.assert_covered(reader, fixture, self.read_bash(path))
                    elif reader.endswith("(local)"):
                        self.assert_covered(reader, fixture, self.read_node(self.local_node, path))
                    elif reader.startswith("node-"):
                        self.assert_covered(reader, fixture, self.read_node(self.entries[key], path))
                    elif reader.startswith("dotenv-"):
                        self.assert_covered(reader, fixture, self.read_dotenv(key, path))
                    else:
                        self.assert_covered(reader, fixture, self.read_pydotenv(path))

    def test_a1_counterexamples_are_real_reader_disagreements_and_refused(self):
        # These inputs deliberately bypass admission only to establish the independent live-reader oracle.
        for prefix in ("", "export "):
            source = prefix + "A='Horse" + "\\" * 2 + "9137Staple'\n"
            path = self.fixtures / "a1-backslash.env"
            path.write_text(source)
            self.assertEqual(self.read_bash(path)["A"], "Horse" + "\\" * 2 + "9137Staple")
            self.assertEqual(self.read_pydotenv(path)["A"], "Horse" + "\\" + "9137Staple")
            with self.assertRaises(envliteral.NotLiteral):
                envliteral.assignments(source)
        source = "A='\u00a0Horse9137Staple\u00a0'\n"
        path = self.fixtures / "a1-nbsp.env"
        path.write_text(source)
        self.assertEqual(self.read_bash(path)["A"], "\u00a0Horse9137Staple\u00a0")
        self.assertEqual(self.read_dotenv("0.4.0", path)["A"], "Horse9137Staple")
        self.assertEqual(self.read_dotenv("6.2.0", path)["A"], "Horse9137Staple")
        with self.assertRaises(envliteral.NotLiteral):
            envliteral.assignments(source)

    def test_dotenv_0_5_0s_recorded_limitation_stands(self):
        # without .env.<NODE_ENV>, 0.5.0's load() fails — it applies values only when BOTH .env and the
        # env-specific file load (`_loadEnv() && _loadEnvDotEnvironment()`, then _setEnvs) — so nothing is
        # applied and the environment stays empty: fail-closed, never a wrong reading (it does not throw;
        # the harness's exception flag stays false). The matrix runs it in its two-file setup above, where it
        # decodes normally
        rundir = self.tmp / "run-0.5.0-alone"
        rundir.mkdir(exist_ok=True)
        shutil.copyfile(str(self.fixtures / "simple.env"), rundir / ".env")
        for stale in (rundir / ".env.development", rundir / "result.json"):
            if stale.exists():
                stale.unlink()
        self.invoke(["env", "-i", self.entries["node-v24.21.0"], str(MATRIX_DIR / "harness.js"),
                     self.entries["dotenv-0.5.0"], str(rundir / ".env"), str(rundir / "result.json"), "cwd"],
                    cwd=str(rundir))
        report = json.loads((rundir / "result.json").read_text())
        self.assertFalse(report.get("failed"), "dotenv 0.5.0 threw — the recorded mechanism (a quiet failed "
                                               "load()) changed; re-check the claim")
        self.assertEqual(report.get("env"), {"A": None, "B": None, "C": None},
                         "dotenv 0.5.0 applied values without .env.<NODE_ENV> — the recorded limitation "
                         "changed; re-check the claim")


if __name__ == "__main__":
    unittest.main()
