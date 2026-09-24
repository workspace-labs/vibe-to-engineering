"""Checks on the protocol text that an agent follows word for word — SKILL.md, its references and the plan template:
the transitions at a gate, the completion outcomes, and what the owner is shown. They guard the wording, not an
agent's behavior.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = Path(os.environ.get("V2E_SKILL_DIR", ROOT / "skills" / "vibe-to-engineering"))  # seam: another copy
SKILL = Path(os.environ.get("V2E_SKILL_MD", SKILL_DIR / "SKILL.md"))


class Protocol(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        self.plan = (SKILL_DIR / "references" / "migration-plan.md").read_text(encoding="utf-8")
        self.template = (SKILL_DIR / "assets" / "plan-template.html").read_text(encoding="utf-8")

    def test_stop_restore_correct_and_retry_are_separate_transitions(self):
        for transition in ("STOP", "RESTORE `<label>`", "CORRECT", "RETRY MIGRATION"):
            self.assertIn("| **%s** |" % transition, self.text)
        for words in ("ONE APPROVAL = ONE STEP", "MIGRATION STOPPED", "RESTORED <label>",
                      "never because of a stop or a restore", "An approval to restore or to correct never includes it"):
            self.assertIn(words, self.text)
        self.assertNotIn("stays at its last verified checkpoint", self.text)  # a stop never implies a restore

    def test_all_green_only_when_every_check_passes_and_approved_failures_stay_visible(self):
        for words in ("`VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES`",
                      "only when every check the plan requires ran in this review and passed",
                      "Still failing (approved at the baseline)",
                      "Never write PASS for a check that fails"):
            self.assertIn(words, self.text)

    def test_the_owner_is_shown_every_file_in_the_trees(self):   # RA-01
        for words in ("prints every file and writes nothing", "Show the human this full tree, never a shortened one",
                      "marked lines included"):
            self.assertIn(words, self.text)
        self.assertIn("they show what the migration never touches", self.template)
        self.assertNotIn("Dependency and build-output folders are not shown", self.template)

    def test_the_plan_and_the_final_report_account_for_every_file_and_every_job(self):   # RA-08
        for words in ('id="files"', "Every file: before → after", "{{FILE_TOTALS}}", "{{FILE_HOLDS_NOW}}",
                      "{{FILE_HOLDS_AFTER}}", "ignored — never touched", "nested repository — never touched",
                      'id="owners"', "Who owns each job", "{{JOB_OWNER_NOW}}", "{{JOB_OWNER_AFTER}}"):
            self.assertIn(words, self.template)
        for words in ("**Every file: before → after**", "the ones the migration never touches included",
                      "**who owns each job**", "closing line of `checkpoint.py tree --current`"):
            self.assertIn(words, self.plan)
        for words in ("account for every file", "who owns each job (database access",
                      "every file before → after, and who owns each job — as they actually came out"):
            self.assertIn(words, self.text)

    def test_every_plan_ends_with_a_record_of_the_structure_left_in_the_project(self):   # RA-02
        for words in ("the documentation phase ends every plan", 'Leave it out only when the human declines it ("no docs")',
                      "every folder and file it names exists and holds what it says", "say that the project holds none",
                      "the record in the project stays either way"):
            self.assertIn(words, self.text)
        for words in ("**The documentation phase comes last,**", "never the migration's history",
                      "The plan shows its exact text", 'at the plan gate ("no docs")', "the ledger records the decision",
                      'otherwise a "Project layout" section in the README'):
            self.assertIn(words, self.plan)
        for words in ('id="record"', "{{RECORD_WHERE}}", "{{RECORD_TEXT}}", 'reply "no docs"'):
            self.assertIn(words, self.template)

    def test_a_changed_ignored_file_is_a_break_like_a_gone_one(self):   # RA-03
        for words in ("no ignored file `changed`", "A changed ignored file is a break like a gone one",
                      "reports none `gone` or `changed`", "ignored files it reports `changed` included"):
            self.assertIn(words, self.text)


if __name__ == "__main__":
    unittest.main()
