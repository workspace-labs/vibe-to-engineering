"""Exercise the reporting forms and trace the documented reader and wrapper checks."""
from pathlib import Path
import re
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering" / "SKILL.md"


class ReviewProtocol(unittest.TestCase):
    def test_status_three_restore_names_the_exceptions_and_stops(self):
        section = SKILL.read_text(encoding="utf-8").split("**Restoring is never automatic.**", 1)[1].split("## 9.", 1)[0]
        forms = re.findall(r"```\nRESTORED <label>\n(.+?)\n```", section, re.S)
        self.assertEqual(len(forms), 2)
        clean, exceptions = forms
        self.assertIn("Restore: VERIFIED", clean)
        self.assertRegex(section, r"both .+?exit 0.+?If either exits 3, use the following form")
        for item, state in (("notes.db changed", "Differences"), ("cache.bin missing", "Differences"),
                            ("old.dat has no fingerprint", "Unknown")):
            with self.subTest(state=state, item=item):
                filled, count = re.subn(r"(?m)^" + state + r": <[^>]+>", state + ": " + item, exceptions)
                self.assertEqual(count, 1)
                self.assertIn(item, filled)
                self.assertNotRegex(filled, r"(?i)\bverified\b")
                for line in ("Pre-restore checkpoint:", "Checks:", "Phase n: NOT COMPLETE", "AWAITING HUMAN APPROVAL"):
                    self.assertIn(line, filled)

    def test_final_reports_identify_the_actual_checker_in_both_routes(self):
        section = SKILL.read_text(encoding="utf-8").split("## 9. FINAL REVIEW", 1)[1].split("## Always", 1)[0]
        rows = dict(re.findall(r"(?m)^\s*\| ([^|]+) \| `(Review: [^`]+)` \|", section))
        self.assertEqual(set(rows), {"A separate reviewer", "The builder alone"})
        for role, reviewer in (("A separate reviewer", "Reviewer B"), ("The builder alone", "Builder A")):
            with self.subTest(role=role):
                rendered = (rows[role].replace("<builder>", "Builder A").replace("<reviewer>", reviewer)
                            .replace("<actual checks>", "compared trees and ran 12 checks"))
                self.assertIn("Builder A", rendered)
                self.assertIn(reviewer, rendered)
                self.assertIn("ran 12 checks", rendered)
                if reviewer == "Builder A":
                    self.assertIn("BUILDER SELF-CHECK", rendered)
                    self.assertIn("independent review pending", rendered)
                    self.assertNotIn("Review: INDEPENDENT", rendered)
                else:
                    self.assertIn("Review: INDEPENDENT", rendered)
        self.assertIn("every final report", section)
        self.assertIn("builder self-check", (ROOT / "README.md").read_text(encoding="utf-8").lower())

    def test_documented_node_checks_identify_wrapper_and_live_reader_separately(self):
        import test_evidence_node
        import test_literal_matrix
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("test_evidence_node.py` checks wrapper refusal", readme)
        matrix = test_literal_matrix.DifferentialMatrix
        name = "test_every_claimed_reader_stays_inside_the_masked_set"
        self.assertIn(matrix.__name__ + "." + name, readme)
        self.assertTrue(callable(getattr(matrix, name)))
        case = test_evidence_node.NodeLoaders()
        with mock.patch.object(case, "refused") as refused, mock.patch.object(case, "runs_masked") as ran:
            case.test_wrapper_refuses_nonliteral_node_fixtures_with_and_without_parent_values()
        comments = set(case.LITERAL_COMMENT_FIXTURES).intersection(case.NODE_KEYS)
        self.assertEqual({call.args[0] for call in ran.call_args_list}, comments)
        self.assertTrue(comments)
        for fixture, (source, key) in case.NODE_KEYS.items():
            if fixture not in comments:
                refused.assert_any_call(fixture + " node parent", source, {key: case.SECRET})
                refused.assert_any_call(fixture + " node alone", source)
