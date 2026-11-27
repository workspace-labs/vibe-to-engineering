"""Exercise decisions in the shipped instructions. Agent obedience needs a separate exam."""
import hashlib
from pathlib import Path
import unittest


SKILL = Path(__file__).resolve().parents[1] / "skills" / "vibe-to-engineering" / "SKILL.md"
HEADER = "| Decision | Observed facts (alternatives separated by commas) | Action | Instructions |"


def decision_rows(text):
    following = text.split(HEADER + "\n", 1)
    if len(following) != 2:
        raise ValueError("workflow decision table missing")
    rows = {}
    for line in following[1].splitlines()[1:]:
        if not line.startswith("|"):
            break
        decision, observed, action, instruction = (cell.strip() for cell in line.strip("|").split("|"))
        for fact in observed.split(", "):
            key = (decision, fact)
            if not fact or not action or key in rows:
                raise ValueError("missing or ambiguous workflow decision")
            rows[key] = action, instruction
    return rows


class Decisions(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.assertTrue(HEADER in self.skill, "workflow decision table missing")
        self.rows = decision_rows(self.skill)

    def expect(self, decision, action, *facts):
        for fact in facts:
            with self.subTest(decision=decision, fact=fact):
                self.assertEqual(self.rows.get((decision, fact), (None,))[0], action)

    def test_approval_is_specific_to_the_pending_step(self):
        self.expect("Approval", "Ask", "question", "comment", "silence", "other step")
        self.expect("Approval", "Take this step", "this step explicitly approved")
        self.expect("Phase boundary", "Wait", "blanket permission", "one phase approved")

    def test_scope_and_evidence_bound_a_diagnosis(self):
        self.expect("Scope", "Decline migration workflow", "feature", "bug fix", "small local refactor")
        self.expect("Scope", "Inspect", "whole-project structural review")
        self.expect("Inspection", "Report unknown", "unread", "inaccessible")
        self.expect("Standard", "Follow project decision", "conflicting local decision")
        self.expect("Diagnosis", "No finding", "layout preference only")
        self.expect("Verdict", "NO MIGRATION REQUIRED", "no findings", "minor findings only")
        self.expect("Verdict", "Design read-only", "material structural finding")

    def test_ledger_tree_abstraction_and_final_outcomes(self):
        self.expect("Resume", "Wait at next gate", "phase completed")
        self.expect("Resume", "Report break", "phase started but incomplete")
        self.expect("Tree", "Show complete tree", "full inventory requested")
        self.expect("Abstraction", "Withhold abstraction", "simpler alternative unexamined")
        self.expect("Abstraction", "Record decision", "evidenced C16 reason and simpler alternative insufficient")
        self.expect("Final review", "ALL GREEN", "all required checks passed and warnings closed")
        self.expect("Final review", "COMPLETE WITH APPROVED BASELINE FAILURES",
                    "approved baseline failures only", "approved failures and accepted gaps")
        self.expect("Final review", "COMPLETE WITH ACCEPTED VERIFICATION GAPS",
                    "accepted gaps and all required checks passed")
        self.expect("Final review", "AWAITING HUMAN APPROVAL", "blocking finding", "open warning")

    def test_unreviewed_directive_changes_require_reconciliation(self):
        # Exact owner-facing instructions constrain the neighboring action label. This
        # is a deliberate editorial lock: it cannot interpret arbitrary natural language.
        # Multiple reviewed phrasings can carry the same action. Compare whole cells
        # so an appended contradictory instruction also requires review.
        reviewed = {
            ("Approval", "silence"): {
                "A question, a comment, silence, or approval of something else is not approval — ask.",
                "Ask for explicit approval of this step when the answer is absent, unclear or about a different step.",
            },
            ("Phase boundary", "blanket permission"): {
                'For either request, even if the human says "do all the phases", stop after each one and wait for the next approval.',
                "Wait at each phase boundary for the owner to approve the next step.",
            },
            ("Inspection", "unread"): {
                "Identify the part and the reason. Never judge what you did not read.",
            },
            ("Standard", "conflicting local decision"): {
                "Use the project's rules and decisions. They outrank this skill's standard.",
            },
            ("Diagnosis", "layout preference only"): {
                "Never make a finding because the tree differs from a preferred layout.",
            },
            ("Verdict", "no findings"): {
                "Give the evidenced verdict in section 2. Then stop. Write nothing.",
            },
        }
        for case, acceptable in reviewed.items():
            with self.subTest(case=case):
                self.assertIn(self.rows[case][1], acceptable)
        # These three directives live in frontmatter or in an existing workflow
        # step. A reversal that retains the old words still changes its whole line.
        for prefix, digest in {
            'description: "': "dcbf3cf034aba4f8e113afc02e810857200d44a03022958e845d65db3881a2ab",
            '- the current tree —': "412c657b5cc8db5ca0ab7aa246bad6d7eb032865817329e79d85aa1b3142e71d",
            '- for every abstraction you propose,': "23fb23a265c1503977cb73018d2719dd19922bced7ed21053f232a3f6a51ab51",
        }.items():
            with self.subTest(directive=prefix):
                lines = [line for line in self.skill.splitlines() if line.startswith(prefix)]
                self.assertEqual(len(lines), 1)
                self.assertEqual(hashlib.sha256(lines[0].encode("utf-8")).hexdigest(), digest,
                                 "reconcile the full directive with its workflow decision")

    def test_rewording_and_ambiguous_rows(self):
        action = ("Phase boundary", "blanket permission")
        original = self.rows[action][1]
        alternative = "Wait at each phase boundary for the owner to approve the next step."
        self.assertEqual(decision_rows(self.skill.replace(original, alternative))[action], ("Wait", alternative))
        duplicate = self.skill.replace("| Approval | question,", "| Approval | silence, question,")
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            decision_rows(duplicate)
