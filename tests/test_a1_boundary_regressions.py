"""Independent regressions for A1-F01/F02; synthetic values, no third-party readers.

Run: python3 -m unittest discover -s tests -p test_a1_boundary_regressions.py -v
Live reader disagreement is separately established by the differential matrix.
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "vibe-to-engineering" / "scripts"
TOOL = Path(os.environ.get("V2E_EVIDENCE", SCRIPTS / "evidence.py"))
sys.path.insert(0, str(SCRIPTS))
import envliteral  # noqa: E402
import enrolled  # noqa: E402 — the isolated HOME with the suite's runners enrolled (A2)


class BoundaryRegressions(unittest.TestCase):
    PREFIXES = ("", "export ")
    QUOTES = ("'", '"')
    # Python and ECMAScript trimming differ at U+FEFF; old dotenv uses JS trim.
    EDGE_SPACES = ("\u00a0", "\u1680", "\u2000", "\u2007", "\u2028",
                   "\u2029", "\u202f", "\u205f", "\u3000", "\ufeff")

    def run_fixture(self, source, printed):
        with tempfile.TemporaryDirectory(prefix="v2e-a1-regression-") as folder:
            base = Path(folder).resolve()
            project = base / "project"
            (project / ".vibe-to-engineering").mkdir(parents=True)
            (project / ".env").write_bytes(source.encode("utf-8"))
            # If launched, this prints exactly the synthetic decoded value whose
            # masking cannot be justified by the literal grammar.
            (project / "check.py").write_text(
                "from pathlib import Path\n"
                "Path('check-ran').write_text('ran')\n"
                "print(%r)\n" % printed, encoding="utf-8")
            evidence = project / ".vibe-to-engineering" / "evidence" / "check.txt"
            result = subprocess.run(
                [sys.executable, str(TOOL), "--project", str(project),
                 "--out", str(evidence), "--", sys.executable, "-B", "check.py"],
                capture_output=True, timeout=30,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(enrolled.enrolled_home()),
                     "LANG": "C", "LC_ALL": "C"})
            diagnostics = (result.stdout + result.stderr).decode("utf-8", "replace")
            saved = evidence.read_text(encoding="utf-8") if evidence.exists() else None
            return result.returncode, (project / "check-ran").exists(), saved, diagnostics

    def assert_refused_before_launch(self, source, forbidden):
        code, ran, saved, diagnostics = self.run_fixture(source, forbidden)
        # Assert the whole contract together, so RED records all consequences.
        raw_value = source.partition("=")[2].rstrip("\n")[1:-1]
        self.assertEqual(
            (code, ran, saved is not None, forbidden in diagnostics or raw_value in diagnostics),
            (2, False, False, False), diagnostics)
        self.assertIn("cannot be masked", diagnostics)

    def test_valid_literals_reach_check_and_are_masked_end_to_end(self):
        values = ("café-9137", "a\tb-9137", "a\\nb-9137")
        for prefix in self.PREFIXES:
            with self.subTest(prefix=prefix):
                source = "".join(prefix + "SECRET_%d='%s'\n" % (index, value)
                                 for index, value in enumerate(values))
                code, ran, saved, diagnostics = self.run_fixture(source, "\n".join(values))
                self.assertEqual((code, ran, saved is not None), (0, True, True), diagnostics)
                for value in values:
                    self.assertNotIn(value, diagnostics)
                    self.assertNotIn(value, saved)
                for index in range(len(values)):
                    self.assertIn("<masked SECRET_%d>" % index, saved)

    def test_single_quoted_backslash_pairs_and_neighboring_runs_refuse(self):
        for prefix in self.PREFIXES:
            for count in (2, 3, 4, 5, 6):
                for value in ("Hor5e" + "\\" * count + "9137Staple",
                              "\\" * count + "Horse9137Staple",
                              "Horse9137Staple" + "\\" * count):
                    with self.subTest(prefix=prefix, count=count, value=value):
                        with self.assertRaises(envliteral.NotLiteral):
                            envliteral.assignments(prefix + "DB_PASSWORD='" + value + "'\n")

    def test_backslash_runs_stop_before_check_or_evidence(self):
        for prefix in self.PREFIXES:
            for count in (2, 3, 4):
                value = "Hor5e" + "\\" * count + "9137Staple"
                decoded = "Hor5e" + "\\" * ((count + 1) // 2) + "9137Staple"
                with self.subTest(prefix=prefix, count=count):
                    self.assert_refused_before_launch(
                        prefix + "DB_PASSWORD='" + value + "'\n", decoded)

    def test_unicode_whitespace_at_either_quoted_edge_refuses(self):
        for prefix in self.PREFIXES:
            for quote in self.QUOTES:
                for space in self.EDGE_SPACES:
                    for value in (space + "Horse9137Staple", "Horse9137Staple" + space):
                        with self.subTest(prefix=prefix, quote=quote, value=value):
                            with self.assertRaises(envliteral.NotLiteral):
                                envliteral.assignments(prefix + "DB_PASSWORD=" + quote + value + quote + "\n")

    def test_every_c1_control_is_refused_in_both_quote_styles(self):
        for prefix in self.PREFIXES:
            for quote in self.QUOTES:
                for codepoint in range(0x80, 0xA0):
                    value = "Horse" + chr(codepoint) + "9137Staple"
                    with self.subTest(prefix=prefix, quote=quote, codepoint=codepoint):
                        with self.assertRaises(envliteral.NotLiteral):
                            envliteral.assignments(prefix + "DB_PASSWORD=" + quote + value + quote + "\n")

    def test_unicode_edge_and_control_refusals_stop_before_launch(self):
        for prefix in self.PREFIXES:
            for quote in self.QUOTES:
                for value in ("\u00a0Horse9137Staple\u00a0", "Horse\u00859137Staple",
                              "\u2007Horse9137Staple", "Horse9137Staple\ufeff"):
                    with self.subTest(prefix=prefix, quote=quote, value=value):
                        self.assert_refused_before_launch(
                            prefix + "DB_PASSWORD=" + quote + value + quote + "\n", value)

    def test_ordinary_unicode_interior_tabs_and_single_backslash_n_stay_literal(self):
        for prefix in self.PREFIXES:
            for quote in self.QUOTES:
                for value in ("café", "a\tb", "café\t9137"):
                    with self.subTest(prefix=prefix, quote=quote, value=value):
                        self.assertEqual(
                            envliteral.assignments(prefix + "A=" + quote + value + quote + "\n"),
                            [("A", value, None)])
            self.assertEqual(envliteral.assignments(prefix + "A='a\\nb'\n"), [("A", "a\\nb", None)])


if __name__ == "__main__":
    unittest.main()
