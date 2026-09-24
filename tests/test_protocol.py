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


if __name__ == "__main__":
    unittest.main()
