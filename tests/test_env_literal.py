"""Tests for the v0.1 literal .env boundary (scripts/envliteral.py; release decision A1, owner-approved
2026-09-27): the grammar itself (admissions with their exact unanimous decodes, and every refused form), the
end-to-end contract through evidence.py (an admitted file runs, its values masked; a refused file stops the run
before the check — exit 2, nothing ran, no evidence), Codex's reproduced brace case as a regression, and the
combination tests the owner directed after it: per-character probing was necessary but not sufficient, so the
admitted set is also exercised in combination — with and without `export ` — against the real readers on this
machine (bash 3.2 as /bin/sh always; the local Node --env-file when present, skipped as NOT VERIFIED otherwise —
set V2E_REQUIRE_NODE=1 to make that a failure). The cross-reader proof over the whole claimed range — Node
v20.7.0, v20.20.2, v22.0.0, v22.16.0, v24.21.0, v26.10.0, npm dotenv 0.4.0–18.0.4, python-dotenv 1.2.3 — is
tests/test_literal_matrix.py; the experiment record behind the boundary is the 2026-09-27 reader-compatibility
bundle named in references/env-boundary.md.

Run from the repository root:  python3 -m unittest discover -s tests -p test_env_literal.py -v
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
sys.path.insert(0, str(ROOT / "skills" / "vibe-to-engineering" / "scripts"))
import envliteral  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


class Grammar(unittest.TestCase):
    """The boundary itself, at unit level: each admitted form with its exact unanimous decode (and the
    dotenv-15.0.0 quoted-empty form), each refused form named with its evidence."""

    def test_admitted_forms_decode_unanimously(self):
        for source, want in {
                "A=abc\n": [("A", "abc", None)],                       # 01-simple
                "A=\n": [("A", "", None)],                             # 02-empty
                "A=abc-def_123./:@x\n": [("A", "abc-def_123./:@x", None)],   # 03-unquoted-punct
                "A=abc   \n": [("A", "abc", None)],                    # 05-trailing-spaces (all strip them)
                "  A=abc\n": [("A", "abc", None)],                     # 06-leading-spaces
                "export A=abc\n": [("A", "abc", None)],                # 08-export (old readers read nothing:
                "A='a b'\n": [("A", "a b", None)],                     # 09  safe direction)
                "A=''\n": [("A", "", "''")],                           # 10 — 15.0.0 reads the two characters
                "A='p@ss#w ord'\n": [("A", "p@ss#w ord", None)],       # 11
                "A='a\\nb'\n": [("A", "a\\nb", None)],                 # 12 — a backslash is literal in '…'
                'A="a b"\n': [("A", "a b", None)],                     # 13
                'A=""\n': [("A", "", '""')],                           # 14
                "# just a comment\nA=x\n": [("A", "x", None)],         # 32-comment-line
                "  # indented comment\nA=x\n": [("A", "x", None)],
                "\n\t\nA=x\n": [("A", "x", None)],                     # blank lines hold nothing
                "A=x\n": [("A", "x", None)],                           # 30-no-trailing-lf is fixture 30's…
                "A=x": [("A", "x", None)],                             # …own bytes, and no trailing LF
                "A='x=y'\n": [("A", "x=y", None)],                     # 44 — '=' inside quotes (0.4.0+ reads it)
                'A="x=y"\n': [("A", "x=y", None)],                     # 45
                'A="it\'s"\n': [("A", "it's", None)],                  # 46 — the other quote is literal
                "A='say \"hi\"'\n": [("A", 'say "hi"', None)],         # 47
                "A='a\tb'\n": [("A", "a\tb", None)],                   # 35 — a literal tab, the one control
                'A="a\tb"\n': [("A", "a\tb", None)],                   # 36   character admitted
                "A=!cmd\n": [("A", "!cmd", None)],                     # c-leading-bang (no history expansion)
                "A=x~y\n": [("A", "x~y", None)],                       # c-7e — '~' mid-value is literal
                "A=x=y\n": [("A", "x=y", None)],                       # c-3d — '=' inside an unquoted value
                "A=   \n": [("A", "", None)],                          # trailing whitespace alone: empty
        }.items():
            with self.subTest(source=source):
                self.assertEqual(envliteral.assignments(source), want)

    def test_every_divergent_form_is_refused(self):
        for name, source in {
                "an inline comment (04)": "A=abc # comment\n",
                "a '#' mid-value (07)": "A=ab#c\n",
                "a backslash-n in double quotes (15)": 'A="a\\nb"\n',
                "an escaped backslash in double quotes (16)": 'A="a\\\\b"\n',
                "an escaped quote in double quotes (17)": 'A="say \\"hi\\""\n',
                "a tab escape in double quotes (18)": 'A="x\\ty"\n',
                "a '$' in single quotes (19)": "A='$HOME'\n",
                "a plain reference (20)": "B=x\nA=$B\n",
                "an operator form (21)": "A=${MISSING:-fallback}\n",
                "a '~' at the value's start (22)": "A=~/x\n",
                "a trailing backslash (23)": "A=ab\\\nC=d\n",
                "backticks (24)": "A=`true`\n",
                "a duplicate name (25)": "A=one\nA=two\n",
                "a duplicate name, same value": "A=one\nA=one\n",
                "a line break inside double quotes (26)": 'A="line1\nline2"\n',
                "CRLF (27)": "A=abc\r\n",
                "a lone carriage return": "A=abc\rB=x\n",
                "spaces around '=' (28)": "A = abc\n",
                "a space after '='": "A= abc\n",
                "whitespace at a quoted value's edge (31)": 'A="  spaced  "\n',
                "the same single-quoted (34)": "A='  spaced  '\n",
                "a tab at a quoted value's edge": "A='\ta'\n",
                "adjacent quotes (33)": "A='a''b'\n",
                "a line break inside single quotes (37)": "A='line1\nline2'\n",
                "a control byte in single quotes (38)": "A='a\x01b'\n",
                "a control byte in double quotes (39)": 'A="a\x01b"\n',
                "a DEL byte in single quotes (40)": "A='a\x7fb'\n",
                "an unquoted tab (41)": "A=a\tb\n",
                "an unquoted space (42)": "A=a b\n",
                "a '~' after ':' with a home path (48)": "A=x:~/x\n",
                "a '~' after ':' (c-tilde-after-colon)": "A=x:~y\n",
                "a bare line (a command to a shell)": "frob\n",
                "a second assignment on the line": "APP=demo DB_PASSWORD=x\n",
                "a quoted name": "'DB_PASSWORD'=x\n",
                "a double-quoted name": '"DB_PASSWORD"=x\n',
                "a colon separator": "DB_PASSWORD: x\n",
                "a name starting with a digit": "2FA_SECRET=x\n",
                "a name holding a dot": "DB.PASSWORD=x\n",
                "two spaces after export": "export  A=x\n",
                "a tab after export": "export\tA=x\n",
                "a tab before the name": "\tA=x\n",
                "a '+=' assignment": "A+=x\n",
                "text after a closing quote": "A='x' extra\n",
                "whitespace after a closing quote (unprobed)": "A='x'  \n",
                "a quote never closed": "A='x\n",
                "an unquoted quote": "A=x'y\n",
                "an unquoted backslash": "A=x\\y\n",
                "a non-ASCII byte unquoted (recorded stricter-than-evidence)": "A=café\n",
        }.items():
            with self.subTest(name):
                with self.assertRaises(envliteral.NotLiteral):
                    envliteral.assignments(source)

    def test_the_file_level_refusals(self):
        with self.assertRaises(envliteral.NotLiteral):   # CRLF as written, though the normalized text hides it
            envliteral.assignments("A=abc\n", "A=abc\r\n")
        with self.assertRaises(envliteral.NotLiteral):   # a byte order mark
            envliteral.assignments("A=abc\n", "\ufeffA=abc\n")

    def test_a_refusal_names_the_line_never_the_text(self):
        try:
            envliteral.assignments("A=x\nDB_PASSWORD=Horse$SECRET-9137\n")
            self.fail("admitted a reference")
        except envliteral.NotLiteral as error:
            self.assertEqual(error.line, 2)
            self.assertNotIn("Horse", str(error))
            self.assertNotIn("SECRET-9137", str(error))


class EndToEnd(unittest.TestCase):
    """Through evidence.py: an admitted file runs with its values masked; a refused file stops the run."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-literal-")).resolve()
        self.count = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check_prints(self, name, files, reader, flags=()):
        """A project holding `files` whose check marks that it ran, then prints what `reader` prints:
        (the tool's exit code, what it showed after the header, the evidence file's text or None, its report,
        whether the check ran)."""
        self.count += 1
        project = self.tmp / (re.sub(r"\W+", "-", name) + "-%d" % self.count)
        (project / ".vibe-to-engineering").mkdir(parents=True)
        for file, content in files.items():
            (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          + reader + "\n")
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(project), "--out", str(out)] + list(flags)
                              + ["--", sys.executable, "-B", "check.py"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=enrolled.environ())
        return (done.returncode, done.stdout.decode("utf-8", "replace"),
                out.read_text(encoding="utf-8") if out.exists() else None,
                done.stderr.decode("utf-8", "replace"), (project / "check-ran").exists())

    def test_an_admitted_file_runs_and_its_values_are_masked(self):
        code, shown, saved, report, ran = self.check_prints(
            "admitted", {".env": "# a comment\nDB_PASSWORD=Hor5e-9137x\nexport API_KEY='p@ss#w ord-9137'\n"
                                 "EMPTY=\nQUOTED_EMPTY=''\n"},
            "print(open('.env').read(), end='')")
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertIsNotNone(saved)
        for text in (shown, saved, report):
            self.assertNotIn("Hor5e-9137x", text)
            self.assertNotIn("p@ss#w ord-9137", text)
        self.assertIn("<masked DB_PASSWORD>", shown)     # the value under its name
        self.assertIn("<masked API_KEY>", shown)
        self.assertIn("QUOTED_EMPTY=<masked QUOTED_EMPTY>", shown)   # dotenv 15.0.0's '' form is masked
        self.assertIn("EMPTY=\n", shown)                 # an empty setting holds no value: left readable

    def test_every_refusal_means_nothing_ran_and_no_evidence(self):
        for name, source in {
                "a reference": "DB_PASSWORD=$FEED-9137\n",
                "a brace pair (Codex's case)": "export A=x{a,b}\n",
                "CRLF": b"DB_PASSWORD=Hor5e-9137x\r\n",
                "a byte order mark": b"\xef\xbb\xbfDB_PASSWORD=Hor5e-9137x\n",
                "a duplicate name": "DB_PASSWORD=Hor5e-9137x\nDB_PASSWORD=other-9137\n",
                "a bare token line": "APP=demo\nc13k-9137-token\n",
        }.items():
            with self.subTest(name):
                code, shown, saved, report, ran = self.check_prints(name, {".env": source}, "print('never')")
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)                    # the check never ran
                self.assertIsNone(saved)                 # and no evidence exists
                self.assertIn(".env", report)
                self.assertIn("cannot be masked", report)
                self.assertNotIn("-9137", shown + report)   # every canary above carries "-9137"; the
                # non-hex '-' can never be spelled by the retained root's random hex name, whose path
                # the report now prints (L3 — the bare "9137" flaked on v2e-run-ba82f9ad9c9137509e)

    def test_the_brace_regression(self):
        # Codex's reproduced case (2026-09-27): export A=x{a,b} becomes A=xb under bash — the brace pair is an
        # operator in export's argument words (each expanded word an assignment, the last winning), while Node
        # and python-dotenv read x{a,b} literally. The v3 per-character probes missed it because isolated braces
        # are literal everywhere; the combination is the operator, and its trigger conditions are too subtle to
        # characterize — so unquoted braces are out of the admitted set entirely, and the boundary refuses the
        # file before launch. Proven here against the real /bin/sh first (a plain assignment line stays literal
        # even under bash; the export form is the one that expands)
        if os.path.exists("/bin/sh"):
            for source, bash_reads in (("export A=x{a,b}\n", "xb"), ("export A=v{1..3}\n", "v3")):
                with self.subTest("bash really expands", source=source.strip()):
                    fixture = self.tmp / ("brace-%d.env" % len(os.listdir(self.tmp)))
                    fixture.write_text(source)
                    out = subprocess.run(["env", "-i", "/bin/sh", "-c", '. "$1"; printf %s "$A"', "_",
                                          str(fixture)], stdout=subprocess.PIPE).stdout.decode()
                    self.assertEqual(out, bash_reads)    # the divergence the refusal exists for
        for source in ("A=x{a,b}\n", "export A=x{a,b}\n", "A=v{1..3}\n", "export A=v{1..3}\n", "A=x{y}\n",
                       "A={x}\n"):
            with self.subTest("refused", source=source.strip()):
                with self.assertRaises(envliteral.NotLiteral):
                    envliteral.assignments(source)
                code, shown, saved, report, ran = self.check_prints("brace " + source.strip(),
                                                                    {".env": source}, "print('never')")
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)
                self.assertIsNone(saved)

    COMBINATIONS = (   # admitted combinations of the allowed set, asserted literal against the real readers
        "f*?[0-9]x",        # a glob run — never expanded (no globbing without a matching path, but refused-era
        "*?[]^_*",          #   forms hid operators; the boundary keeps only what every reader reads literally)
        "!cmd!rm",          # a leading '!' word
        "a::b::c",          # a ':' run
        "a==b=c",           # an '=' run
        "pre_FIX-01./:@x=y",  # the punctuation set together
        "x~y~z",            # '~' mid-value
    )
    QUOTED_COMBINATIONS = ("a{b}c",)   # braces are literal inside quotes only (unquoted they are refused)

    def test_admitted_combinations_read_literally_with_and_without_export(self):
        for value in self.COMBINATIONS:
            for line in ("A=%s\n" % value, "export A=%s\n" % value,
                         "A='%s'\n" % value, "export A=\"%s\"\n" % value):
                with self.subTest(line=line.strip()):
                    self.assertEqual(envliteral.assignments(line)[0][1], value)
        for value in self.QUOTED_COMBINATIONS:
            for line in ("A='%s'\n" % value, "export A=\"%s\"\n" % value):
                with self.subTest(line=line.strip()):
                    self.assertEqual(envliteral.assignments(line)[0][1], value)
        for value in self.COMBINATIONS:
            for prefix in ("", "export "):
                source = "%sA=%s\n" % (prefix, value)
                with self.subTest("bash reads it literally", source=source.strip()):
                    if not os.path.exists("/bin/sh"):
                        self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
                    fixture = self.tmp / ("combo-%d.env" % len(os.listdir(self.tmp)))
                    fixture.write_text(source)
                    out = subprocess.run(["env", "-i", "/bin/sh", "-c", '. "$1"; printf %s "$A"', "_",
                                          str(fixture)], stdout=subprocess.PIPE).stdout.decode()
                    self.assertEqual(out, value)
        node = shutil.which("node")
        for value in self.COMBINATIONS:
            for prefix in ("", "export "):
                source = "%sA=%s\n" % (prefix, value)
                with self.subTest("node reads it literally", source=source.strip()):
                    if not node:
                        if os.environ.get("V2E_REQUIRE_NODE"):
                            self.fail("NOT VERIFIED: V2E_REQUIRE_NODE is set but no node is on the PATH")
                        self.skipTest("NOT VERIFIED: no node on the PATH, so the combination was not checked "
                                      "against a real Node")
                    folder = self.tmp / ("node-%d" % len(os.listdir(self.tmp)))
                    folder.mkdir()
                    (folder / ".env").write_text(source)
                    out = subprocess.run([node, "--env-file=.env", "-e",
                                          "process.stdout.write(process.env.A ?? '')"], cwd=str(folder),
                                         stdout=subprocess.PIPE).stdout.decode()
                    self.assertEqual(out, value)

    def test_refused_combinations_with_and_without_export(self):
        # the combination forms the owner named after the brace case: {a,b} and {x..y} (refused by the brace
        # removal) and '~' after ':' (bash expands it through the account database) — each with and without export
        for line in ("A=x{a,b}\n", "A=v{1..3}\n", "A=x:~y\n", "A=~/x\n"):
            for prefix in ("", "export "):
                source = prefix + line
                with self.subTest(source=source.strip()):
                    with self.assertRaises(envliteral.NotLiteral):
                        envliteral.assignments(source)
                    code, shown, saved, report, ran = self.check_prints("combo refusal", {".env": source},
                                                                        "print('never')")
                    self.assertEqual(code, 2, report)
                    self.assertFalse(ran)
                    self.assertIsNone(saved)


if __name__ == "__main__":
    unittest.main()
