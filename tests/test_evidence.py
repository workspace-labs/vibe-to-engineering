"""Tests for scripts/evidence.py: a check's output is kept as evidence with every secret value masked, only inside
the project's evidence folder.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import json
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

    def run_tool(self, out, *command, env=(), without=()):   # without: names taken out of the tool's environment
        settings = [part for setting in env for part in ("--env", setting)]
        parent = {name: value for name, value in os.environ.items() if name not in without}
        if "HOME" not in without:
            parent["HOME"] = str(enrolled.enrolled_home())   # the isolated enrolled registry (A2)
        done = subprocess.run([sys.executable, str(TOOL), "--project", str(self.project), "--out", str(out)] + settings
                              + ["--"] + list(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=parent)
        return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")

    def refused_run(self, name, files, secrets, blamed, reader="print('ran')", env=()):
        """The shared refusal contract: a secret file outside the literal grammar stops the run before the
        check — exit code 2, the check's ran-marker absent, no evidence file, the report naming the file and
        saying it cannot be masked, and no secret word in the report or on the screen."""
        with self.subTest(name):
            project = self.tmp / re.sub(r"\W+", "-", name)
            (project / ".vibe-to-engineering").mkdir(parents=True)
            for file, content in files.items():
                (project / file).parent.mkdir(parents=True, exist_ok=True)
                (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
            (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                              + reader + "\n")
            self.project = project
            out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py", env=env)
            self.assertEqual(code, 2, report)
            self.assertFalse((project / "check-ran").exists())      # the check never ran
            self.assertFalse(out.exists())
            self.assertIn(blamed, report)
            self.assertIn("cannot be masked", report)
            for secret in secrets:
                self.assertNotIn(secret, report + printed)
            return printed

    def admitted_run(self, name, files, reader, env=()):
        """The shared run contract for a file the grammar reclassifies as ordinary assignments: the check
        runs — exit code 0 and the check's ran-marker present. Returns the project, the check's output below
        the header, the saved evidence, and the report."""
        with self.subTest(name):
            project = self.tmp / re.sub(r"\W+", "-", name)
            (project / ".vibe-to-engineering").mkdir(parents=True)
            for file, content in files.items():
                (project / file).parent.mkdir(parents=True, exist_ok=True)
                (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
            (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                              + reader + "\n")
            self.project = project
            out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py", env=env)
            self.assertEqual(code, 0, report)
            self.assertTrue((project / "check-ran").exists())
            return project, printed.split("\n\n", 1)[1], out.read_text(encoding="utf-8"), report

    def test_no_secret_value_reaches_the_evidence_file_or_the_screen(self):
        out = self.folder / "00-baseline" / "tests.txt"
        code, printed, report = self.run_tool(out, sys.executable, "-c", CHECK)
        self.assertEqual(code, 0, report)   # the check ran and its evidence was saved (R2-F6: the wrapper's
        self.assertIn("the check exited 3", report)   # status is its own; the check's exit 3 is recorded data)
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
        # D4 rule 4 (NEW-5 stage 1): a declared value is sensitive from admission, so the evidence masks it — the
        # redirection itself (the check read the throwaway path, nothing else) is unchanged
        self.assertIn("DB at <masked DB_PATH>", printed)
        self.assertNotIn(str(throwaway), printed)

    def test_a_name_the_env_flag_gives_the_check_never_stops_the_run(self):
        # round 8 (B6): a .env name the environment the check inherits already holds stops the run, because
        # python-dotenv's load_dotenv() keeps that value over the file's — but a name --env gives is this tool's own
        # setting for the check, written in the evidence's header: pointing a check at throwaway data still works.
        # Stage 1 (D4 rules 4–5): the exclusion mechanism round 8 did this with is superseded — the declared name
        # joins the precedence analysis, the reading it wins is determinable from the constructed environment, and
        # the declared value is masked as the winner, never refused, never shown
        (self.project / ".env").write_text("DB_PASSWORD=Horse9137Staple\n")
        code, printed, report = self.run_tool(self.folder / "check.txt", sys.executable, "-c",
                                              "import os; print('uses', os.environ['DB_PASSWORD'])",
                                              env=["DB_PASSWORD=throwaway-4471"])
        self.assertEqual(code, 0, report)
        self.assertIn("uses <masked DB_PASSWORD>", printed)
        for text in (printed, report, (self.folder / "check.txt").read_text(encoding="utf-8")):
            self.assertNotIn("throwaway-4471", text)
            self.assertNotIn("Horse9137Staple", text)

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

    def test_every_value_a_secret_file_holds_is_masked_however_it_is_written(self):
        token = "fixture-ordinary-value-73921"
        outside = self.tmp / "linked-value.env"
        outside.write_text("SECRET_KEY=%s\n" % token)
        cases = {   # the independent review's five leaks (2026-09-24), and the forms an agent meets
            "a JSON credentials file": (
                ("credentials.json", '{"password": "%s"}' % token),
                "import json; print(json.load(open('credentials.json'))['password'])"),
            "a three-character password, printed bare": (
                (".env", "PASSWORD=xyz\n"), "print(open('.env').read().split('=',1)[1].strip())"),
            "a .env that is a link": ((".env", outside), "print(open('.env').read().split('=',1)[1])"),
            "a quoted value with an escaped quote": (
                ("secrets.yaml", 'token: "abc\\"def-98765"\n'), "print('abc\"def-98765')"),
            "a YAML value under a nested key": (
                ("credentials.yml", "db:\n  password: %s\n" % token), "print('%s')" % token),
        }
        for name, ((file, content), check) in cases.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                if isinstance(content, Path):
                    os.symlink(str(content), str(project / file))
                else:
                    (project / file).write_text(content)
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-c", check)
                self.assertEqual(code, 0, report)
                secret = "xyz" if "three" in name else 'abc"def-98765' if "escaped" in name else token
                for word in secret.split():                 # no part of the value survives, not only the whole
                    self.assertNotIn(word, printed.split("\n\n", 1)[1])   # (the header repeats the check's code)
                    self.assertNotIn(word, out.read_text(encoding="utf-8").split("\n\n", 1)[1])
                    self.assertNotIn(word, report)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "an inline comment after the value" and "an inline comment
        # after a value with spaces" expected the run to go ahead with each value masked as python-dotenv reads it;
        # the grammar admits no unquoted '#' and no interior whitespace in an unquoted value (readers disagree: a
        # shell cuts the value there, python-dotenv keeps it) — and the second file also assigns SECRET_KEY twice
        # (dotenv 0.1.1 takes the first, every other reader the last) — so each file now refuses before launch.
        self.refused_run("an inline comment after the value",
                         {".env": "SECRET_KEY=%s # fixture-only comment\n" % token}, (token,), ".env")
        self.refused_run("an inline comment after a value with spaces",
                         {".env": "SECRET_KEY=quorble zaxtic wembly # fixture-only comment\nSECRET_KEY=quorble\n"},
                         ("quorble", "zaxtic", "wembly"), ".env")

    def test_a_value_in_any_written_form_is_masked_and_a_secret_file_that_is_not_text_stops_the_run(self):
        token = "roundtwo-synthetic-value-93715"
        cases = {   # the independent round-2 review's leaks (2026-09-24, night), and their neighbours
            "a JSON value written with escapes": (
                "credentials.json", '{"password": "roundtwo-synthetic-value-\\u0039\\u0033\\u0037\\u0031\\u0035"}',
                "import json; print(json.load(open('credentials.json'))['password'])", (token,)),
            "a JSON list of values": (
                "credentials.json", '{"passwords": ["%s", "other-synthetic-value-4471"]}' % token,
                "import json; print(*json.load(open('credentials.json'))['passwords'])",
                (token, "other-synthetic-value-4471")),
            "a YAML value written with escapes": (   # decoded by the reader, in a file that is not JSON
                "secrets.yaml", 'token: "roundtwo-synthetic-value-\\u0039\\u0033\\u0037\\u0031\\u0035"\n',
                "import json; print(json.loads(open('secrets.yaml').read().split(': ', 1)[1]))", (token,)),
            "a YAML block value": (
                "secrets.yaml", "password: |-\n  %s\n" % token,
                "print(open('secrets.yaml').read().splitlines()[1].strip())", (token,)),
            "a YAML block line that looks like a comment": (
                "secrets.yaml", "password: |-\n  #not-a-comment-98213\n",
                "print(open('secrets.yaml').read().splitlines()[1].strip())", ("#not-a-comment-98213",)),
            "a YAML folded value over two lines": (
                "secrets.yaml", "password: >\n  %s\n  second-synthetic-line-8802\n" % token,
                "print(open('secrets.yaml').read().splitlines()[2].strip())", (token, "second-synthetic-line-8802")),
            "one line of a private key's body": (
                "id_rsa", "-----BEGIN PRIVATE KEY-----\n%s\n-----END PRIVATE KEY-----\n" % token,
                "print(open('id_rsa').read().splitlines()[1])", (token,)),
            "a key file holding one bare value": (
                "api.key", "%s\n" % token, "print(open('api.key').read().strip())", (token,)),
            "a UTF-16 credentials file with a byte order mark": (
                "credentials.json", ('{"password": "%s"}' % token).encode("utf-16"),
                "import json; print(json.loads(open('credentials.json', 'rb').read().decode('utf-16'))['password'])",
                (token,)),
        }
        for name, (file, content, check, secrets) in cases.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-c", check)
                self.assertEqual(code, 0, report)
                for secret in secrets:
                    self.assertNotIn(secret, printed.split("\n\n", 1)[1])   # (the header repeats the check's code)
                    self.assertNotIn(secret, out.read_text(encoding="utf-8").split("\n\n", 1)[1])
                    self.assertNotIn(secret, report)
                self.assertIn("<masked", printed)
        refused = {   # not text this tool can read: the run stops before the check, naming the file
            "a UTF-16 file without a byte order mark": (".env", ("PASSWORD=%s\n" % token).encode("utf-16-le")),
            "a binary key container": ("release.p12", b"\x30\x82\x01\x0a\x02\x01\x03" + bytes(range(256))),
        }
        for name, (file, content) in refused.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                (project / file).write_bytes(content)
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-c", "print('ran')")
                self.assertEqual(code, 2, report)
                self.assertNotIn("ran", printed)
                self.assertIn(file, report)
                self.assertIn("not text this tool can read", report)
                self.assertNotIn(token, report)
                self.assertFalse(out.exists())
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "a quoted .env value over two lines" expected the run with
        # the value masked as python-dotenv reads it across the lines; the grammar admits a quoted value only closed
        # on its own line (a line break inside quotes refuses — readers disagree on where the value ends), so the
        # run now stops before the check, naming the file.
        printed = self.refused_run("a quoted .env value over two lines",
                                   {".env": 'PASSWORD="first-line\n%s"\n' % token}, (token,), ".env")
        self.assertNotIn("ran", printed)

    def test_a_value_is_masked_completely_in_every_format_the_tool_reads_or_the_file_stops_the_run(self):
        token, other, body = "r3-synthetic-value-58392", "r3-second-value-81724", "cjMtc3ludGhldGljLWtleS1wYWRkaW5nLQ=="

        def run_check(name, file, content, reader):
            """The check is a file, so the command line holds no value: it marks that it ran, then reads the secret
            file and prints the value."""
            project = self.tmp / re.sub(r"\W+", "-", name)
            (project / ".vibe-to-engineering").mkdir(parents=True)
            (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
            (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                              + reader + "\n")
            self.project = project
            out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
            return out, code, printed, report, (project / "check-ran").exists()

        load_json = "import json; print(json.loads(open('credentials.json', 'rb').read())['password'])"
        masked = {   # the independent round-3 review's six exposures (2026-09-24), each value and each piece it left
            "a YAML flow list": (
                "credentials.yaml", 'passwords: ["%s", "%s"]\n' % (token, other),
                "import json; print(*json.loads(open('credentials.yaml').read().split(':', 1)[1]))", (token, other)),
            "a YAML block header with a comment": (
                "secrets.yaml", "password: |- # ordinary YAML comment\n  #r3-secret-value-58392\n",
                "print(open('secrets.yaml').read().splitlines()[1].strip())", ("#r3-secret-value-58392",)),
            "a TOML triple-quoted value": (
                "secrets.toml", 'password = """%s"""\n' % token,
                "print(open('secrets.toml').read().split(chr(34) * 3)[1])", (token,)),
            "a TOML multi-line value with escapes": (
                "secrets.toml", 'password = """\nr3-decoded-value-\\u0039\\u0033\\u0037\\u0031\\u0035"""\n',
                "import json; s = open('secrets.toml').read().split(chr(34) * 3)[1].lstrip(chr(10)); "
                "print(json.loads(chr(34) + s + chr(34)))", ("r3-decoded-value-93715",)),
            "a YAML single-quoted value with a doubled quote": (
                "secrets.yaml", "password: 'r3-don''t-disclose-58392'\n",
                "s = open('secrets.yaml').read().split(':', 1)[1].strip(); "
                "print(s[1:-1].replace(chr(39) * 2, chr(39)))",
                ("r3-don't-disclose-58392", "'t-disclose-58392")),
            "a private key body with padding": (   # the payload must not survive, not even as a mask's name
                "id_rsa", "-----BEGIN PRIVATE KEY-----\n%s\n-----END PRIVATE KEY-----\n" % body,
                "print(open('id_rsa').read().splitlines()[1])", (body, body.rstrip("="))),
            # forms that must keep working
            "a plain YAML value over two lines": (
                "secrets.yaml", "password: %s\n  %s\n" % (token, other),
                "s = open('secrets.yaml').read().split(':', 1)[1]; print(' '.join(x.strip() for x in s.splitlines()))",
                (token, other)),
            "an exported quoted value": (
                ".env", 'export PASSWORD="%s"\n' % token,
                "print(open('.env').read().split('=', 1)[1].strip().strip(chr(34)))", (token,)),
            "a quoted value printed with its quotes": (
                ".env", 'PASSWORD="%s"\n' % token, "print(open('.env').read().split('=', 1)[1].strip())", (token,)),
            "pretty UTF-16 JSON with a byte order mark": (
                "credentials.json", json.dumps({"password": token}, indent=2).encode("utf-16"), load_json, (token,)),
            "a JSON value holding regular-expression signs": (
                "credentials.json", json.dumps({"password": "r3.[a-z]+(x)?^$-58392"}), load_json,
                ("r3.[a-z]+(x)?^$-58392",)),
            "UTF-32 JSON": ("credentials.json", json.dumps({"password": token}).encode("utf-32"), load_json, (token,)),
            "UTF-8 JSON with a byte order mark": (
                "credentials.json", json.dumps({"password": token}).encode("utf-8-sig"), load_json, (token,)),
        }
        for name, (file, content, reader, secrets) in masked.items():
            with self.subTest(name):
                out, code, printed, report, ran = run_check(name, file, content, reader)
                self.assertEqual(code, 0, report)
                self.assertTrue(ran)
                self.assertTrue(out.exists())
                for secret in secrets:
                    self.assertNotIn(secret, printed.split("\n\n", 1)[1])
                    self.assertNotIn(secret, report)
                    self.assertNotIn(secret, out.read_text(encoding="utf-8"))
                self.assertIn("<masked", printed)
        refused = {   # a form the reader does not understand: the run stops before the check, naming the file
            "a TOML triple-quoted value never closed": ("secrets.toml", 'password = """%s\n' % token),
            "a YAML explicit key": ("secrets.yaml", "? password\n: %s\n" % token),
            "a YAML flow list never closed": ("credentials.yaml", 'passwords: ["%s", "%s"\n' % (token, other)),
            "a .env quote never closed": (".env", 'PASSWORD="%s\n' % token),
            # SUPERSEDED (A1 literal boundary, 2026-09-27): "an empty value, then a bare line" expected the run with
            # the bare line's token masked (round 8: a shell runs the bare line as a command); the grammar admits
            # no bare line (a line is blank, a '#' comment, or NAME=VALUE) and no name assigned twice (dotenv 0.1.1
            # takes the first, every other reader the last), so the file now refuses before launch.
            "an empty value, then a bare line": (".env", "NAME=\n%s\nNAME=\n" % token),
        }
        for name, (file, content) in refused.items():
            with self.subTest(name):
                out, code, printed, report, ran = run_check(name, file, content, "print(open(%r).read())" % file)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)                                      # the check never ran
                self.assertFalse(out.exists())
                self.assertIn(file, report)
                self.assertIn("cannot be masked", report)
                for secret in (token, other):
                    self.assertNotIn(secret, report + printed)

    def test_a_value_inside_another_value_or_a_bare_token_line_is_masked_and_never_named(self):
        # the first independent check of the round-4 repair (2026-09-25) and the rulings on it: a NAME=VALUE part of a
        # value (R1), a bare token line (R2), a data-format extension before a .env name (R4), a mask whose name would
        # hold a value from any secret file (R5), a .env value as Node, a shell or an interpolating reader reads it
        # (R6), Java .properties (R7), a Helm template (R8), a stripped value (R9); and an INI file with an option
        # before any [section], which stops the run (R3).
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the R2 bare-token-in-.env, R4 .env.local and R6 reader cases
        # rested on files outside the literal grammar — they are refusal cases below, except the two '='-padding
        # lines the grammar reads as ordinary assignments, also below.
        slash = chr(92)
        padded, single = "cjMtZW52LXBhZGRlZC10b2tlbi00Nw==", "cjMtZW52LXNpbmdsZS1wYWQtNDgwMTE="
        commented = "cjMtZW52LXBhZC1jb21tZW50LTM1MDE="
        glued, glued_one, glued_text = ("cjMtZW52LWdsdWVkLW9uZS0zNjAyMQ==", "cjMtZW52LWdsdWVkLXBhZC0zNjE=",
                                        "cjMtdHh0LWdsdWVkLXBhZC0zNzAxeA==")
        value_of = "line = next(x for x in open(%r).read().splitlines() if %r in x); "
        java = ("import re; text = re.sub(chr(92) * 2 + chr(10) + '[ ' + chr(9) + ']*', '', open(%r).read()); "
                "text = re.sub(chr(92) * 2 + 'u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text); "
                "values = {k.strip(): v.strip() for k, v in (x.split('=', 1) for x in text.splitlines() "
                "if '=' in x)}; ")
        cases = {   # name: ({file: text}, what the check prints, the values and pieces that must not be seen, the mask
            #                that must be seen (its name holds no secret text), and any text that must stay readable)
            "R1 a NAME=VALUE entry in a YAML list": (
                {"secrets.yaml": "services:\n  db:\n    environment:\n      - POSTGRES_PASSWORD=r3-compose-pass-1801\n"
                                 "      - POSTGRES_USER=admin\n"},
                value_of % ("secrets.yaml", "_PASSWORD=") + "print('connecting with', line.split('=', 1)[1])",
                ("r3-compose-pass-1801",), "<masked environment>"),
            "R1 a password= parameter in a YAML value": (
                {"secrets.yaml": "database_url: postgres://app@db:5432/app?sslmode=require"
                                 "&password=r3-dsn-pass-1901\n"},
                "from urllib.parse import urlsplit, parse_qs; url = open('secrets.yaml').read().split(': ', 1)[1]; "
                "print(parse_qs(urlsplit(url.strip()).query)['password'][0])", ("r3-dsn-pass-1901",),
                "<masked database_url>"),
            "R1 a Password= part of a JSON connection string": (
                {"secrets.json": '{"ConnectionStrings:Default": '
                                 '"Server=db;User Id=sa;Password=r3-mssql-pass-3301;"}\n'},
                "import json; cs = json.load(open('secrets.json'))['ConnectionStrings:Default']; "
                "parts = dict(p.split('=', 1) for p in cs.split(';') if p); print('with', parts['Password'])",
                ("r3-mssql-pass-3301",), "<masked ConnectionStrings:Default>"),
            "R1 a Password= part of a YAML connection string": (
                {"secrets.yaml": 'ConnectionStrings:\n'
                                 '  Default: "Server=db;User Id=sa;Password=r3-yaml-mssql-3401;"\n'},
                "cs = open('secrets.yaml').read().split(chr(34))[1]; "
                "parts = dict(p.split('=', 1) for p in cs.split(';') if p); print('with', parts['Password'])",
                ("r3-yaml-mssql-3401",), "<masked Default>"),
            "R1 a Password= part of a quoted .env value": (
                {".env": 'SQL_CONN="Server=db;User Id=sa;Password=r3-mssql-env-5001;"\n'},
                "cs = open('.env').read().split('=', 1)[1].strip().strip(chr(34)); "
                "parts = dict(p.split('=', 1) for p in cs.split(';') if p); print('with', parts['Password'])",
                ("r3-mssql-env-5001",), "<masked SQL_CONN>"),
            "R1 a PIN in a list entry under an ordinary name": (
                {"secrets.yaml": "environment:\n  - DB_PIN=4821\n"},
                value_of % ("secrets.yaml", "DB_PIN") + "print('pin', line.split('=', 1)[1])", ("4821",),
                "<masked secret in environment>"),
            "R2 a padded token with a comment glued on, in a text secret file": (
                {"secret.txt": "%s#old\n" % glued_text}, "print(open('secret.txt').read().split('#')[0].strip())",
                (glued_text, glued_text.rstrip("=")), "<masked secret.txt>"),
            "R2 a secret file with no extension holding a == padded token": (
                {"jwt-secret": padded + "\n"}, "print(open('jwt-secret').read().strip())", (padded, padded.rstrip("=")),
                "<masked jwt-secret>"),
            "R2 a secret file with no extension holding a token with one =": (
                {"api-secret": single + "\n"}, "print(open('api-secret').read().strip())", (single, single.rstrip("=")),
                "<masked api-secret>"),
            "R2 a padded token and its inline comment in a text secret file": (
                {"secret.txt": "%s # old\n" % commented}, "print(open('secret.txt').read().split()[0])",
                (commented, commented.rstrip("=")), "<masked secret.txt>"),
            "R2 a bare line after a name with nothing after its colon, in a text secret file": (
                {"secret.txt": "password:\n  r3-text-after-colon-8802\n"},
                "print(open('secret.txt').read().splitlines()[1].strip())", ("r3-text-after-colon-8802",),
                "<masked secret.txt>"),
            "R2 a short value of signs in a text secret file": (
                {"secret.txt": "password: !@#\n"}, "print('password is', open('secret.txt').read().split()[-1])",
                ("!@#",), "<masked secret.txt>"),
            "R4 a YAML flow list in .env.yaml": (
                {".env.yaml": 'API_KEYS: ["r3-envyaml-key-2001", "r3-envyaml-key-2002"]\nREGION: me-central-1\n'},
                "import json; print(*json.loads(open('.env.yaml').read().splitlines()[0].split(': ', 1)[1]))",
                ("r3-envyaml-key-2001", "r3-envyaml-key-2002"), "<masked API_KEYS>"),
            "R4 a TOML multi-line value with escapes in .env.toml": (
                {".env.toml": 'password = """r3-envtoml-' + slash + "u0041" + slash + 'u0042-2201"""\n'},
                "import json; print(json.loads(chr(34) + open('.env.toml').read().split(chr(34) * 3)[1] + chr(34)))",
                ("r3-envtoml-AB-2201",), "<masked password>"),
            "R4 a Java .properties value in .env.properties": (
                {".env.properties": "db.password=r3-envprop-" + slash + "u0043-2301\n"},
                java % ".env.properties" + "print(values['db.password'])", ("r3-envprop-C-2301",),
                "<masked db.password>"),
            "R5 a key that holds another file's value": (   # only a mask's name could show the .env value
                {".env": "TOKEN=r3-inlabel-longer-value-9301\n",
                 "secrets.yaml": "r3-inlabel-longer-value-9301-backup: v-9302x\n"},
                "print(open('secrets.yaml').read().split(': ', 1)[1].strip())",
                ("r3-inlabel-longer-value-9301", "v-9302x"), "<masked secrets.yaml>"),
            "R5 a key that holds another file's short value as a word": (
                {".env": "PIN=Q7X\n", "secrets.yaml": "backup_Q7X_key: r3-short-in-name-9401\n"},
                "print(open('secrets.yaml').read().split(': ', 1)[1].strip())", ("Q7X", "r3-short-in-name-9401"),
                "<masked secrets.yaml>"),
            "R5 a PIN whose name holds another value": (   # the mask still says secret, so the PIN stays masked
                {".env": "APP=DEMO\nDEMO_PIN=4821\n"}, "print('pin', open('.env').read().split('=')[-1].strip())",
                ("4821",), "<masked secret in .env>"),
            "R5 a secret file whose own name holds a value": (
                {".env": "TOKEN=r3-namefile-7777\n", "r3-namefile-7777-secret.txt": "r3-filenamed-line-7778\n"},
                "print(open('r3-namefile-7777-secret.txt').read().strip())",
                ("r3-namefile-7777", "r3-filenamed-line-7778"), "<masked secret file>"),
            "R7 a Java .properties value written with escapes": (
                {"secrets.properties": "db.password=r3-prop-" + slash + "u0041" + slash + "u0042-9701\n"
                                       "api.key = r3-prop-plain-9702\n"},
                java % "secrets.properties" + "print(values['db.password'], values['api.key'])",
                ("r3-prop-AB-9701", "r3-prop-plain-9702"), "<masked db.password>"),
            "R7 a Java .properties value continued on the next line": (
                {"secrets.properties": "db.password = r3-first-part-" + slash + "\n      r3-second-part-9801\n"},
                java % "secrets.properties" + "print(values['db.password'])",
                ("r3-first-part", "r3-second-part-9801"), "<masked db.password>"),
            "R8 a Helm template holding {{ }}": (   # not YAML data: read as text, never refused
                {"chart/templates/secret.yaml": "apiVersion: v1\nkind: Secret\nmetadata:\n"
                                                "  name: {{ .Release.Name }}-db\nstringData:\n"
                                                "  password: {{ .Values.dbPassword | quote }}\n"
                                                "  literal: r3-helm-literal-9901\n{{- if .Values.extra }}\n"
                                                "  extra: r3-helm-extra-9902\n{{- end }}\n"},
                value_of % ("chart/templates/secret.yaml", "literal:") + "print(line.split(': ', 1)[1])",
                ("r3-helm-literal-9901",), "<masked secret.yaml>"),
            "R9 a TOML value with spaces around it, printed stripped": (
                {"secrets.toml": 'password = "  r3-padded-value-9911  "\n'},
                "import json; print(json.loads(open('secrets.toml').read().split('= ', 1)[1]).strip())",
                ("r3-padded-value-9911",), "<masked password>"),
        }
        for name, (files, reader, secrets, mask, *kept) in cases.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                for file, content in files.items():
                    (project / file).parent.mkdir(parents=True, exist_ok=True)
                    (project / file).write_text(content)
                (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                                  + reader + "\n")
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
                self.assertEqual(code, 0, report)
                self.assertTrue((project / "check-ran").exists())
                shown, saved = printed.split("\n\n", 1)[1], out.read_text(encoding="utf-8")
                for secret in secrets:
                    self.assertNotIn(secret, shown)
                    self.assertNotIn(secret, report)
                    self.assertNotIn(secret, saved)
                self.assertIn(mask, shown)          # the value's mask, named by the file or by a name without it
                self.assertIn(mask, saved)
                for text in kept:
                    self.assertIn(text, shown)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each of these .env cases expected the run with its value
        # masked as one reader reads it; every fixture is outside the literal grammar, so the run now refuses
        # before launch — "R1 a password= parameter in an unquoted .env URL": '&' is outside the probed unquoted
        # set; "R1 a double-quoted .env value as a shell reads it": a '$' in a value (interpolation — bash expands
        # it, dotenv 0.3–1.2 even inside single quotes); the three R2 comment cases and "R6 a .env value Node ends
        # at #": an unquoted '#' (readers disagree on cut vs keep); "R4 a .env.local file read as Node reads a .env
        # file": '.env.local' matches '.env.*' and its unquoted '#' refuses the same way; "R6 a .env name starting
        # with a digit": a NAME is [A-Za-z_][A-Za-z0-9_]*, a shell's name; both R6 reference cases: a '$' in a
        # value, even inside single quotes.
        refused = {   # name: ({file: text}, the values and pieces that must not be seen, the file the report names)
            "R1 a password= parameter in an unquoted .env URL": (
                {".env": "DATABASE_URL=postgres://db/app?user=app&password=r3-pg-5101\n"}, ("r3-pg-5101",), ".env"),
            "R1 a double-quoted .env value as a shell reads it": (
                {".env": 'PASSWORD="r3' + slash + '$dollar-4401"\n'}, ("r3$dollar-4401", "$dollar-4401"), ".env"),
            "R2 a bare .env token and its inline comment": (
                {".env": "%s # rotated\n" % commented}, (commented, commented.rstrip("=")), ".env"),
            "R2 a bare .env token with a comment glued on, as Node reads it": (
                {".env": "APP_NAME=demo\n%s#rotated\n" % glued}, (glued, glued.rstrip("=")), ".env"),
            "R2 a bare .env token with one = and a comment glued on": (
                {".env": "APP_NAME=demo\n%s#rotated\n" % glued_one}, (glued_one, glued_one.rstrip("=")), ".env"),
            "R4 a .env.local file read as Node reads a .env file": (
                {".env.local": "DB_PASSWORD=r3node-local-2401#tail-2402\n"}, ("r3node-local-2401",), ".env.local"),
            "R6 a .env name starting with a digit": (
                {".env": "2FA_SECRET=r3-twofactor-4601\n"}, ("r3-twofactor-4601",), ".env"),
            "R6 a .env value Node ends at #": (
                {".env": "DB_PASSWORD=r3node-4501#tail-4502\n"}, ("r3node-4501",), ".env"),
            "R6 a .env value after its NAME reference is filled in": (
                {".env": 'SALT_PART=r3-salt-part-4901\nPASSWORD="r3-literal-lead-${SALT_PART}"\n'},
                ("r3-literal-lead", "r3-salt-part-4901"), ".env"),
            "R6 a .env value whose bare reference names a later line": (
                {".env": "PASSWORD='r3-lit-$SUFFIX_PART'\nSUFFIX_PART=r3-suffix-5601\n"},
                ("r3-lit-", "r3-suffix-5601"), ".env"),
        }
        for name, (files, secrets, blamed) in refused.items():
            self.refused_run(name, files, secrets, blamed)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "R2 a bare .env token with == padding" and "... with one = of
        # padding" expected the whole line masked as a bare token ("<masked .env>"); the grammar reads each line as
        # an ordinary assignment every claimed reader decodes alike (a NAME over A-Za-z0-9, '=', then a value of '='
        # signs or empty), so the line stays readable and every other = is untouched.
        for name, bare in (("R2 a bare .env token with == padding", padded),
                           ("R2 a bare .env token with one = of padding", single)):
            _, shown, _, _ = self.admitted_run(name, {".env": "APP_NAME=demo\n%s\n" % bare},
                                               "print(open('.env').read().splitlines()[1]); print('x = y == z')")
            self.assertIn(bare, shown)                  # an ordinary assignment: its name is not a secret
            self.assertIn("x = y == z", shown)          # a lone = is never a value: every other = stays readable
            self.assertNotIn("<masked", shown)
        project = self.tmp / "settings-in-a-list"   # a number in a list entry under ordinary names stays readable
        (project / ".vibe-to-engineering").mkdir(parents=True)
        (project / "secrets.yaml").write_text("environment:\n  - PORT=8000\n  - API_TOKEN=r3-list-token-8803\n")
        self.project = project
        code, printed, report = self.run_tool(project / ".vibe-to-engineering" / "evidence" / "check.txt",
                                              sys.executable, "-c", "print('listening on 8000')")
        self.assertEqual(code, 0, report)
        self.assertIn("listening on 8000", printed.split("\n\n", 1)[1])
        project = self.tmp / "ini-option-before-any-section"   # not INI, as configparser says: the run stops
        (project / ".vibe-to-engineering").mkdir(parents=True)
        (project / "secrets.conf").write_text("user = admin\npassword = r3-conf-o3801\n")
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          "print(open('secrets.conf').read())\n")
        self.project = project
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
        self.assertEqual(code, 2, report)
        self.assertFalse((project / "check-ran").exists())                # the check never ran
        self.assertFalse(out.exists())
        self.assertIn("secrets.conf", report)
        self.assertIn("cannot be masked", report)
        self.assertNotIn("r3-conf-o3801", report + printed)

    def test_a_setting_token_part_or_standard_reading_of_a_value_is_masked_and_never_named(self):
        # the three lens checks of the round-4 repair (2026-09-25) and the amended rulings on them: a name with an
        # empty value is a setting that holds nothing, so the net for named values still masks NAME=value printed at
        # run time, while a would-be name that is not a name is a bare token (R2'); a name found inside a value is
        # never a mask's name, nor a setting unless given with '=' to a setting's name (R1', R5'); YAML data holding {{ is read as
        # YAML (R8'); the parts of a value (R13); and a value as each standard reader of its format reads it (R14).
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the R2'/R13/R14 cases whose .env fixtures are outside the
        # literal grammar are refusal cases below; the padded-token line the grammar reads as an ordinary assignment
        # is below too.
        slash, quote, apostrophe = chr(92), chr(34), chr(39)
        glued, padded = "cjMtcjE4LWdsdWVkLXNpbmdsZS1wYWQteHg=", "cjMtcjE4LWVudi1wYWRkZWQtbmFtZS14eA=="
        ini_token, prop_token = "cjMtcjE4LWluaS1wYWRkZWQtY29tbWVudA==", "cjMtcjE4LXByb3AtcGFkZGVkLXRva2VueA=="
        fetched = "fetched = open('runtime/fetched.txt').read().strip(); "   # a value no secret file holds
        cases = {   # name: ({file: text or bytes}, what the check prints, the values and pieces that must not be seen,
            #                the mask that must be seen (None: any), and any text that must stay readable)
            "R2' an empty setting in .env.example leaves the net for named values on": (
                {".env.example": "API_KEY=\nDEBUG=false\n", "runtime/fetched.txt": "r3-r18-fetched-1101\n"},
                fetched + "print('API_KEY=' + fetched)", ("r3-r18-fetched-1101",), "API_KEY=<masked>"),
            "R2' an INI option with nothing after it leaves the net for named values on": (
                {"credentials.ini": "[api]\napi_key =\n", "runtime/fetched.txt": "r3-r18-fetched-1104\n"},
                fetched + "print('api_key = ' + fetched)", ("r3-r18-fetched-1104",), "api_key = <masked>"),
            "R2' a list of field names leaves the net for named values on": (
                {".env": "LOG_REDACT_FIELDS=password,secret,token\n", "runtime/fetched.txt": "r3-r18-fetched-1105\n"},
                fetched + "print('token=' + fetched)", ("r3-r18-fetched-1105",), "=<masked>"),
            "R2' a padded token and a comment in an INI file with no extension": (
                {"credentials": "[default]\n" + ini_token + " ; rotated\n"},
                "for line in open('credentials'):\n    print(line.strip())\n    print(line.split()[0])",
                (ini_token.rstrip("="),), "<masked credentials>"),
            "R2' a padded token in a .properties file": (
                {"secrets.properties": "db.user=admin\n" + prop_token + "\n"},
                "print(open('secrets.properties').read().splitlines()[1])", (prop_token.rstrip("="),),
                "<masked secrets.properties>"),
            "R2' a .properties line with no separator": (
                {"secrets.properties": "db.user=admin\nr3-r18-keyonly-1301\n"},
                "print(open('secrets.properties').read().splitlines()[1])", ("r3-r18-keyonly-1301",),
                "<masked secrets.properties>"),
            "R1' the part of a password after a colon is never left readable": (
                {".env": "DB_PASSWORD=r3Horse:1984\n"}, "print('year', open('.env').read().strip().split(':')[1])",
                ("1984", "r3Horse"), "<masked DB_PASSWORD>"),
            "R1' the part of a token before a colon is never a mask's name": (
                {".env": "API_TOKEN=r3keyid4471:r3keysecret9902\n"},
                "print('secret half', open('.env').read().strip().split(':')[1])",
                ("r3keyid4471", "r3keysecret9902"), "<masked API_TOKEN>"),
            "R1' the part of a JSON password before its = is never a mask's name": (
                {"credentials.json": '{"password": "r3Head7788=r3tail-7789"}'},
                "import json; print('tail', json.load(open('credentials.json'))['password'].split('=')[1])",
                ("r3Head7788", "r3tail-7789"), "<masked password>"),
            "R5' the summary of settings never shows a name found inside a password": (
                {".env": "DB_PASSWORD=r3Horse:1984\n"},
                "print('password', open('.env').read().split('=', 1)[1].strip())",
                ("r3Horse", "1984"), "<masked DB_PASSWORD>"),
            "R5' a short value mixing letters and digits inside a key is never a mask's name": (
                {".env": "PIN=Q7X\n", "secrets.yaml": "backupQ7Xkey: r3-r18-glued-pin-1401\n"},
                "print('value', open('secrets.yaml').read().split(': ')[1].strip())", ("Q7X", "r3-r18-glued-pin-1401"),
                "<masked secrets.yaml>"),
            "R8' YAML data with {{ in a comment is read as YAML": (
                {"secrets.yaml": "# rendered from {{ .Values }}\n"
                                 'passwords: ["r3-r18-tplc-1501", "r3-r18-tplc-1502"]\n'},
                "import json; print(*json.loads(open('secrets.yaml').read().splitlines()[1].split(':', 1)[1]))",
                ("r3-r18-tplc-1501", "r3-r18-tplc-1502"), "<masked passwords>"),
            "R8' an Ansible value holding {{ }} beside a value with a YAML escape": (
                {"secrets.yml": 'vault_password: "r3-r18-ans-' + slash + 'x41-1601"\n'
                                'db_password: "{{ vault_password }}"\n'},
                "print(open('secrets.yml').read().split(chr(34))[1].replace(chr(92) + 'x41', 'A'))",
                ("r3-r18-ans-A-1601",), "<masked secrets.yml>"),
            "R13 a URL's password": (
                {"backend.env": "REDIS_URL=redis://:r3-r18-redis-1701@cache:6379/0\n"},
                "from urllib.parse import urlsplit; "
                "print('password', urlsplit(open('backend.env').read().split('=', 1)[1].strip()).password)",
                ("r3-r18-redis-1701",), None),
            "R13 each member of a YAML value": (
                {"secrets.yaml": "api_keys: r3-r18-yc-1901,r3-r18-yc-1902\n"},
                "print(*open('secrets.yaml').read().split(': ', 1)[1].strip().split(','))",
                ("r3-r18-yc-1901", "r3-r18-yc-1902"), "<masked api_keys>"),
            "R13 a word of a JSON value": (
                {"credentials.json": '{"auth_header": "Bearer r3-r18-bearer-2001"}'},
                "import json; print(json.load(open('credentials.json'))['auth_header'].split()[1])",
                ("r3-r18-bearer-2001",), "<masked auth_header>"),
            "R13 a quoted .properties value printed without its quotes": (
                {"secrets.properties": 'db.password="r3-r18-pq-2101"\n'},
                "print(open('secrets.properties').read().split('=', 1)[1].strip().strip(chr(34)))",
                ("r3-r18-pq-2101",), "<masked db.password>"),
            "R13 the first word of an INI value": (
                {"credentials.ini": "[db]\npassword = r3-r18-iw-2201 r3-r18-iw-2202\n"},
                "import configparser; c = configparser.ConfigParser(); c.read('credentials.ini'); "
                "print(c['db']['password'].split()[0])", ("r3-r18-iw-2201",), "<masked password>"),
            # "R14 a single-quoted .env value as Node ends it" stops the run since round 9: /bin/sh never finds its
            # last quote closed (test_a_quote_the_shell_never_finds_closed_stops_the_run, test_evidence_readings.py)
            "R14 an INI value as configparser fills in its references": (
                {"credentials.ini": "[DEFAULT]\nport = 8443\nyear = 2031\n[api]\npin = %(port)s%(year)s\n"},
                "import configparser; c = configparser.ConfigParser(); c.read('credentials.ini'); "
                "print('pin', c['api']['pin'])", ("84432031",), "<masked pin>"),
            "R14 a .properties value as Java reads it from ISO-8859-1": (
                {"secret.properties": ("password=r3-r18-caf" + chr(0xe9) + "-2901\n").encode("utf-8")},
                "print(open('secret.properties', 'rb').read().decode('latin-1').split('=', 1)[1].strip())",
                ("r3-r18-caf" + chr(0xc3) + chr(0xa9) + "-2901",), "<masked password>"),
            "R14 a YAML base-60 number as PyYAML reads it": (
                {"secrets.yaml": "pin: 190:20:30.15\n"}, "print('pin', 190 * 3600 + 20 * 60 + 30.15)", ("685230.15",),
                "<masked pin>"),
            "R14 a YAML date and time as PyYAML reads it": (
                {"secrets.yaml": "password: 2001-12-14t21:59:43.10-05:00\n"},
                "import datetime; zone = datetime.timezone(datetime.timedelta(hours=-5)); "
                "print(datetime.datetime(2001, 12, 14, 21, 59, 43, 100000, zone))", ("21:59:43.100000",),
                "<masked password>"),
            "R14 a TOML date and time as tomllib reads it": (
                {"secrets.toml": "password = 1979-05-27T07:32:00.999999999-07:00\n"},
                "import datetime; zone = datetime.timezone(datetime.timedelta(hours=-7)); "
                "print(datetime.datetime(1979, 5, 27, 7, 32, 0, 999999, zone))", ("07:32:00.999999",),
                "<masked password>"),
        }
        for name, (files, reader, secrets, mask, *kept) in cases.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                for file, content in files.items():
                    (project / file).parent.mkdir(parents=True, exist_ok=True)
                    (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
                (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                                  + reader + "\n")
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
                self.assertEqual(code, 0, report)
                self.assertTrue((project / "check-ran").exists())
                shown, saved = printed.split("\n\n", 1)[1], out.read_text(encoding="utf-8")
                for secret in secrets:
                    self.assertNotIn(secret, shown)
                    self.assertNotIn(secret, report)                # the summary of settings too
                    self.assertNotIn(secret, saved)
                self.assertIn(mask or "<masked", shown)          # the value's mask, named by a name that holds none
                self.assertIn(mask or "<masked", saved)
                for text in kept:
                    self.assertIn(text, shown)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each of these .env cases expected the run with its value
        # masked as one standard reader reads it (R13, R14) or with the net for named values left on (R2'); every
        # fixture is outside the literal grammar, so the run now refuses before launch — "R2' a password written as
        # #..." and "R2' a token with one = and a comment glued on": an unquoted '#' (readers disagree on cut vs
        # keep); "R13 a percent-encoded query value": '&' is outside the probed unquoted set; both R14 escape cases:
        # a backslash in a double-quoted value (bash keeps it, dotenv decodes it — readers disagree on every
        # escape); "R14 ... a shell continues on the next line" and "... joins from quoted parts": a backslash or
        # quote inside an unquoted value; "R14 ... a shell's C quotes": a '$' in a value (interpolation).
        refused = {   # name: ({file: text}, the values and pieces that must not be seen, the file the report names)
            "R2' a password written as #... in .env leaves the net for named values on": (
                {".env": "DB_PASSWORD=#r3-r18-hash-1102\n", "runtime/fetched.txt": "r3-r18-fetched-1103\n"},
                ("r3-r18-hash-1102", "r3-r18-fetched-1103"), ".env"),
            "R2' a token with one = and a comment glued on, printed as python-dotenv reads its value": (
                {".env": glued + "#r3-r18-note-1201\n"}, ("r3-r18-note-1201", glued.rstrip("=")), ".env"),
            "R13 a percent-encoded query value": (
                {".env": "DATABASE_URL=postgres://db/app?user=app&password=r3%21r18%21pct-1801\n"},
                ("r3!r18!pct-1801", "r3%21r18%21pct-1801"), ".env"),
            "R14 a .env value as python-dotenv reads it (only its own escapes)": (
                {".env": "DB_PASSWORD=" + quote + "r3-r18-mix-" + slash + "t" + slash + "101-2301" + quote + "\n"},
                ("r3-r18-mix", "101-2301"), ".env"),
            "R14 a .env value as Node reads it (a line break for each backslash-n)": (
                {".env": "DB_PASSWORD=" + quote + "r3-r18-left-2401" + slash * 2 + "nr3-r18-right-2402" + quote + "\n"},
                ("r3-r18-left-2401", "r3-r18-right-2402"), ".env"),
            "R14 a .env value a shell continues on the next line": (
                {".env": "API_TOKEN=r3-r18-cont" + slash + "\ninued-2601\n"}, ("r3-r18-cont", "inued-2601"), ".env"),
            "R14 a .env value in a shell's C quotes": (
                {".env": "API_TOKEN=$" + apostrophe + "r3-r18-" + slash + "x41nsi-2701" + apostrophe + "\n"},
                ("r3-r18-", "nsi-2701"), ".env"),
            "R14 a .env value a shell joins from quoted parts": (
                {".env": "SECRET=r3" + apostrophe + "z!" + apostrophe + "q7\n"}, ("r3z!q7", "r3z!"), ".env"),
        }
        for name, (files, secrets, blamed) in refused.items():
            self.refused_run(name, files, secrets, blamed)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "R2' a padded token printed as the name a .env reader sees"
        # expected the token masked even as the would-be name a reader sees; the grammar reads the line as an
        # ordinary assignment (a NAME over A-Za-z0-9, '=', a value of '=' signs — every claimed reader agrees), and
        # a name is never a secret — masks are named by them — so the name prints readably beside PORT.
        _, shown, _, _ = self.admitted_run(
            "R2' a padded token printed as the name a .env reader sees",
            {".env": padded + "\nPORT=8000\n"},
            "for line in open('.env'):\n    print('setting', line.strip().split('=', 1)[0])")
        self.assertIn("setting " + padded.rstrip("="), shown)   # a name is never a secret: the mask names it
        self.assertIn("setting PORT", shown)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): this block's .env.example held "API_KEY= # set me" and
        # expected the run with the --env value kept out of the header; whitespace and '#' after '=' are outside the
        # grammar (readers disagree on cut vs keep), so the run now refuses before launch — an --env flag does not
        # bypass the boundary. The header rule itself still stands, proven by
        # test_a_name_the_env_flag_gives_the_check_never_stops_the_run and the pinned-value block in
        # test_masking_one_value_never_hides_another_and_each_reading_the_checkers_found_is_masked.
        self.refused_run("empty-setting-and-an-env-flag",
                         {".env": "APP=demo\n", ".env.example": "API_KEY= # set me\n"},
                         ("r3-r18-flag-3001",), ".env.example", env=["API_KEY=r3-r18-flag-3001"])

    def test_masking_one_value_never_hides_another_and_each_reading_the_checkers_found_is_masked(self):
        # the second round of lens checks (2026-09-25) and the leader's repair: every match is found in the output as
        # printed before any is replaced, so a masked name, word or member never hides NAME=value from the net for
        # named values; a name found inside a value is never a mask's name; a list's numbers are never settings; and
        # the readings they found — YAML aliases, configparser's [DEFAULT] in each section, Java reading a
        # JSON-shaped file, a URL's password holding '@', a query value holding ';'
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the .env readings this round found — shell parameters,
        # python-dotenv's spaces and quoted names, Node's carriage returns, a base32 token as a bare line — rested
        # on files outside the literal grammar; they are refusal cases below, except the two the grammar reads as
        # ordinary assignments (the padded base32 line, the number after a token), also below.
        slash, fetched = chr(92), "v = open('runtime/fetched.txt').read().strip(); "   # a value no secret file holds
        shell = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', 'set -a; . ./.env; printf %s "
                 + '"$DB_PASSWORD"' + "'], stdout=subprocess.PIPE).stdout.decode())")
        cases = {   # name: ({file: text or bytes}, what the check prints, the values and pieces that must not be seen)
            "a word of a field list inside a setting's name": (
                {".env": "RESULT_CODES=FAIL,PASS,SKIP\n", "runtime/fetched.txt": "r3-l4-fetched-0101\n"},
                fetched + "print('DB_PASSWORD=' + v)", ("r3-l4-fetched-0101",)),
            "a field list naming the setting printed": (
                {".env": "SENSITIVE_FIELDS=password,OAUTH2_TOKEN,apikey\n", "runtime/fetched.txt": "r3-l4-f-0102\n"},
                fetched + "print('OAUTH2_TOKEN=' + v); print('apikey: ' + v)", ("r3-l4-f-0102",)),
            "a member that starts the value printed": (
                {".env": "ALLOWED_SCHEMES=ftp,https\n", "runtime/fetched.txt": "r3-l4-hook-0103\n"},
                fetched + "print('SLACK_WEBHOOK_SECRET=https://hooks.test/services/' + v)", ("r3-l4-hook-0103",)),
            "a setting's name kept in a comment": (
                {".env.example": "# Required: OAUTH2_CLIENT_SECRET\nAPP=demo\n", "runtime/fetched.txt": "r3-l4-c-0104\n"},
                fetched + "print('OAUTH2_CLIENT_SECRET=' + v)", ("r3-l4-c-0104",)),
            "a password that reads like a setting's name": (
                {".env": "POSTGRES_PASSWORD=postgres_password\nREDIS_PASSWORD=secret\n"},
                "values = dict(line.split('=', 1) for line in open('.env').read().split()); "
                "print('postgresql://app:' + values['POSTGRES_PASSWORD'] + '@db/app'); "
                "print('redis://:' + values['REDIS_PASSWORD'] + '@cache:6379/0')", ("postgres_password", ":secret@")),
            "a password whose head reads like a name": (
                {".env": "DB_PASSWORD=monkey:Banana77\n", "secrets.toml": 'api_token = "pinwheelKey=Orbit6620"\n'},
                "print('tail', open('.env').read().strip().split(':')[1]); "
                "print('tail', open('secrets.toml').read().split('=')[2].strip().strip(chr(34)))",
                ("Banana77", "monkey", "Orbit6620", "pinwheelKey")),
            "numbers in a list under a plain name": (
                {"secrets.yaml": "recovery_codes:\n  - 48213377\n  - 90517264\npins: [4821, 9934]\n"},
                "print('codes', *open('secrets.yaml').read().split()[2:5:2]); print('pins 4821 9934')",
                ("48213377", "90517264", "4821", "9934")),
            "a URL's password holding @, and a query value holding ;": (
                {".env": "DATABASE_URL=postgres://app:r3-l4-at@tail-0105x@db:5432/app\n",
                 "secrets.yaml": 'dsn: "postgres://db/app?password=r3;l4-semi-0106&sslmode=require"\n'},
                "from urllib.parse import urlsplit, parse_qs; "
                "print('pw', urlsplit(open('.env').read().split('=', 1)[1].strip()).password); "
                "url = open('secrets.yaml').read().split(chr(34))[1]; "
                "print('pw', parse_qs(urlsplit(url).query)['password'][0])", ("r3-l4-at", "tail-0105x", "l4-semi-0106")),
            "a YAML alias under a secret name": (
                {"secrets.yaml": "defaults: &d 4821\npin: *d\ncodes: &c [4822, 4823]\nrecovery_keys: *c\n"},
                "print('pin', open('secrets.yaml').read().split()[2]); print([4822, 4823])", ("4821", "4822", "4823")),
            "configparser: a [DEFAULT] reference filled in each section": (
                {"credentials": "[DEFAULT]\npin = %(branch)s%(suffix)s\n[bank]\nbranch = 48\nsuffix = 21\n"},
                "import configparser; c = configparser.ConfigParser(); c.read('credentials'); print(c['bank']['pin'])",
                ("4821",)),
            "Java: a .properties file that is one JSON document": (
                {"credentials.properties": '{"password": "r3-l4-j' + slash + 'b-0112"}\n'},
                "print(open('credentials.properties').read().split(': ', 1)[1].replace(chr(92), '').strip())",
                ("r3-l4-jb-0112",)),
            "a short value inside another file's key": (
                {".env": "PIN=QXZ\n", "secrets.yaml": "backupQXZkey: r3-l4-short-0115\n"},
                "print('value', open('secrets.yaml').read().split(': ')[1].strip())", ("QXZ", "r3-l4-short-0115")),
            "a number under a key inside a table, mapping or section named secret": (
                {"secrets.toml": "[pin]\nvalue = 0x12D5\n", "credentials.json": '{"pin": {"code": 4822}}',
                 "secrets.yaml": "credentials:\n  code: 4823\n", "credentials.ini": "[pin]\ncode = 4824\n"},
                "print(4821, 4822, 4823, 4824)", ("4821", "4822", "4823", "4824")),
            "a Helm template's quoted value with a YAML escape": (
                {"chart/templates/secret.yaml": "stringData:\n  password: {{ .Values.password | quote }}\n"
                                                "{{- if .Values.extra }}\n  apikey: " + '"r3-l4-helm-' + slash
                                                + "x43" + slash + "x31" + slash + 'x36-0119"\n{{- end }}\n'},
                "print('key', 'r3-l4-helm-C16-0119')", ("r3-l4-helm-C16-0119", "C16-0119", "helm-C16")),
            "a file with no extension that starts like INI but is not, read as text": (
                {"credentials": "[default]\nnot an option line\n482195\n"},
                "print(open('credentials').read().splitlines()[2])", ("482195",)),
            # the final lens checks (2026-09-25, night): a masked value is the edge of a word, as its mask was
            "an all-digit password glued to a token": (
                {".env": "SF_PASSWORD=48213377\nSF_SECURITY_TOKEN=Zq8vLmN3pRtWx9Yk\n"},
                "print('login as app with 48213377Zq8vLmN3pRtWx9Yk')", ("48213377", "Zq8vLmN3pRtWx9Yk")),
            "a token shape glued to a value": (
                {".env": "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCYzz99\n"},
                "print('AKIAIOSFODNN7EXAMPLE' + 'wJalrXUtnFEMIK7MDENGbPxRfiCYzz99')", ("AKIAIOSFODNN7EXAMPLE",)),
            "a token used as a key, and a key holding a control character": (
                {"credentials.json": '{"ghp_ZyXwVuTsRqPoNmLkJiHgFeDc98": "deploy-bot-r3l4", "a' + slash + 'u0000b": 8123}'},
                "print('ghp_ZyXwVuTsRqPoNmLkJiHgFeDc98 -> deploy-bot-r3l4'); print('port 8123')",
                ("ghp_ZyXwVuTsRqPoNmLkJiHgFeDc98", "deploy-bot-r3l4")),
            "a YAML flow mapping under a name that says secret": (
                {"secrets.yaml": "pin: {value: 9272}\nsecret: {code: 9170}\ncredentials: [{port: 5434}]\n"},
                "print(9272, 9170, 5434)", ("9272", "9170", "5434")),
            "a [DEFAULT] option read in a section named secret": (
                {"credentials.ini": "[DEFAULT]\nbase = 9215\n[secret]\nhost = db\n"},
                "import configparser; c = configparser.ConfigParser(); c.read('credentials.ini'); print(c['secret']['base'])",
                ("9215",)),
            "a URL whose user is a token beside a password": (
                {".env": "REPO_URL=https://g9Tok9234Abc:x-oauth-basic@github.com/org/repo.git\n"},
                "from urllib.parse import urlsplit; print(urlsplit(open('.env').read().split('=', 1)[1]).username)",
                ("g9Tok9234Abc",)),
        }
        for name, (files, reader, secrets) in cases.items():
            if "/bin/sh" in reader and not os.path.exists("/bin/sh"):
                continue                                      # a shell's reading needs a POSIX shell (not Windows)
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                for file, content in files.items():
                    (project / file).parent.mkdir(parents=True, exist_ok=True)
                    (project / file).write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
                (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                                  + reader + "\n")
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
                self.assertEqual(code, 0, report)   # the constructed environment holds HOME whatever the parent's
                self.assertTrue((project / "check-ran").exists())
                self.assertTrue(printed.startswith("$ "))            # a lone $ is never masked, the header's included
                self.assertNotIn(chr(0), printed + report)            # no reader's mark ever reaches a mask's name
                shown, saved = printed.split("\n\n", 1)[1], out.read_text(encoding="utf-8")
                for secret in secrets:
                    self.assertNotIn(secret, shown)
                    self.assertNotIn(secret, report)                # the summary of settings too
                    self.assertNotIn(secret, saved)
                self.assertIn("<masked", shown)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each of these .env cases expected the run with the reading
        # the named checker finds masked; every fixture is outside the literal grammar, so the run now refuses
        # before launch — the two ${NAME:-word}/${NAME:+word} cases, "a shell trimming a prefix", "a shell's nested
        # reference" and "a shell's := giving a later line its value, arithmetic, and a tilde over the file's HOME":
        # a '$' or '{', '}' in a value (interpolation, brace expansion — Codex's reproduced bash case), arithmetic
        # expansion, a '~' at a value's start (bash expands it through the account database); "python-dotenv: a
        # no-break space before a quote": a non-ASCII byte and a backslash (the unquoted set is the probed ASCII
        # set); "python-dotenv: a quoted name holding =" and "names python-dotenv takes that are not written as
        # names": a NAME is [A-Za-z_][A-Za-z0-9_]*, a shell's name; both carriage-return cases: the boundary is
        # LF-only (bash keeps a '\r' in the value); "a bare number line in .env": a bare line is never an
        # assignment; "a URL whose user is a token, and a token in a URL's fragment" and "a query parameter whose
        # name is percent-encoded": '#' and '&' are outside the probed unquoted set; "a name that says secret right
        # after a value ending in a letter outside ASCII": a non-ASCII byte in an unquoted value.
        refused = {   # name: ({file: text or bytes}, what the check would print, the values and pieces that must
            #               not be seen, the file the report names) — the check must never run
            "a shell's ${NAME:=word}, the default it assigns": (
                {".env": "R3_L4_UNSET=\nDB_PASSWORD=${R3_L4_UNSET:=r3-l4-assign-0108}\n"}, shell,
                ("r3-l4-assign-0108",), ".env"),
            "a shell's ${NAME:+word}, the alternate it gives": (
                {".env": "R3_L4_SET=x1\nDB_PASSWORD=${R3_L4_SET:+r3-l4-alt-0109}\n"}, shell, ("r3-l4-alt-0109",),
                ".env"),
            "python-dotenv: a no-break space before a quote": (
                {".env": "DB_PASSWORD=" + chr(0xa0) + '"r3-l4-nb' + slash + 'tsp-0110"\n'},
                "print(open('.env').read())", ("r3-l4-nb", "sp-0110"), ".env"),
            "python-dotenv: a quoted name holding =": (
                {".env": "'DB_PASSWORD=old'=r3-l4-qk-0111\n"}, "print(open('.env').read())", ("r3-l4-qk-0111",),
                ".env"),
            "Node: a carriage return inside a quoted PIN": (
                {".env": b'PIN="48\r21"\n'}, "print(open('.env', 'rb').read())", ("4821",), ".env"),
            "a bare number line in .env": (
                {".env": "482193\nAPI_KEY=r3-l4-bare-0114\n"}, "print(open('.env').read())",
                ("482193", "r3-l4-bare-0114"), ".env"),
            "a URL whose user is a token, and a token in a URL's fragment": (
                {".env": "GIT_URL=https://r3l4tok0116x@git.example.test/repo\n"
                         "CALLBACK=https://app.test/cb#access_token=r3%2Fl4-frag-0117&state=x\n"},
                "print(open('.env').read())",
                ("r3l4tok0116x", "r3/l4-frag-0117", "r3%2Fl4-frag-0117", "l4-frag-0117"), ".env"),
            "a shell trimming a prefix from a value": (
                {".env": "WHOLE=pre-r3-l4-trim-0118\nDB_PASSWORD=${WHOLE#pre-}\n"}, shell, ("r3-l4-trim-0118",),
                ".env"),
            "a name that says secret right after a value ending in a letter outside ASCII": (
                {".env": "USER_NAME=Gr" + chr(252) + "sse77\n"}, "print(open('.env').read())",
                ("r3l4B01aa1", "Gr" + chr(252) + "sse77"), ".env"),
            "a shell's nested reference, a pattern from another value, and a POSIX class": (
                {".env": "UNSET_X=\nDB_BASE=g9HorseBattery9137Staple\nTOKEN_PREFIX=g9pre\n"
                         "API_TOKEN=g9preOrchid9141Lamp\n"
                         "DB_SECRET=Cobalt-Lynx9146\nDB_PASSWORD=${UNSET_X:-${DB_BASE#g9}}\n"
                         "API_KEY=${API_TOKEN#$TOKEN_PREFIX}\nDB_PIN=${DB_SECRET%%[![:alpha:]]*}\n"},
                "print(open('.env').read())", ("HorseBattery9137Staple", "Orchid9141Lamp", "Cobalt"), ".env"),
            "a shell's := giving a later line its value, arithmetic, and a tilde over the file's HOME": (
                {".env": "UNSET_SEED=\nSEED=${UNSET_SEED:=Kq4}\nDB_PASSWORD=${UNSET_SEED}Zr8\n"
                         "API_TOKEN=g9Horse9144:tail\nPIN=$((9000+147))\nHOME=/r3-l4-home\nTILDE_PIN=~/tail9137\n"},
                "print(open('.env').read())", ("Kq4Zr8", "g9Horse9144", "9147", "tail9137"), ".env"),
            "names python-dotenv takes that are not written as names": (
                {".env": "DB_PASSWORD[0]=g9Zeb9150Qa\nAPI_KEY!=g9Bg9265Qw\nDB_PASSWORD+=g9Pl9266Zx\n"},
                "print(open('.env').read())", ("g9Zeb9150Qa", "g9Bg9265Qw", "g9Pl9266Zx"), ".env"),
            "Node deleting a lone carriage return inside an unquoted PIN": (
                {".env": b"PIN=48\r21\n"}, "print(open('.env', 'rb').read())", ("4821",), ".env"),
            "a query parameter whose name is percent-encoded": (
                {".env": "CALLBACK=https://app.test/cb?p%69n=4821&x=1\n"}, "print(open('.env').read())", ("4821",),
                ".env"),
        }
        for name, (files, reader, secrets, blamed) in refused.items():
            self.refused_run(name, files, secrets, blamed, reader=reader)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "a base32 token with its padding" expected the whole bare
        # line masked, token included; the grammar reads the line as an ordinary assignment every claimed reader
        # decodes alike (NAME=JBSWY3DPINXHE2LOMFXGG5DPKE, a value of '=' padding), so the name stays readable and
        # the padding alone is masked.
        _, shown, saved, _ = self.admitted_run("a base32 token with its padding",
                                               {".env": "APP=demo\nJBSWY3DPINXHE2LOMFXGG5DPKE======\n"},
                                               "print(open('.env').read().split()[1])")
        self.assertEqual(shown, "JBSWY3DPINXHE2LOMFXGG5DPKE=<masked>\n")   # the name is never a secret
        self.assertIn("JBSWY3DPINXHE2LOMFXGG5DPKE=<masked>", saved)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "a number after a token on a .env line" expected the number
        # masked as part of a token reading; the grammar reads the line as an ordinary assignment (NAME over
        # A-Za-z0-9, '=', value 4841), and a number under a name holding no secret word is a setting left readable
        # — the same rule test_a_number_or_a_yes_no_word_under_an_ordinary_name_stays_readable_and_is_named proves.
        _, shown, _, report = self.admitted_run("a number after a token on a .env line",
                                                {".env": "cjMtZW52LXRva2VuLXAzMw=4841\n"}, "print('code 4841')")
        self.assertIn("code 4841", shown)
        self.assertIn("settings left readable: cjMtZW52LXRva2VuLXAzMw", report)
        project = self.tmp / "a-pin-glued-to-a-token-in-the-env-header"   # D4 rule 4: the header records the
        (project / ".vibe-to-engineering").mkdir(parents=True)            # --env name only, so a declared value
        (project / ".env").write_text("API_TOKEN=Zq8vLmN3pRtW\nPIN=4821\n")   # never reaches it, glued or not
        self.project = project
        code, printed, report = self.run_tool(project / ".vibe-to-engineering" / "evidence" / "check.txt",
                                              sys.executable, "-c", "print('ok')", env=["MIX=Zq8vLmN3pRtW4821"])
        self.assertEqual(code, 0, report)
        self.assertIn("  with MIX\n", printed)
        for text in (printed, report, (project / ".vibe-to-engineering" / "evidence" / "check.txt").read_text(
                encoding="utf-8")):
            self.assertNotIn("Zq8vLmN3pRtW4821", text)
        project = self.tmp / "a-yaml-key-outside-the-subset-beside-a-template"   # no {{ on the line it stops at
        (project / ".vibe-to-engineering").mkdir(parents=True)
        (project / "secrets.yml").write_text("? complex_key\n: v\nvault_pw: " + '"r3-l4-av-' + slash + 'x41-0113"\n'
                                             'db_pw: "{{ vault_pw }}"\n')
        (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                          "print('r3-l4-av-A-0113')\n")
        self.project = project
        out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
        code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
        self.assertEqual(code, 2, report)                    # refused, as without the template: never read as text
        self.assertFalse((project / "check-ran").exists())
        self.assertFalse(out.exists())
        self.assertIn("secrets.yml", report)

    def test_a_padded_token_a_fragment_parameter_and_a_json_list_in_env_each_stay_masked(self):
        # three protections the round-4 mutation run found no test for (the independent re-review, 2026-09-25): two
        # '=' of padding make a bare .env line a token even when its would-be name holds a secret word (KEYA====); a URL
        # fragment's parameters are read, split at ';' too, under the name each is given (#%70in=4821); and a .env file
        # that is one JSON document is read as JSON as well. Each value leaks when its protection is taken out.
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the first and third protections rested on reader modeling —
        # KEYA==== is an ordinary assignment under the grammar (below), and a .env file holding one JSON document is
        # not a literal assignment, so it refuses (below). The second protection stands, unchanged, in the case above.
        cases = {   # name: ({file: text}, what the check prints, the value and its pieces, the one mask it shows)
            "a PIN among a URL fragment's parameters split at ';'": (
                {"credentials.json": json.dumps({"url": "#%70in=4821;other=x"})},
                "import json; from urllib.parse import unquote; frag = json.load(open('credentials.json'))['url'][1:]; "
                "print(dict((unquote(k), v) for k, v in (p.split('=', 1) for p in frag.split(';')))['pin'])",
                ("4821",), "<masked secret in url>"),
        }
        for name, (files, reader, secrets, label) in cases.items():
            with self.subTest(name):
                project = self.tmp / re.sub(r"\W+", "-", name)
                (project / ".vibe-to-engineering").mkdir(parents=True)
                for file, content in files.items():
                    (project / file).write_text(content)
                (project / "check.py").write_text("from pathlib import Path\nPath('check-ran').write_text('ran')\n"
                                                  + reader + "\n")
                self.project = project
                out = project / ".vibe-to-engineering" / "evidence" / "check.txt"
                code, printed, report = self.run_tool(out, sys.executable, "-B", "check.py")
                self.assertEqual(code, 0, report)
                self.assertTrue((project / "check-ran").exists())
                shown, saved = printed.split("\n\n", 1)[1], out.read_text(encoding="utf-8")
                self.assertEqual(re.sub(r"<masked(?: [^>\n]*)?>|\s+", "", shown), "")   # not a piece of it is left
                self.assertEqual(set(re.findall(r"<masked[^>]*>", shown)), {label})  # and no mask shows secret text
                for secret in secrets:
                    for text in (shown, saved, report):
                        self.assertNotIn(secret, text)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "a base32 token whose would-be name holds a secret word"
        # expected the whole KEYA==== line masked as a bare token, its name hidden too; the grammar reads the line
        # as an ordinary assignment every claimed reader decodes alike (NAME=KEYA, a value of '=' padding), and a
        # name is never a secret — the mask is named by it — so KEYA stays readable and only the padding is masked.
        _, shown, saved, _ = self.admitted_run("a base32 token whose would-be name holds a secret word",
                                               {".env": "KEYA====\n"}, "print(open('.env').read().strip())")
        self.assertEqual(shown, "KEYA=<masked>\n")       # not a piece of the value is left
        self.assertEqual(set(re.findall(r"<masked[^>]*>", saved)), {"<masked>"})
        # SUPERSEDED (A1 literal boundary, 2026-09-27): "a JSON list with an escape, in a .env file" expected the
        # file read as JSON as well as .env, masked both ways; the grammar admits only literal assignments, and a
        # JSON document is not one (no NAME=VALUE line), so the file now refuses before launch.
        self.refused_run("a JSON list with an escape, in a .env file", {".env": '["r4-json-\\u0056alue-59274"]\n'},
                         ("r4-json-Value-59274", "Value-59274", "r4-json-" + chr(92) + "u0056alue-59274"), ".env",
                         reader="import json; print(json.load(open('.env'))[0])")

    def test_a_number_or_a_yes_no_word_under_an_ordinary_name_stays_readable_and_is_named(self):
        (self.project / ".env").write_text("PORT=8000\nDEBUG=true\nSECRET_KEY=abcd1234efgh5678\nPIN=1234\n")
        code, printed, report = self.run_tool(self.folder / "check.txt", sys.executable, "-c",
                                              "print('listening on 8000, debug true, 12 passed')")
        self.assertEqual(code, 0, report)
        self.assertIn("listening on 8000, debug true, 12 passed", printed)   # settings, not secrets
        self.assertIn("settings left readable: DEBUG, PORT", report)
        self.assertNotIn("PIN", report.split("settings left readable")[1])   # a PIN is masked, whatever its shape
        code, printed, _ = self.run_tool(self.folder / "pin.txt", sys.executable, "-c", "print('pin 1234 ok, 12345')")
        self.assertIn("pin <masked PIN> ok, 12345", printed)                 # a short value: whole words only

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "needs POSIX file permissions and a normal user")
    def test_a_folder_that_cannot_be_listed_or_is_a_link_stops_the_run_before_the_check(self):
        (self.project / "config").mkdir()
        (self.project / "config" / ".env").write_text("SECRET_KEY=fixture-ordinary-value-73921\n")
        os.chmod(self.project / "config", 0o111)                 # can be entered, cannot be listed
        try:
            code, printed, report = self.run_tool(self.folder / "x.txt", sys.executable, "-c",
                                                  "print(open('config/.env').read())")
        finally:
            os.chmod(self.project / "config", 0o755)
        self.assertEqual(code, 2, report)
        self.assertNotIn("fixture-ordinary-value-73921", printed + report)
        self.assertIn("cannot list the folder", report)
        os.chmod(self.project / "config", 0o755)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        os.symlink(str(elsewhere), str(self.project / "shared"))
        code, printed, report = self.run_tool(self.folder / "y.txt", sys.executable, "-c", "print('ran')")
        self.assertEqual(code, 2, report)
        self.assertNotIn("ran", printed)
        self.assertIn("is a link to a folder", report)

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
