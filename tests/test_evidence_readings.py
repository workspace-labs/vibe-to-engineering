"""Tests for the readings behind scripts/evidence.py: a secret file's value is masked whole as each program that reads
its format reads it — PyYAML through the document's %TAG handles, a POSIX shell sourcing a .env file — or, when only
that program can make the reading out, the file stops the run before the check. (tests/test_evidence.py holds the
rest of evidence.py's tests; this file keeps it under the 1,000-line limit.)

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import base64
import codecs
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


class Readings(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="v2e-readings-")).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check_prints(self, name, files, reader, env=None, flags=()):
        """A project holding `files` (text, or bytes as written) whose check marks that it ran, then prints what
        `reader` prints: (the tool's exit code, what it showed after the header, the evidence file's text or None, its
        report, whether the check ran). `env`: added to the environment the tool runs in, which the check inherits —
        a name given None is taken out of it. `flags`: the tool's own options (--env NAME=VALUE)."""
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

    def assert_masked_whole(self, name, files, reader, secrets, label, env=None):
        """The check ran and printed only the value: nothing of it is left once each mask is taken out — not the
        value, nor a piece of it — and every mask carries `label`, never secret text."""
        code, shown, saved, report, ran = self.check_prints(name, files, reader, env)
        self.assertEqual(code, 0, report)
        self.assertTrue(ran)
        self.assertEqual(re.sub(r"<masked(?: [^>\n]*)?>|\s+", "", shown), "", "a piece of the value is left")
        self.assertEqual(set(re.findall(r"<masked[^>]*>", shown)), {label})
        for secret in secrets:
            for text in (shown, saved, report):
                self.assertNotIn(secret, text)

    def test_a_yaml_tag_or_a_shell_expansion_is_read_as_its_reader_reads_it_or_the_file_stops_the_run(self):
        # the round-4 re-review (2026-09-25): a YAML value tagged binary through a %TAG handle (!e!binary, !binary),
        # and a .env value a shell reads with arithmetic inside "…", hexadecimal arithmetic or ${#NAME}, reached the
        # evidence whole or in part, because the reader did not read it as PyYAML or the shell does. Each such reading
        # is now masked whole, or — a reading only the program can make — the file stops the run before the check;
        # the neighbours of each are here too (the shell readings superseded by the A1 literal boundary — every
        # masked shell case below stops the run now; the YAML cases stand)
        secret = "r5-synthetic-value-69173"
        body = base64.b64encode(secret.encode()).decode()

        def shell(name="DB_PASSWORD"):   # a check that sources .env with a POSIX shell and prints one value
            return ("import subprocess; print(subprocess.run(['/bin/sh', '-c', 'set -a; . ./.env; printf %s "
                    + '"$' + name + '"' + "'], stdout=subprocess.PIPE).stdout.decode())")
        decoded = ("import base64, re; print(base64.b64decode(re.search('cjUt[A-Za-z0-9+/=]+', open('secrets.yaml')"
                   ".read()).group()).decode())")   # the value PyYAML makes of the binary tag, read without PyYAML
        # SUPERSEDED (A1 literal boundary, 2026-09-27): every masked shell case here held a '$' — arithmetic
        # $((…)) or $[…], ${#NAME}, $(…), '$$' even inside single quotes — or more than one assignment on a line.
        # The grammar refuses any '$' or backtick in a value ("no references, interpolation or expansion", single
        # quotes included: dotenv 0.3–1.2 interpolate there) and any line past one literal [export ]NAME=VALUE, so
        # each file now stops the run before the check instead of being masked as the shell reads it. name:
        # ({file: text}, the value and its pieces, a two-digit piece checked against the printed text only)
        superseded = {
            "arithmetic inside double quotes": (
                {".env": 'DB_PASSWORD="Horse$((9100+37))Staple"\n'}, ("Horse9137Staple", "9137"), ()),
            "hexadecimal arithmetic": ({".env": "DB_PASSWORD=Horse$((0x23B1))Staple\n"}, ("Horse9137Staple",), ()),
            "the length of another value": (
                {".env": "A=HorseBattery\nDB_PASSWORD=Orbit${#A}Moon\n"}, ("Orbit12Moon",), ("12",)),
            "octal arithmetic": ({".env": "DB_PASSWORD=Horse$((017+9122))Staple\n"}, ("Horse9137Staple",), ()),
            "arithmetic in brackets": ({".env": "DB_PASSWORD=Horse$[9100+37]Staple\n"}, ("Horse9137Staple",), ()),
            "the length of another value inside double quotes": (
                {".env": 'A=HorseBattery\nDB_PASSWORD="Orbit${#A}Moon"\n'}, ("Orbit12Moon",), ("12",)),
            "arithmetic inside a default value": (
                {".env": "R5_UNSET=\nDB_PASSWORD=${R5_UNSET:-Horse$((9100+37))Staple}\n"},
                ("Horse9137Staple", "9137"), ()),
            # nothing inside '…' is expanded — but a '$' refuses even there now
            "$$ and $( … ) inside single quotes": (
                {".env": "DB_PASSWORD='pa$$wo$(rd)9137'\n"}, ("pa$$wo$(rd)9137", "9137"), ()),
            # an assignment a shell goes on to make on the same line: never one literal assignment, refused too
            "a password a URL's & hands to the shell": (
                {".env": "DATABASE_URL=postgres://db/app?user=app&password=Horse$((9100+37))\n"}, ("Horse9137",),
                ()),
            "a second assignment after a plain value": (
                {".env": "APP=demo DB_PASSWORD=Horse$((9100+37))Staple\n"}, ("Horse9137Staple",), ()),
            "a PIN assigned after a plain value": ({".env": "APP=demo DB_PIN=$((4800+21))\n"}, ("4821",), ()),
            "an assignment in the command after a ;": (   # a path since round 8: no inherited function (B1)
                {".env": "APP=demo /usr/bin/true; DB_PASSWORD=Horse$((9100+37))Staple\n"}, ("Horse9137Staple",), ()),
            "an assignment after a redirection": (
                {".env": "APP=demo 2>/dev/null DB_PASSWORD=Horse$((9100+37))Staple\n"}, ("Horse9137Staple",), ()),
            # a number under names that say nothing secret was a readable setting; the line is no literal
            # assignment now, so the file stops the run
            "a port assigned after a plain value": ({".env": "APP=demo PORT=$((8000+80))\n"}, ("8080",), ()),
        }
        for name, (files, secrets, pieces) in superseded.items():
            with self.subTest(name):
                shown, _ = self.refused(name, files, shell(), secrets)
                for piece in pieces:
                    self.assertNotIn(piece, shown)
        for name, (files, reader, secrets, label) in {
                "an Ansible vault value, a tag kept as text": (
                    {"secrets.yml": "password: !vault |\n  $ANSIBLE_VAULT;1.1;AES256\n  r5-vault-line-7101\n"},
                    "print(open('secrets.yml').read().splitlines()[2].strip())", ("r5-vault-line-7101",),
                    "<masked password>"),
                "a tag another schema names through %TAG": (
                    {"secrets.yaml": "%TAG !e! tag:example.com,2000:\n---\npassword: !e!thing r5-tagged-7102\n"},
                    "print(open('secrets.yaml').read().split()[-1])", ("r5-tagged-7102",),
                    "<masked password>")}.items():
            with self.subTest(name):
                self.assert_masked_whole(name, files, reader, secrets, label)
        refused = {   # name: ({file: text}, what the check prints) — the check must never run
            "a YAML binary tag through a named handle": (
                {"secrets.yaml": "%TAG !e! tag:yaml.org,2002:\n---\npassword: !e!binary " + body + "\n"}, decoded),
            "a YAML binary tag through the primary handle": (
                {"secrets.yaml": "%TAG ! tag:yaml.org,2002:\n---\npassword: !binary " + body + "\n"}, decoded),
            "a YAML binary tag with an escaped letter": (
                {"secrets.yaml": "password: !!bin%61ry " + body + "\n"}, decoded),
            "a YAML binary tag written in full with an escaped comma": (
                {"secrets.yaml": "password: !<tag:yaml.org%2C2002:binary> " + body + "\n"}, decoded),
            "a YAML tag written against a comma, which PyYAML reads on": (
                {"secrets.yaml": "%TAG !e! tag:yaml.org\n---\npasswords: [!e!,2002:binary " + body + "]\n"}, decoded),
            "PyYAML's python/bytes through a handle": (
                {"secrets.yaml": "%TAG !! tag:yaml.org,2002:python/\n---\npassword: !!bytes " + body + "\n"}, decoded),
            "a YAML binary tag on a line whose comment holds {{": (
                {"secrets.yaml": "password: !!binary " + body + " # {{ .Values.note }}\n"}, decoded),
            "a command's output": ({".env": "DB_PASSWORD=Horse$(printf %s 9137)Staple\n"}, shell()),
            "a command's output in backquotes inside double quotes": (
                {".env": 'DB_PASSWORD="Horse`printf %s 9137`Staple"\n'}, shell()),
            "arithmetic over a name": ({".env": "A=9100\nDB_PASSWORD=Horse$((A+37))Staple\n"}, shell()),
            "a part of another value": ({".env": "A=HorseBattery9137\nDB_PASSWORD=${A:5:11}Staple\n"}, shell()),
            "the shell's process id": ({".env": "DB_PASSWORD=Horse$$Staple\n"}, shell()),
            "the length of the shell's flags": ({".env": "DB_PASSWORD=Horse${#-}Staple9137\n"}, shell()),
        }
        for name, (files, reader) in refused.items():
            with self.subTest(name):
                code, shown, saved, report, ran = self.check_prints(name, files, reader)
                self.assertEqual(code, 2, report)
                self.assertFalse(ran)                                      # the check never ran
                self.assertIsNone(saved)                                   # and no evidence was written
                self.assertIn(next(iter(files)), report)
                self.assertIn("cannot be masked", report)
                self.assertNotIn(secret, shown + report)
                self.assertNotIn("9137", shown)


    def refused(self, name, files, reader, secrets, env=None):
        """The file stops the run: exit 2, the check never ran, no evidence file, the file named, no value shown.
        Returns (what was printed, the report) so a caller can check a value's short pieces against the printed
        text only — a two-digit piece could collide with the temporary folder's random name in the report's path."""
        code, shown, saved, report, ran = self.check_prints(name, files, reader, env)
        self.assertEqual(code, 2, report)
        self.assertFalse(ran)
        self.assertIsNone(saved)
        self.assertIn(next(iter(files)), report)
        self.assertIn("cannot be masked", report)
        for secret in secrets:
            self.assertNotIn(secret, shown + report)
        return shown, report

    def test_a_yaml_file_is_read_as_a_template_s_text_only_for_template_syntax_and_never_past_a_decoding_tag(self):
        # the round-5 re-review (2026-09-25): a valid YAML file the reader stopped on was read as a template's text
        # whenever that line held {{ or {% anywhere — in a comment, in a quoted value — so a binary tag PyYAML
        # decodes, on that line or further on, reached the evidence decoded and unmasked. The text reading is now
        # taken only for a marker in the line's data, and never for a file holding a tag PyYAML decodes
        secret = "r6-synthetic-value-78421"
        body = base64.b64encode(secret.encode()).decode()
        decoded = ("import base64, re; print(base64.b64decode(re.search('cjYt[A-Za-z0-9+/=]+', open('secrets.yaml')"
                   ".read()).group()).decode())")   # the value PyYAML makes of the binary tag, read without PyYAML
        for name, source in {
                "a binary tag on a document's own line, a marker in its comment":
                    "--- {password: !!binary BODY} # {{ harmless }}\n",
                "the same with an escaped letter": "--- {password: !!bin%61ry BODY} # {{ harmless }}\n",
                "the same written in full with an escaped comma":
                    "--- {password: !<tag:yaml.org%2C2002:binary> BODY} # {{ harmless }}\n",
                "the same as PyYAML's python/bytes": "--- {password: !!python/bytes BODY} # {{ harmless }}\n",
                "a marker in a quoted value on that line": '--- {note: "{{benign}}", password: !!binary BODY}\n',
                "the same through a %TAG handle":
                    '%TAG !e! tag:yaml.org,2002:\n--- {note: "{{benign}}", password: !e!binary BODY}\n',
                "an explicit key holding a quoted marker, then a binary tag":
                    '? "{{benign}}"\n: harmless\npassword: !!binary BODY\n',
                "a tagged key holding a quoted marker, then a binary tag":
                    '!!str "{{benign}}": harmless\npassword: !!binary BODY\n',
                "a template line, and a binary tag further on":
                    "metadata:\n  name: {{ .Release.Name }}-db\npassword: !!binary BODY\n",
                "a template line, and a binary tag through a %TAG handle further on":
                    "%TAG !e! tag:yaml.org,2002:\n---\nmetadata:\n  name: {{ .Release.Name }}-db\n"
                    "password: !e!binary BODY\n"}.items():
            with self.subTest(name):
                self.refused(name, {"secrets.yaml": source.replace("BODY", body)}, decoded, (secret, body))
        number = "import re; print(int(re.search('0x[0-9A-Fa-f]+', open('secrets.yaml').read()).group(), 16))"
        for name, source in {   # no tag at all: a number PyYAML works out, which the text reading never masks
                "a number PyYAML works out, a marker only in the comment": "--- {pin: 0x12D5} # {{ harmless }}\n",
                "a number PyYAML works out, a marker only in a quoted value":
                    '--- {note: "{{benign}}", pin: 0x12D5}\n'}.items():
            with self.subTest(name):
                self.refused(name, {"secrets.yaml": source}, number, ("4821",))
        with self.subTest("a template line whose comment holds a marker too is still read as text"):
            self.assert_masked_whole(
                "template line with a marked comment",
                {"secrets.yaml": "metadata:\n  name: {{ .Release.Name }}-db # {{ note }}\nliteral: r6-helm-7301\n"},
                "print(open('secrets.yaml').read().split()[-1])", ("r6-helm-7301",), "<masked secrets.yaml>")

    def test_a_shell_value_is_read_with_the_shell_s_own_variables_or_the_file_stops_the_run(self):
        # the round-5 re-review (2026-09-25): ${#NAME} measured another reader's value of NAME, not the shell's (after
        # arithmetic, quoting, an escape, a continued line, a same-line or += assignment, or one && or || skipped); an
        # assignment inside an unused ${…} branch was made anyway; export -n, export --, readonly -- and declare -x
        # lost the value they assign; and arithmetic past 64 bits was worked out as the shell never works it out. Each
        # reading is now the shell's own, masked whole — or the file stops the run before the check (the masked
        # readings superseded by the A1 literal boundary: every one stops the run now)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        sourced = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', '. ./.env; printf \"%s\\\\n\" "
                   "\"$DB_PASSWORD\"'], stdout=subprocess.PIPE).stdout.decode(), end='')")
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each masked case here held a construct the literal grammar
        # refuses — a '$' (arithmetic, ${#NAME}), a backslash or quotes outside the literal quoting, a continued
        # line, several assignments or a command on one line, '+=', '&', 'export --'/'readonly --' — so each file
        # now stops the run before the check; none is read as the shell reads it any longer. The cases already
        # refused below stand. name: (the .env text, the value and its pieces, a two-digit piece checked against
        # the printed text only)
        superseded = {
            "the length of a value worked out by arithmetic": (
                "A=Horse$((9100+37))Staple\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit15Moon",), ("15",)),
            "the same in double quotes": (
                'A="Horse$((9100+37))Staple"\nDB_PASSWORD=Orbit${#A}Moon\n', ("Orbit15Moon",), ("15",)),
            "the length of a word with an escaped space": (
                "A=Horse\\ Battery\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit13Moon",), ("13",)),
            "the length of a word continued on the next line": (
                "A=Horse\\\nBattery\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit12Moon",), ("12",)),
            "the length of a C-quoted word": ("A=$'Horse\\x41'\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit6Moon",), ()),
            "the length of joined quotes": (
                "A=Horse'Battery'\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit12Moon",), ("12",)),
            "the length of a single-quoted $": (
                "A='Horse$Battery'\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit13Moon",), ("13",)),
            "the length of a value assigned earlier on the line": (
                "A=HorseBattery DB_PASSWORD=Orbit${#A}Moon\n", ("Orbit12Moon",), ("12",)),
            "the length after +=": ("A=Horse; A+=Battery; DB_PASSWORD=Orbit${#A}Moon\n", ("Orbit12Moon",), ("12",)),
            "a value a background job never changes": (
                "A=Horse\nA=Battery9137 &\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit5Moon",), ()),
            "a value one command's assignment never changes": (   # a path since round 7: no inherited function
                "A=Horse\nA=Battery9137 /usr/bin/true\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit5Moon",), ()),
            "a value assigned beside an &> redirection": (
                "A=HorseBattery9 &>/dev/null\nDB_PASSWORD=Orbit${#A}Moon\n", ("Orbit13Moon",), ("13",)),
            "export's words, all expanded before it assigns": (   # A is o2d to the shell, o$((1+1))d to others
                "A=o$((1+1))d\nexport A=Horse9137 DB_PASSWORD=Orbit${#A}Moon\n", ("Orbit3Moon",), ()),
            "a value export assigns after --": (
                "APP=demo; export -- DB_PASSWORD=Horse$((9100+37))Staple\n", ("Horse9137Staple", "9137"), ()),
            "a value readonly assigns after --": (
                "APP=demo; readonly -- DB_PASSWORD=Horse$((9100+37))Staple\n", ("Horse9137Staple", "9137"), ()),
            "a line the shell reads as the rest of a word": (   # B set first: the file's own since round 7
                "B=Horse\nA=Horse\\\nB=Battery9137\nDB_PASSWORD=Orbit${#B}Moon\n", ("Orbit5Moon",), ()),
            "a value readonly assigns on a line of its own": (
                "readonly DB_PASSWORD=Horse$((9100+37))Staple\n", ("Horse9137Staple", "9137"), ()),
            "arithmetic at the edge of 64 bits": (
                "DB_PASSWORD=Horse$((9223372036854775807-9223372036854766670))Staple\n", ("Horse9137Staple",), ()),
            # final-review R1: an assignment inside a ${…} branch the shell never uses is never made — and
            # ${#B} of the never-set B is 0, computed now that the environment is known empty for it
            "an assignment in an unused default": (
                "A=Horse\nDB_PASSWORD=Orbit${A:-${B:=HorseBattery9137}}${#B}Moon\n", ("Orbit0Moon", "9137"), ()),
            "an assignment in an unused alternate": (
                "A=\nDB_PASSWORD=Orbit${A:+${B:=HorseBattery9137}}${#B}Moon\n", ("Orbit0Moon", "9137"), ()),
        }
        for name, (source, secrets, pieces) in superseded.items():
            with self.subTest(name):
                shown, _ = self.refused(name, {".env": source}, sourced, secrets)
                for piece in pieces:
                    self.assertNotIn(piece, shown)
        for name, source in {
                "an assignment after false &&": "A=Horse; false && A=BatteryABC; DB_PASSWORD=Orbit${#A}Moon9137\n",
                "an assignment after true ||": "A=Horse; true || A=BatteryABC; DB_PASSWORD=Orbit${#A}Moon9137\n",
                "a pipeline": "A=Horse | cat\nDB_PASSWORD=Orbit${#A}Moon9137\n",
                "export -n": "APP=demo; export -n DB_PASSWORD=Horse$((9100+37))Staple\n",
                "an assignment before export": "A=Horse9137 export DB_PASSWORD=Orbit${#A}Moon\n",
                "declare -x": "APP=demo; declare -x DB_PASSWORD=Horse$((9100+37))Staple\n",
                "a number past 64 bits": "DB_PASSWORD=Horse$((0x10000000000000000+9137))Staple\n",
                "a sum past 64 bits": "DB_PASSWORD=Horse$((9223372036854775807+9223372036854775807+9139))Staple\n",
                "a here-document the shell prints": "cat <<EOF\nHorse$((9100+37))Staple\nEOF\n",
                "eval": "eval DB_PASSWORD=Horse$((9100+37))Staple\n",
                "an array's length": "DB[0]=Horse9137\nDB_PASSWORD=Orbit${#DB}Moon\n",
                "a reference in a command's words": "A=Horse9137\necho Orbit${A}Moon\n"}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, sourced, ("9137",))

    def sourced(self, name="DB_PASSWORD", before="", args=""):
        """A check that sources .env with /bin/sh — after `before`, with `args` as the shell's own arguments — and
        prints one value."""
        script = (before + "; " if before else "") + '. ./.env; printf "%s\\n" "$' + name + '"'
        return ("import subprocess, shlex; print(subprocess.run(['/bin/sh', '-c', %r, 'sh'] + shlex.split(%r), "
                "stdout=subprocess.PIPE).stdout.decode(), end='')" % (script, args))

    def test_a_reference_the_file_does_not_decide_is_computed_from_the_constructed_environment(self):
        # the round-6 re-review (2026-09-25): DB_PASSWORD=${SECRET:-safe-fallback} was read with SECRET unset, but a
        # shell sourcing the file inherits SECRET from wherever it runs — the check printed the inherited secret and
        # the evidence kept it. Under inheritance every such reading was refused (round 7). Stage 1 changed what
        # that means, and final-review R1 closed the gap: the check's environment is constructed, so nothing is
        # inherited — a name the file does not set is the constructed environment's when it holds it and
        # determinably empty when it does not (D4 rule 5: refuse only what stays indeterminate). Each case below
        # runs twice, with the parent holding the round-7 secrets and without: the parent's values must never
        # appear, and the reading the file decides — the fallback, the empty string, the file's own parts — is
        # computed and masked whole, checked against the real /bin/sh sourcing the file under that environment
        # (superseded by the A1 literal boundary — every computed and masked case below stops the run now)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        inherited = {"SECRET": "runtime-secret-99173", "A": "runtime-secret-99174", "B": "runtime-secret-99175",
                     "DB_PASSWORD": "runtime-secret-99176", "SALT": "runtime-secret-99177"}
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each computed case held a reference or form the literal
        # grammar refuses — any '$' in a value ("no references, interpolation or expansion"), '+=' (not NAME=), or
        # a command on the line — so each file now stops the run before the check, in a parent environment holding
        # the round-7 secrets and in an empty one alike; the constructed-environment reading is never made
        superseded = {
            "a variable in a default (the reviewer's case)": "DB_PASSWORD=${SECRET:-safe-fallback}\n",
            "a reference": "DB_PASSWORD=Horse${SECRET}Staple\n",
            "a reference without braces": "DB_PASSWORD=Horse$SECRET\n",
            "a default in double quotes": 'DB_PASSWORD="${SECRET:-safe-fallback}"\n',
            "a reference in double quotes": 'DB_PASSWORD="Horse$SECRET"\n',
            "an alternate, unset": "DB_PASSWORD=Horse${SECRET:+Battery}Staple\n",
            "a length of an unset value": "DB_PASSWORD=Orbit${#SECRET}Moon\n",
            "a trimming pattern that is empty": "C=HorseBattery\nDB_PASSWORD=${C#$SECRET}\n",
            "an assigned default": "DB_PASSWORD=${SECRET:=safe-fallback}\n",
            "a default the shell uses, nested": "C=\nDB_PASSWORD=${C:-Horse${D:-${SECRET}}}\n",
            "an alternate the shell uses, nested": "C=x\nDB_PASSWORD=${C:+Horse${SECRET}}\n",
            "chained: an earlier value from outside": "C=${SECRET}\nDB_PASSWORD=Horse${C}Staple\n",
            "chained: a name exported, never set": "export A\nDB_PASSWORD=Horse${A}Staple\n",
            "a name set only on a later line": "DB_PASSWORD=Horse$B\nB=Battery9137\n",
            "readonly": "readonly DB_PASSWORD=${SECRET:-safe-fallback}\n",
            "export's words, all expanded before it assigns": "export A=Battery9137 DB_PASSWORD=Horse$A\n",
            "an assignment earlier on the line": "APP=demo DB_PASSWORD=$SECRET\n",
            "a command after ;": "APP=demo; DB_PASSWORD=x${SECRET}y\n",
            "+= onto a name nowhere set": "DB_PASSWORD+=Staple9137\n",
            "export with +=": "export DB_PASSWORD+=Staple9137\n",
            "a command the file names, which nothing invisible can stand in for": (
                "C=Horse\nAPP=demo true\nDB_PASSWORD=${C}\n"),
            "export": "export DB_PASSWORD=$SECRET\n",
            "export after --": "export -- DB_PASSWORD=${SECRET}\n",
        }
        for name, source in superseded.items():
            for environment in (inherited, {}):
                with self.subTest(name, inherited=bool(environment)):
                    self.refused(name + " inherited" * bool(environment), {".env": source}, self.sourced(),
                                 tuple(inherited.values()), environment)
        for name, source in {   # still refused — genuinely indeterminate even with the environment known:
                "an error-style default on an empty value": "DB_PASSWORD=${SECRET:?safe-fallback}\n",
                "a name made read-only, then assigned": (
                    "readonly A\nA=safe-value\nDB_PASSWORD=Horse${A}Staple\n")}.items():
            for environment in (inherited, {}):
                with self.subTest(name, inherited=bool(environment)):
                    self.refused(name + " inherited" * bool(environment), {".env": source}, self.sourced(),
                                 tuple(inherited.values()), environment)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): these were masked whole because the shell never reads
        # SECRET where the file sets the name whose default or operator holds it — but every fixture still holds a
        # '$' (or a '+=', not NAME=), which the grammar refuses outright, so each file now stops the run before
        # the check. SECRET is still passed in the tool's own environment to prove the boundary: the parent's
        # values never reach the check at all, inherited or not
        for name, (source, secrets) in {
                "the default of a value the file sets": (
                    "C=HorseBattery9137\nDB_PASSWORD=${C:-${SECRET}}\n", ("HorseBattery9137",)),
                "the same without braces, in double quotes": (
                    'C=HorseBattery9137\nDB_PASSWORD="${C:-$SECRET}"\n', ("HorseBattery9137",)),
                "- and = of a value the file sets, even empty": (
                    "C=\nDB_PASSWORD=Horse${C-$SECRET}${C=$SECRET}Staple9137\n", ("HorseStaple9137",)),
                ":= and :? of a value the file sets": (
                    "C=HorseBattery9137\nDB_PASSWORD=${C:=$SECRET}${C:?$SECRET}\n",
                    ("HorseBattery9137HorseBattery9137",)),
                "the pattern of an empty value": (
                    "C=\nDB_PASSWORD=Horse${C#$SECRET}Staple9137\n", ("HorseStaple9137",)),
                "a variable the file sets, not the environment's": (
                    "SALT=Battery9137\nDB_PASSWORD=Horse${SALT}Staple\n", ("HorseBattery9137Staple",)),
                "+= onto a value the file sets": (
                    "DB_PASSWORD=Horse\nDB_PASSWORD+=Battery9137\n", ("HorseBattery9137",)),
                "export of a value the file set before": (
                    "A=Battery9137\nexport DB_PASSWORD=Horse$A\n", ("HorseBattery9137",)),
                ":= giving a name the file sets empty a value only the shell works out": (
                    "C=\nD=${C:=Horse$((9000+137))}\nDB_PASSWORD=${C}Staple\n", ("Horse9137Staple",))}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), secrets + tuple(inherited.values()),
                             {"SECRET": inherited["SECRET"]})

    def test_a_value_the_file_does_not_decide_stops_the_run_and_the_shell_reads_every_line_as_written(self):
        # the round-7 builder's checks against /bin/sh (2026-09-25): positional and special parameters, the shell's own
        # variables, ~ and its working folders, the locale's length and pattern matching, $'…' escapes and $"…" that
        # shells read differently all reached the evidence unmasked; so did a value holding a literal $ (read again
        # for references), a line python-dotenv reads as the rest of a quoted value (never read for the shell at all),
        # and a Windows line break (a carriage return the shell keeps in the value). Each is now refused or masked
        # whole, and a refusal never shows the file's text (the computed and masked cases superseded by the A1
        # literal boundary: all of them stop the run now)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        c_locale = self.sourced(before="LC_ALL=C; export LC_ALL")
        for name, (source, reader, secrets) in {
                "a positional parameter": ("DB_PASSWORD=Horse$1Staple\n", self.sourced(args="Battery9137"),
                                           ("Battery9137",)),
                "a positional parameter's default": ("DB_PASSWORD=${1:-safe}\n", self.sourced(args="Battery9137"),
                                                     ("Battery9137",)),
                "a positional parameter the sourcing shell has none of (round 3's fixture)": (
                    "DB_PASSWORD=r3-l4-dol$1lar-0107\n", self.sourced(), ("r3-l4-dollar-0107", "lar-0107")),
                "$# and $@": ("DB_PASSWORD=Horse$#-$@Staple\n", self.sourced(args="Battery9137 x"), ("Battery9137",)),
                "$? of the command before": ("DB_PASSWORD=Horse$?Staple9137\n", self.sourced(before="false"),
                                             ("Horse1Staple9137",)),
                "a variable the shell works out itself": ("RANDOM=1\nDB_PASSWORD=Horse$RANDOM\n", self.sourced(),
                                                          ("Horse",)),
                ":? on an empty value, where the shell stops and prints its word": (
                    "C=\nexport -- DB_PASSWORD=Horse${C:?Staple9137}Staple\n", self.sourced(), ("Staple9137", "9137")),
                "~+, the working folder": ("DB_PASSWORD=~+/Hunter2Staple9137\n", self.sourced(),
                                           ("Hunter2Staple9137",)),
                "~- and ~1": ("DB_PASSWORD=~-/Hunter2Staple9137:~1\n", self.sourced(), ("Hunter2Staple9137",)),
                "the length of a value outside ASCII": ("C=Hors" + chr(233) + "\nDB_PASSWORD=Orbit${#C}Moon9137\n",
                                                        c_locale, ("Orbit6Moon9137",)),
                "a range in a trimming pattern": ("C=BatteryHorse9137\nDB_PASSWORD=${C#[a-z]}\n", self.sourced(),
                                                  ("atteryHorse9137",)),
                "an extended pattern": ("C=HorseBattery9137\nDB_PASSWORD=${C#@(Horse|x)}\n", self.sourced(),
                                        ("Battery9137",)),
                "hexadecimal bytes forming UTF-8 in $'…'": ("DB_PASSWORD=$'P\\xc3\\xa9ssword9137'\n", self.sourced(),
                                                            ("P" + chr(233) + "ssword9137",)),
                "a byte outside ASCII in $'…'": ("DB_PASSWORD=$'Hunter\\351Staple9137'\n", self.sourced(),
                                                 ("Staple9137",)),
                "\\u in $'…', which bash 3.2 keeps": ("C=$'Horse\\u0041'\nDB_PASSWORD=Orbit${#C}Moon9137\n",
                                                      self.sourced(), ("Orbit11Moon9137",)),
                "\\c before a character that is no letter": ("DB_PASSWORD=$'Horse9137\\c?'\n", self.sourced(),
                                                             ("Horse9137",)),
                "a NUL byte in $'…', where the shell's value ends": ("DB_PASSWORD=$'Hunter2\\0Staple9137'\n",
                                                                    self.sourced(), ("Hunter2",)),
                'a $"…" the locale translates': ('DB_PASSWORD=$"Horse9137Staple"\n', self.sourced(),
                                                ("Horse9137Staple",)),
                "a command's output on such a line": ("C='x\\'\nDB_PASSWORD=Horse$(printf %s 9137)Staple #'\n",
                                                      self.sourced(), ("Horse9137Staple",)),
                "a refusal never shows the line's word": ("Hunter2Staple9137$X\n", self.sourced(),
                                                          ("Hunter2Staple9137",)),
                # round 6's refusal, where round 7's reading alone would accept the line (its two pins of a part the
                # shell skips are masked below since round 8: the owner's rule, B4); ~name is B5's refusal now
                "an assignment before export, of a name the file sets": (
                    "A=x\nA=Horse9137 export DB_PASSWORD=Orbit${#A}Moon\n", self.sourced(), ("Orbit1Moon",))}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, reader, secrets, {"SECRET": "runtime-secret-99173"})
        # SUPERSEDED (A1 literal boundary, 2026-09-27): these two were computed (the constructed HOME; SECRET
        # determinably unset) — but a '~' at a value's start refuses (bash expands it through the account
        # database) and any '$' refuses, so each file now stops the run before the check
        for name, source in {
                "~ without a HOME the file sets: the constructed HOME": "DB_PASSWORD=~/Hunter2Staple9137\n",
                "a variable nowhere set on a line python-dotenv reads inside a quote": (
                    "C='x\\'\nDB_PASSWORD=${SECRET:-safe} #'\n")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("Hunter2Staple9137", "runtime-secret-99173"),
                             {"SECRET": "runtime-secret-99173"})
        # SUPERSEDED (A1 literal boundary, 2026-09-27): masked whole, as the shell prints them — but an array
        # assignment (no literal NAME=), a '${…}', a '$' inside single quotes, arithmetic, and a carriage return
        # (the boundary is LF-only) all sit outside the literal grammar, so each file now stops the run before
        # the check
        for name, (source, secrets) in {
                "an array's element named in a part the shell skips": (
                    "DB[0]=Horse9137\nC=x\nDB_PASSWORD=${C:-${DB}}Moon9137\n", ("xMoon9137",)),
                "an assignment inside a part the shell skips, of a name the file sets": (
                    "A=Horse\nB=x\nDB_PASSWORD=Orbit${A:-${B:=HorseBattery9137}}${#B}Moon\n", ("OrbitHorse1Moon",)),
                "a value holding a literal $, never read again": ("C='$B'\nD=$C$C\nDB_PASSWORD=Orbit${#D}Moon9137\n",
                                                                  ("Orbit4Moon9137",)),
                "arithmetic on a line python-dotenv reads inside a quote": (
                    "C='x\\'\nDB_PASSWORD=Horse$((9100+37))Staple #'\n", ("Horse9137Staple",)),
                "the length of a value ending a Windows line": ("C=Horse\r\nDB_PASSWORD=Orbit${#C}Moon9137\r\n",
                                                                ("Orbit6Moon9137",))}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), secrets)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): stage 1 (NEW-5 slice 3) masked a '~' reading with the
        # file's own HOME; the grammar refuses '~' at a value's start or after a ':' (bash expands it through the
        # account database), so both files now stop the run before the check
        for name, source in {
                "~ with the file's HOME": "HOME=/r7-file-home\nDB_PASSWORD=~/Hunter2Staple9137\n",
                "~ starting a default's word": "HOME=/r7-file-home\nC=\nDB_PASSWORD=${C:-~/Hunter2Staple9137}\n"}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("Hunter2Staple9137",))

    SECRET = "runtime-secret-99173"   # the round-7 reviewer's synthetic inherited value

    def test_no_inherited_function_can_stand_in_for_a_command_under_the_constructed_environment(self):
        # B1, the round-7 re-review (2026-09-25): a function inherited from the environment (BASH_FUNC_frob%%) stood in
        # for a command the file runs and changed a value the file had set before it; under inheritance such a value
        # was refused unless the file set it again. Stage 1 removes the channel itself: the constructed environment
        # admits no BASH_FUNC_* (D3), so no function is ever inherited, a bare command name is resolved on the
        # constructed PATH (or simply not found) and can never change the sourcing shell's variables — the file's own
        # values stand and are masked, and the function's value is nowhere (final-review R1: the readings are
        # determinate, so D4 rule 5 computes them; refusal is kept only where a reading stays indeterminate). Each
        # case runs with the function defined in the tool's own environment: proof it never reaches the check
        # (the computed and masked cases superseded by the A1 literal boundary: all of them stop the run now)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        secret = self.SECRET
        frob = {"BASH_FUNC_frob%%": "() { DB_PASSWORD=%s; APP=%s; }" % (secret, secret)}
        true = {"BASH_FUNC_true%%": "() { DB_PASSWORD=%s; }" % secret}
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each computed case held a bare command line ('frob',
        # 'true') or a reference or a space in an unquoted value — a bare line, any '$', and interior whitespace
        # are all outside the literal grammar, so each file now stops the run before the check; the BASH_FUNC_*
        # entries still stand in the tool's own environment as proof nothing is ever inherited
        for name, (source, reader, functions) in {
                "a value set before the command (the reviewer's case)": (
                    "DB_PASSWORD=from-file\nfrob\n", self.sourced(), frob),
                "a value exported before the command": ("export DB_PASSWORD=from-file\nfrob\n", self.sourced(), frob),
                "a value set earlier on the command's line": ("DB_PASSWORD=from-file; frob\n", self.sourced(), frob),
                "a builtin nothing invisible stands in for": ("DB_PASSWORD=from-file\ntrue\n", self.sourced(), true),
                "a NAME=value on the command's own line: it lasts only for the command": (
                    "APP=demo frob\n", self.sourced("APP"), frob),
                "another value set again, not this one": (
                    "DB_PASSWORD=from-file\nAPP=demo\nfrob\nAPP=again\n", self.sourced(), frob),
                "a reference after the command, to a value the file sets again later": (
                    "C=Horse\nfrob\nDB_PASSWORD=${C}\nC=again\n", self.sourced(),
                    {"BASH_FUNC_frob%%": "() { C=%s; }" % secret}),
                "an unquoted value with a space: the shell runs its second word": (
                    "APP_NAME=My App\n", self.sourced("APP_NAME"),
                    {"BASH_FUNC_App%%": "() { APP_NAME=%s; }" % secret})}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, reader, (secret,), functions)
        with self.subTest("a reference in a command's words: still refused"):   # a different refusal, standing
            self.refused("a reference in a path command's words", {".env": "A=Horse9137\n/bin/echo Orbit${A}Moon\n"},
                         self.sourced(), (secret,), frob)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the controls ran the file's own value to the evidence,
        # masked — but each holds a bare command line ('frob', '/usr/bin/true', 'frob &'), which the grammar
        # refuses, so each file stops the run before the check and neither the file's value nor the function's
        # value appears anywhere
        for name, (source, value) in {
                "a value the file sets again after the command (the reviewer's control)": (
                    "DB_PASSWORD=from-file\nfrob\nDB_PASSWORD=after-file9137\n", "after-file9137"),
                "a path command, which no function stands in for (the reviewer's control)": (
                    "DB_PASSWORD=from-file9137\n/usr/bin/true\n", "from-file9137"),
                "a function run as a background job": ("DB_PASSWORD=from-file9137\nfrob &\n", "from-file9137")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (value, secret), frob)
        with self.subTest("a value made read-only before the command: the shell stops rather than change it"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): a 'readonly NAME=…' line is no literal assignment (only
            # a single 'export ' prefix is admitted) and 'frob' is a bare line — the file stops the run before
            # the check, the function's value nowhere
            self.refused("read-only before a function", {".env": "readonly DB_PASSWORD=from-file9137\nfrob\n"},
                         self.sourced(), (secret, "from-file9137"), frob)

    def test_a_byte_order_mark_a_shell_reads_as_part_of_the_first_word_stops_the_run(self):
        # B2, the round-7 re-review: the reader decoded a .env file's byte order mark away and read its first line as
        # an assignment, but a shell sourcing the file reads the mark's bytes as part of the first word — a command it
        # cannot find — so an inherited DB_PASSWORD stayed and the check printed it. A .env file that starts with a
        # byte order mark now stops the run, whatever the environment holds; another secret file with one is read as
        # before
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        plain = "DB_PASSWORD=from-file\n"
        for name, data in {"UTF-8 (the reviewer's case)": codecs.BOM_UTF8 + plain.encode("utf-8"),
                           "UTF-16 little-endian": codecs.BOM_UTF16_LE + plain.encode("utf-16-le"),
                           "UTF-16 big-endian": codecs.BOM_UTF16_BE + plain.encode("utf-16-be"),
                           "UTF-32 little-endian": codecs.BOM_UTF32_LE + plain.encode("utf-32-le"),
                           "UTF-32 big-endian": codecs.BOM_UTF32_BE + plain.encode("utf-32-be")}.items():
            for environment in ({"DB_PASSWORD": self.SECRET}, {}):
                with self.subTest(name, inherited=bool(environment)):
                    self.refused(name + " inherited" * bool(environment), {".env": data}, self.sourced(),
                                 (self.SECRET,), environment)
        with self.subTest("a JSON secret file with a byte order mark is read as before"):
            self.assert_masked_whole("json with a mark", {"secrets.json": codecs.BOM_UTF8 + b'{"password": "Horse9137"}'},
                                     "print('Horse9137')", ("Horse9137",), "<masked password>")

    def test_json_text_in_a_env_file_never_stands_in_for_the_shell_reading_it_refuses(self):
        # B3, the round-7 re-review: a .env file whose text is also one JSON document was read as JSON when the shell
        # reading refused it, so the check ran — and the shell, which runs the line as a command, printed an error
        # holding the inherited SECRET. A .env refusal now stands when the text is JSON too; a JSON line the shell
        # reading accepts is read both ways, as before
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        errors = ("import subprocess; print(subprocess.run(['/bin/sh', '-c', '. ./.env'], stdout=subprocess.PIPE, "
                  "stderr=subprocess.STDOUT).stdout.decode(), end='')")   # what the shell prints, its errors too
        for name, source in {"an object (the reviewer's case)": '{"A":"${SECRET:-safe-fallback}"}\n',
                             "a list": '["${SECRET:-safe-fallback}"]\n',
                             "an object whose key says secret": '{"DB_PASSWORD":"${SECRET:-safe-fallback}"}\n'}.items():
            for environment in ({"SECRET": self.SECRET}, {}):
                with self.subTest(name, inherited=bool(environment)):
                    self.refused(name + " inherited" * bool(environment), {".env": source}, errors, (self.SECRET,),
                                 environment)
        with self.subTest("a JSON line the shell reading accepts is read as JSON too"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): the line begins with '{', no literal assignment, so
            # the .env file stops the run before the check — a .env file is never read as JSON any longer
            self.refused("json line accepted", {".env": '{"A":"Horse9137Staple"}\n'},
                         "import json; print(json.load(open('.env'))['A'])", ("Horse9137Staple",))

    def test_a_construct_in_a_part_the_shell_skips_never_stops_the_run_and_stops_it_where_the_shell_reads_it(self):
        # B4, the round-7 re-review: ${A:-$(printf unsafe)} with A set was refused although /bin/sh never runs the
        # command; so were an empty ${A:+…} and a set ${A:=…}. The owner's rule (2026-09-25): a construct in a part the
        # shell provably does not evaluate never stops the run for what it would do if evaluated — ${A:-${B:=unsafe}}
        # included — and where the shell does evaluate it, the refusals stand. Each value below is what /bin/sh prints;
        # a part the reader cannot find the end of as the shell does is still refused (the masked cases superseded by
        # the A1 literal boundary: every one stops the run now; the refused ones stand)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        skipped = {"SECRET": self.SECRET}
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each of these was masked as /bin/sh prints it (the skipped
        # part never evaluated) — but every fixture holds a '${…}' or a '$', and any '$' or backtick in a value
        # refuses under the literal grammar whether or not the shell would evaluate the part, so each file now
        # stops the run before the check. The cases where the shell evaluates the part, below, stay refused
        for name, (source, value) in {
                "a command's output in the default of a set value (the reviewer's case)": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(printf unsafe)}\n", "chosen9137"),
                "a command's output in the alternate of an empty value": (
                    "A=\nDB_PASSWORD=Horse${A:+$(printf unsafe)}Staple9137\n", "HorseStaple9137"),
                "a command's output in := of a set value": (
                    "A=chosen9137\nDB_PASSWORD=${A:=$(printf unsafe)}\n", "chosen9137"),
                "an assignment inside a skipped part (the owner's example)": (
                    "A=chosen9137\nDB_PASSWORD=${A:-${B:=unsafe}}\n", "chosen9137"),
                "a part of a value, in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-${SECRET:1}}\n", "chosen9137"),
                "a command's output in the pattern of an empty value": (
                    "A=\nDB_PASSWORD=Horse${A#$(printf unsafe)}Staple9137\n", "HorseStaple9137"),
                "backquotes in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-`printf unsafe`}\n", "chosen9137"),
                "$$ in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-$$}\n", "chosen9137"),
                "division by zero in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-$((1/0))}\n", "chosen9137"),
                "arithmetic over a name in a skipped part": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$((B+1))}\n", "chosen9137"),
                "indirection in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-${!A}}\n", "chosen9137"),
                "an array's element in a skipped part": (
                    "DB[0]=x\nA=chosen9137\nDB_PASSWORD=${A:-${DB}}\n", "chosen9137"),
                "~name in a skipped part": ("A=chosen9137\nDB_PASSWORD=${A:-~root/x}\n", "chosen9137"),
                "~+ in a skipped part (the reviewer's probe)": ("A=chosen9137\nDB_PASSWORD=${A:-~+}\n", "chosen9137"),
                "a command's output over two lines in a skipped part": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(printf un\nsafe)}\n", "chosen9137"),
                # refused in round 8 as parts whose end the reader could not find; /bin/sh reads both (round 9)
                "a } inside backquotes in a skipped part": ("A=Horse9137\nDB_PASSWORD=${A:-`echo }`}\n", "Horse9137"),
                "a quote inside a command's output in a skipped part": (
                    "A=Horse9137\nDB_PASSWORD=${A:-$(echo ')')}\n", "Horse9137")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (value, self.SECRET), skipped)
        for name, source in {   # the same constructs where the shell evaluates them
                "a command's output in the default of an empty value": "A=\nDB_PASSWORD=${A:-$(printf Horse9137)}\n",
                "an assignment inside a part the shell uses": "A=\nDB_PASSWORD=${A:-${B:=Horse9137}}\n",
                "an assignment inside a part the shell uses, to a name the file sets": (
                    "A=\nB=\nDB_PASSWORD=${A:-${B:=Horse9137}}\n"),
                "a command's output in the pattern of a set value": "A=Horse9137\nDB_PASSWORD=${A#$(printf H)}\n",
                "backquotes in a part the shell uses": "A=\nDB_PASSWORD=${A:-`printf Horse9137`}\n",
                "$$ in a part the shell uses": "A=\nDB_PASSWORD=Horse${A:-$$}9137\n",
                "an array's element in a part the shell uses": "DB[0]=Horse9137\nA=\nDB_PASSWORD=${A:-${DB}}\n",
                "~name in a part the shell uses": "A=\nDB_PASSWORD=${A:-~root/Horse9137}\n",
                # /bin/sh ends the ${ … } at the } inside the command's output, then stops at the ) left over
                "a } inside a command's output in a skipped part": (
                    "A=Horse9137\nDB_PASSWORD=${A:-$(echo })}\n")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("Horse9137",), skipped)

    def test_a_home_folder_the_user_database_decides_stops_the_run(self):
        # B5, the round-7 re-review: DB_PASSWORD=~root/suffix was accepted, but the user database, not the file,
        # decides what ~root is (/var/root on this Mac). ~name now stops the run wherever the shell expands it — at a
        # word's start, after a ':' in an assignment, starting a used ${…} word; ~ with a HOME the file sets does not
        # (that last masked case superseded by the A1 literal boundary: '~' at a value's start stops the run now)
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        for name, source in {"~root (the reviewer's case)": "DB_PASSWORD=~root/Hunter2Staple9137\n",
                             "~ with a user name the database does not hold": "DB_PASSWORD=~nosuch9137/Hunter2Staple\n",
                             "~name after a ':' in an assignment": "DB_PASSWORD=/opt:~root/Hunter2Staple9137\n",
                             "~name in a command's words": "APP=x /usr/bin/true ~root/Hunter2Staple9137\n",
                             "~name exported": "export DB_PASSWORD=~root/Hunter2Staple9137\n"}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("Hunter2Staple", "/var/root"))
        with self.subTest("~ with a HOME the file sets"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): stage 1 slice 3 masked this reading (the file's HOME
            # was determinable); the grammar refuses '~' at a value's start (bash expands it through the account
            # database), so the file now stops the run before the check
            self.refused("tilde with the file's HOME", {".env": "HOME=/r8-home\nDB_PASSWORD=~/Hunter9137\n"},
                         self.sourced(), ("Hunter9137",))

    def test_a_value_python_dotenv_takes_from_the_environment_is_computed_never_guessed(self):
        # B6, the round-7 re-review (§7): python-dotenv 1.2.3 fills ${NAME} and ${NAME:-default} in every value —
        # single-quoted and backslash-escaped too — from the values set on earlier lines, else from the environment;
        # and load_dotenv() at its default keeps a value the environment already holds, over a name the file sets and
        # over a name a value is filled from. Under inheritance each leaked the inherited value, so the owner's rule
        # (2026-09-25) was: refuse. Stage 1 (NEW-5 slices 2–3, D4 rules 4–5): the environment is constructed and known
        # exactly, so each such reading is determinable and never refuses — a name the parent environment alone holds
        # is nothing to the check; a name the constructed environment holds fills or wins with a known value (a
        # declared --env value, masked as the winner; a synthesized one, not a secret); a name nothing holds fills in
        # empty. What python-dotenv reads from the file alone is masked as before — and the shell's own refusals
        # stand: a bare line is a command to it. (All of that modeling is superseded by the literal boundary —
        # see below.)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): python-dotenv's fill-ins are gone with the reader models —
        # a '${…}' anywhere (single quotes and $'…' included), an escaped '$', a '~' at a value's start, a bare
        # line, a quoted or dotted key, and a line python-dotenv cannot read all refuse under the literal grammar,
        # so each such file stops the run before the check rather than being computed or masked. What stands is
        # the one plain literal assignment below (the reviewer's case): admitted and masked, the parent's value
        # never reaching the check
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        secret = self.SECRET
        for name, (source, environment) in {   # every one now stops the run before the check
                "a single-quoted reference (the reviewer's case)": ("DB_PASSWORD='${SECRET}'\n", {"SECRET": secret}),
                "the same, nothing inherited": ("DB_PASSWORD='${SECRET}'\n", {}),
                "a single-quoted default (the reviewer's case)": (
                    "DB_PASSWORD='${SECRET:-safe-fallback}'\n", {"SECRET": secret}),
                "an escaped dollar (the reviewer's case)": ("DB_PASSWORD=\\${SECRET}\n", {"SECRET": secret}),
                "a reference inside an alternate the shell skips": (
                    "C=\nDB_PASSWORD=Horse${C:+${SECRET}}Staple\n", {"SECRET": secret}),
                "a reference inside $'…'": ("DB_PASSWORD=$'Horse${SECRET}9137'\n", {"SECRET": secret}),
                "a reference to a name set only on a later line": ("DB_PASSWORD='${A}'\nA=later\n", {"A": secret}),
                "HOME the file sets, which the constructed environment always holds": (
                    "HOME=/r8-home\nDB_PASSWORD=~/x\n", {})}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (secret,), environment)
        with self.subTest("a reference to a name the file gives no value"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): the bare first line is no literal assignment, and a
            # '$' in the second line's single quotes refuses — the file stops the run before the check
            self.refused("a name the file gives no value", {".env": "A\nDB_PASSWORD='x${A}y'\n"}, self.sourced(),
                         (secret,), {"A": secret})
        with self.subTest("a key the file names with no value"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): a bare line is no literal assignment — the file stops
            # the run before the check
            self.refused("a bare key line", {".env": "APP=x\nDB_PASSWORD\n"}, self.sourced(), (secret,),
                         {"DB_PASSWORD": secret})
        with self.subTest("a name the file sets (the reviewer's case), held only by the parent environment"):
            # unchanged: a plain literal assignment is admitted — the file runs, masked as the file-only reading,
            # and the value the parent environment alone holds is nothing to the check
            code, shown, saved, report, ran = self.check_prints(
                "a name the file sets", {".env": "DB_PASSWORD=from-file\n"}, self.sourced(), {"DB_PASSWORD": secret})
            self.assertEqual(code, 0, report)
            self.assertTrue(ran)
            self.assertNotIn("from-file", shown)
            self.assertIn("<masked DB_PASSWORD>", shown)
            for text in (shown, saved, report):
                self.assertNotIn(secret, text)
        for name, (source, environment, value) in {   # SUPERSEDED (A1 literal boundary, 2026-09-27): each held
                # only by the parent environment — but a '${…}', a quoted key, and a line python-dotenv cannot
                # read all refuse under the grammar now, so each file stops the run before the check
                "a name a value is filled from": ("A=from-file\nDB_PASSWORD=${A}\n", {"A": secret}, "from-file"),
                "a quoted key": ("'DB_PASSWORD'=from-file\n", {"DB_PASSWORD": secret}, "from-file"),
                "a key after a line python-dotenv cannot read": (
                    "APP B=x\nDB_PASSWORD=from-file\n", {"DB_PASSWORD": secret}, "from-file"),
                "a length python-dotenv reads as a variable named #C": (
                    "C=HorseBattery\nDB_PASSWORD=Orbit${#C}Moon\n", {"#C": secret}, "Orbit12Moon"),
                # keys no constructed environment can hold (not shell names) — a quoted key and a dotted one are
                # no literal NAME= either, so refused all the same
                "a quoted key after a line python-dotenv cannot read": (
                    "APP B=x\n'DB PASSWORD'=from-file\n", {"DB PASSWORD": secret}, "from-file"),
                "a key holding a dot": ("DB.PASSWORD=from-file\n", {"DB.PASSWORD": secret}, "from-file")}.items():
            with self.subTest(name + ", held only by the parent environment"):
                self.refused(name, {".env": source}, self.sourced(), (secret, value), environment)
        for name, (source, value) in {   # SUPERSEDED (A1 literal boundary, 2026-09-27): python-dotenv read these
                # from the file alone — masked — but each holds a '${…}', which the grammar refuses, so each file
                # now stops the run before the check
                "a name filled from an earlier line, nothing inherited (the reviewer's control)": (
                    "A=from-file9137\nDB_PASSWORD=${A}\n", "from-file9137"),
                "a length, nothing named #C inherited": (
                    "C=HorseBattery\nDB_PASSWORD=Orbit${#C}Moon9137\n", "Orbit12Moon9137"),
                "${C-…}: a name no shell sets, not inherited": (
                    "C=\nDB_PASSWORD=Horse${C-$SECRET}Staple9137\n", "HorseStaple9137"),
                "${C=…}: a name that holds '=', never in an environment": (
                    "C=\nDB_PASSWORD=Horse${C=$SECRET}Staple9137\n", "HorseStaple9137")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (value, secret), {"SECRET": secret})

    def test_valid_syntax_in_a_part_the_shell_skips_is_masked_and_stops_the_run_where_the_shell_reads_it(self):
        # B4, the round-8 re-review (2026-09-26): with A set, ${A:-"unsafe"}, ${A:-'unsafe'}, ${A:-\$SECRET},
        # ${A:-$(printf 'unsafe')} and ${A:-$(printf un\safe)} print A's value under /bin/sh, which never reads the part
        # after :-, yet the reader refused each: a quote or a backslash inside ${ … } stopped it before the shell's
        # choice of part was made. Where a ${ … } ends is now found as bash 3.2 finds it, both when it reads the word
        # and when it expands it: valid syntax in a part the shell skips is masked as the shell prints it, and where the
        # shell reads that part, ends the ${ … } somewhere else, or never, the run stops. Each value is what /bin/sh
        # prints (the round-9 handoff's r9-shell-facts.json) — the masked cases superseded by the A1 literal
        # boundary: every one stops the run now; the refused ones stand
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        skipped = {"SECRET": self.SECRET}
        # SUPERSEDED (A1 literal boundary, 2026-09-27): each of these was masked as bash prints it, the skipped
        # part never read — but every fixture holds a '${ … }' (a '$' in a value refuses: "no references,
        # interpolation or expansion"), so each file now stops the run before the check, whether or not the shell
        # would evaluate the part. The cases where the shell reads the part, below, were and stay refused
        for name, (source, value) in {
                "double quotes (the reviewer's case)": ('A=chosen9137\nDB_PASSWORD=${A:-"unsafe"}\n', "chosen9137"),
                "single quotes (the reviewer's case)": ("A=chosen9137\nDB_PASSWORD=${A:-'unsafe'}\n", "chosen9137"),
                "an escaped $ (the reviewer's case)": ("A=chosen9137\nDB_PASSWORD=${A:-\\$SECRET}\n", "chosen9137"),
                "a quoted command's output (the reviewer's case)": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(printf 'unsafe')}\n", "chosen9137"),
                "a backslash in a command's output (the reviewer's case)": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(printf un\\safe)}\n", "chosen9137"),
                "a } in single quotes": ("A=chosen9137\nDB_PASSWORD=${A:-'}'}x\n", "chosen9137x"),
                "a } in double quotes": ('A=chosen9137\nDB_PASSWORD=${A:-"}"}x\n', "chosen9137x"),
                "an escaped }": ("A=chosen9137\nDB_PASSWORD=${A:-\\}}x\n", "chosen9137x"),
                "a # in a command's output, then its line break": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(echo # x\n)}x\n", "chosen9137x"),
                "a } in quotes in a command's output": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(echo \"}\" '}')}x\n", "chosen9137x"),
                "an escaped } in a command's output": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(echo \\})}x\n", "chosen9137x"),
                "$'…' with an escaped quote and a }": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$'x\\'}'}x\n", "chosen9137x"),
                '$"…" with a }': ('A=chosen9137\nDB_PASSWORD=${A:-$"x}"}x\n', "chosen9137x"),
                "every kind at once": ("A=chosen9137\nDB_PASSWORD=${A:-\"a\"'b'\\c$(d \"e\")`f \"g\"`}x\n",
                                       "chosen9137x"),
                "quotes in a part skipped inside a part the shell reads": (
                    'B=val9137\nA=\nDB_PASSWORD=${A:-${B:-"x}"}}x\n', "val9137x"),
                "single quotes in a ${ … } in double quotes": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-'unsafe'}x\"\n", "chosen9137x"),
                "double quotes in a ${ … } in double quotes, inside a word": (
                    'A=chosen9137\nDB_PASSWORD=a"${A:-"x}"}"b\n', "achosen9137b"),
                "a backslash and a line break": ("A=chosen9137\nDB_PASSWORD=${A:-x\\\ny}z\n", "chosen9137z"),
                ":+ of an empty value": ('A=\nDB_PASSWORD=Horse${A:+"$(printf RAN)"}Staple9137\n', "HorseStaple9137"),
                "the pattern of an empty value": ('A=\nDB_PASSWORD=Horse${A#"$(printf RAN)"}Staple9137\n',
                                                  "HorseStaple9137"),
                ":= of a set value": ('A=chosen9137\nDB_PASSWORD=${A:="unsafe"}\n', "chosen9137"),
                "a quoted } in backquotes": ("A=chosen9137\nDB_PASSWORD=${A:-`printf 'x}'`}y\n", "chosen9137y"),
                "a command's output holding a } in backquotes": (
                    "A=chosen9137\nDB_PASSWORD=${A:-`echo $(echo })`}y\n", "chosen9137y"),
                "$[ … ] holding quotes in double quotes": (
                    'A=chosen9137\nDB_PASSWORD=${A:-"$[ "]" ]"}y\n', "chosen9137y"),
                # bash ends the inner ${ … } at the } in the command's output as it reads the word, and after it as it
                # expands it — the word goes on, so the one after that ends the outer one
                "a } in a command's output, in a part skipped inside a part the shell reads": (
                    "B=val9137\nA=\nDB_PASSWORD=${A:-${B:-$(echo })}}x\n", "val9137x"),
                "a comment holding a } in a command's output, skipped inside a part read": (
                    "B=val9137\nA=\nDB_PASSWORD=${A:-${B:-$(echo # }\n)}}x\n", "val9137x"),
                "a $'…' in double quotes decoding to the } that ends the ${ … }: as bash reads it": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-$'\\x7d'}unsafe9137\"\n", "chosen9137}unsafe9137"),
                "a $'…' bash rewrote, left outside the ${ … } by the } another decodes to": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-$'\\x7d'$'q9137'}tail\"\n", "chosen9137q9137}tail"),
                "a $'…' holding \\' in a part skipped inside a part the shell reads": (
                    "B=val9137\nA=\nDB_PASSWORD=${A:-${B:-$'it\\'s'}}x\n", "val9137x"),
                "an escaped quote in double quotes": ('A=chosen9137\nDB_PASSWORD=${A:-"\\"}"}x\n', "chosen9137x"),
                "a quote after a ${ … } in a skipped part": ('A=chosen9137\nDB_PASSWORD=${A:-${B:-x}"y"}z\n',
                                                              "chosen9137z"),
                "an escaped backquote in backquotes": ("A=chosen9137\nDB_PASSWORD=${A:-`echo \\``}x\n", "chosen9137x"),
                "a comment in a command's output, its line continued, then the output closed": (
                    "A=chosen9137\nDB_PASSWORD=${A:-$(echo # x\\\n)\n)}\n", "chosen9137"),
                # bash escapes a \x01 or \x7f byte its own way as it reads a word; with no backslash before it, its
                # expansion still ends the ${ … } where the reading does (round 8 masked these; so must round 9)
                "a \\x01 byte": ("A=chosen9137\nDB_PASSWORD=${A:-\x01}x\n", "chosen9137x"),
                "a \\x7f byte": ("A=chosen9137\nDB_PASSWORD=${A:-\x7f}x\n", "chosen9137x"),
                "a $'…' in double quotes decoding to a \\x01 byte": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-$'\\001'}x}y9137\"\n", "chosen9137x}y9137")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (value, self.SECRET), skipped)
        inherited = {"DB_PASSWORD": self.SECRET}   # an inherited DB_PASSWORD survives a line the shell stops on
        for name, (source, environment) in {
                "double quotes the shell reads": ('A=\nDB_PASSWORD=${A:-"unsafe9137"}\n', skipped),
                "single quotes the shell reads": ("A=\nDB_PASSWORD=${A:-'unsafe9137'}\n", skipped),
                "an escaped $ the shell reads": ("A=\nDB_PASSWORD=${A:-\\$unsafe9137}\n", skipped),
                "a quoted command's output the shell runs": ("A=\nDB_PASSWORD=${A:-$(printf 'unsafe9137')}\n", skipped),
                "a backslash in a command's output the shell runs": (
                    "A=\nDB_PASSWORD=${A:-$(printf un\\safe9137)}\n", skipped),
                "quotes in a nested part the shell reads": ('A=\nB=\nDB_PASSWORD=${A:-${B:-"unsafe9137"}}\n', skipped),
                "a bare } in a command's output: the shell stops at the ) left over": (
                    "A=chosen9137\nAPP=demo DB_PASSWORD=${A:-$(echo })}unsafe9137\n", inherited),
                "a quote never closed in a skipped part": ('A=chosen9137\nAPP=demo DB_PASSWORD=${A:-"}unsafe9137\n',
                                                           inherited),
                "a ${ … } never closed": ('A=chosen9137\nAPP=demo DB_PASSWORD=${A:-"unsafe9137"\n', inherited),
                # a # starting a word in a command's output makes the rest of its line a comment as bash expands it —
                # there the ) and the } too, so the shell finds no end: a bad substitution, the assignment never made
                "a comment in a command's output taking its ) and the }": (
                    "A=chosen9137\nAPP=demo DB_PASSWORD=${A:-$(echo # )}\nB=unsafe9137\n", inherited),
                "a comment in a command's output, its line continued onto the )": (
                    "A=chosen9137\nAPP=demo DB_PASSWORD=${A:-$(echo # x\\\n)}\nB=unsafe9137\n", inherited),
                "a $'…' inside a ${ … } in double quotes, in a part the shell reads": (
                    "A=\nDB_PASSWORD=\"${A:-$'unsafe9137'}\"\n", skipped),
                "a \\x01 byte after a backslash, which bash escapes its own way as it reads a word": (
                    "A=chosen9137\nDB_PASSWORD=${A:-\\\x01}x}unsafe9137\n", skipped),
                "a \\x01 byte after the backslash a $'…' in double quotes decodes to": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-$'\\\\'\x01}x}unsafe9137\"\n", skipped),
                # bash reads the backslash one $'…' decodes to with the first character the next one decodes to
                "a $'…' decoding to a \\x01 byte after one decoding to a backslash (bash: a bad substitution)": (
                    "A=chosen9137\nAPP=demo DB_PASSWORD=\"${A:-$'\\\\'$'\\001'}tail9137\"\n", inherited),
                "a $'…' decoding to a } after one decoding to a backslash": (
                    "A=chosen9137\nDB_PASSWORD=\"${A:-$'\\\\'$'}'}unsafe9137\"\n", skipped)}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("unsafe9137", self.SECRET), environment)

    def test_a_name_followed_by_anything_but_an_operator_stops_the_run_where_the_shell_reads_it(self):
        # BAD-SUBSTITUTION, found by the round-9 builder and corrected with B4 by the owner's decision (2026-09-26):
        # ${A${B}}, ${A$(cmd)}, ${A`cmd`}, ${A$$} — a name, then anything but an operator — are a "bad substitution"
        # to /bin/sh, which then never makes the line's assignment, so an inherited DB_PASSWORD stays; the reader read
        # each as ${A} and ran the check. Round 7 already leaked ${A${B}}; round 8's marks (B4) added the others. Such a
        # ${ … } now stops the run where the shell reads it — so does a quote after the name, which round 9's reading of
        # quotes would otherwise let through — and a part the shell skips is still never read
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        inherited = {"DB_PASSWORD": self.SECRET}
        for name, source in {
                "a command's output after the name (the builder's case)": "A=x\nAPP=demo DB_PASSWORD=${A$(printf z)}\n",
                "a ${ … } after the name, read-only (round 7 leaked it too)": (
                    "A=x\nB=y\nreadonly DB_PASSWORD=${A${B}}\n"),
                "a ${ … } after the name": "A=x\nB=y\nAPP=demo DB_PASSWORD=${A${B}}\n",
                "backquotes after the name": "A=x\nAPP=demo DB_PASSWORD=${A`printf z`}\n",
                "$$ after the name": "A=x\nAPP=demo DB_PASSWORD=${A$$}\n",
                "double quotes after the name": 'A=x\nAPP=demo DB_PASSWORD=${A"x"}\n',
                "single quotes after the name": "A=x\nAPP=demo DB_PASSWORD=${A'x'}\n",
                "a backslash after the name": "A=x\nAPP=demo DB_PASSWORD=${A\\x}\n",
                "inside a part the shell reads": "A=\nB=y\nAPP=demo DB_PASSWORD=${A:-${A${B}}}\n"}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (self.SECRET,), inherited)
        with self.subTest("inside a part the shell skips"):
            # SUPERSEDED (A1 literal boundary, 2026-09-27): the skipped part was never read and C's value printed
            # masked; any '$' in a value refuses under the literal grammar now, so the file stops the run before
            # the check — the skipped part is never read at all
            self.refused("bad substitution skipped",
                         {".env": "A=x\nB=y\nC=chosen9137\nAPP=demo DB_PASSWORD=${C:-${A${B}}}\n"},
                         self.sourced(), ("chosen9137", self.SECRET), inherited)

    def test_a_quote_the_shell_never_finds_closed_stops_the_run(self):
        # UNCLOSED-QUOTE, found by the round-9 builder and corrected with B4 by the owner's decision (2026-09-26):
        # /bin/sh stops reading the file with a syntax error at a quote it never finds closed, so every name the file
        # sets from that line on keeps the value the environment gives it. The reader stopped reading there too, but
        # accepted the file when no other reader saw that quote — inside a word, on a second assignment, or on an
        # earlier line — and an inherited DB_PASSWORD reached the evidence. B4's faithful reading of quotes in a part
        # the shell skips finds more such lines. A quote the shell never finds closed now stops the run
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        inherited = {"DB_PASSWORD": self.SECRET}
        for name, source in {
                "a double quote inside a word (the builder's case)": 'APP=demo DB_PASSWORD=x"y\n',
                "a single quote inside a word": "APP=demo DB_PASSWORD=x'y\n",
                "a $'…' never closed": "APP=demo DB_PASSWORD=x$'y\n",
                "a quote on an earlier line": "APP=demo X=a'b\nAPP2=demo DB_PASSWORD=from-file9137\n",
                "a quote after a ${ … } whose skipped part holds quotes": (
                    'A=chosen9137\nAPP=demo DB_PASSWORD=${A:-""}"x\n'),
                "a quote never closed inside a ${ … } in double quotes": (
                    'A=chosen9137\nAPP=demo DB_PASSWORD="${A:-"}x"\n')}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (self.SECRET,), inherited)
        with self.subTest("a single-quoted value Node ends at an escaped quote (round 3's R14, masked until round 9)"):
            self.refused("r14 single-quoted", {".env": "API_SECRET='r3-r18-sq-2501\\'r3-r18-sq-2502'\n"},
                         self.sourced("API_SECRET"), ("r3-r18-sq-2501", "r3-r18-sq-2502"))

    # the Node-loader key registry and its tests moved to tests/test_evidence_node.py (the 1,000-line limit)
    def test_a_backslash_before_a_byte_bash_keeps_its_escape_byte_for_stops_the_run(self):
        # found by the round-9 builder: bash reads a \x7f byte after a backslash in "…", and a \x01 or \x7f byte after
        # one in $'…', with its own \x01 escape byte left in the value, which the reader did not have, so the value
        # reached the evidence unmasked (round 8 too; round 9's B4 let more words reach it). Such a word stops the run;
        # the same bytes the reader reads as the shell does were masked (superseded below: they stop the run too now).
        if not os.path.exists("/bin/sh"):
            self.skipTest("a shell's reading needs a POSIX shell (not Windows)")
        env, q = {"SECRET": self.SECRET}, "DB_PASSWORD=$'Quartz9137\\"
        for name, source in {"\\x7f in double quotes": 'DB_PASSWORD="Quartz9137\\\x7fLima"\n',
                             "\\x7f in $'…'": q + "\x7fLima'\n", "\\x01 in $'…'": q + "\x01Lima'\n",
                             "after a $'…' ends a part": 'A=x\nDB_PASSWORD="${A:-$\'}\'\\\x7fLima9137}"\n'}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), ("Quartz9137", "Lima9137"), env)
        # SUPERSEDED (A1 literal boundary, 2026-09-27): the three words below were masked as the shell reads them —
        # but each holds a backslash (refused in a double-quoted value, and outside the unquoted set) and bytes
        # outside the literal range, so each file now stops the run before the check, as the four above already did
        for name, (source, value) in {
                "\\x01 in double quotes": ('DB_PASSWORD="Quartz9137\\\x01Lima"\n', "Quartz9137\\\x01Lima"),
                "an escaped backslash, then \\x7f, in $'…'": (q + "\\\x7fLima'\n", "Quartz9137\\\x7fLima"),
                "\\x7f unquoted": ("DB_PASSWORD=Quartz9137\\\x7fLima\n", "Quartz9137\x7fLima")}.items():
            with self.subTest(name):
                self.refused(name, {".env": source}, self.sourced(), (value, self.SECRET), env)



if __name__ == "__main__":
    unittest.main()
