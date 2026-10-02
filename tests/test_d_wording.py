"""Guards for the D-fix-round wording (the D review of 2026-10-02, owner-approved fix round):

D-F1 — enrollment is a named human gate and the agent never supplies the approval word itself;
D-F4 — the §3.7 limit sentence travels with every fingerprint/checkpoint comparison the skill
templates (the phase-complete block, the restored block, the final report and the ledger rule);
D-F2 — NO MIGRATION REQUIRED lists every finding judged Minor with its reason and says the human
may still ask for a migration; D-F3 — secret files are read for key names only through the form
the skill shows, never through the agent's own ad-hoc command. They guard the wording, not an
agent's behavior — the convention of test_protocol.py / test_c_wording.py.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = Path(os.environ.get("V2E_SKILL_DIR", ROOT / "skills" / "vibe-to-engineering"))
SKILL = Path(os.environ.get("V2E_SKILL_MD", SKILL_DIR / "SKILL.md"))

LIMIT = "do not prove the absence of reads, remote writes or temporary changes"


def fenced_block(text, first_line):
    """The first fenced code block whose first content line is first_line."""
    marker = "```\n" + first_line
    start = text.index(marker) + len(marker)
    return text[start:text.index("```", start)]


class DWording(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.registry = (SKILL_DIR / "references" / "supported-checks.md").read_text(encoding="utf-8")
        self.skill_flat = " ".join(self.skill.split())       # assertions ignore line wraps
        self.registry_flat = " ".join(self.registry.split())

    def test_enrollment_is_a_named_human_gate_the_agent_never_approves_itself(self):   # D-F1
        self.assertIn("| Enrollment |", self.skill)
        for words in ("never supply the approval word",
                      "not typed, not piped, not through stdin by any means",
                      "The human runs the enrollment command and types the approval word themselves",
                      "never covers enrollment"):
            self.assertIn(words, self.skill_flat)
        for words in ("never supplies the approval word itself",
                      "not typed, not piped, not through stdin by any means",
                      "The human runs the enrollment command and types the approval word themselves",
                      "never covers enrollment"):
            self.assertIn(words, self.registry_flat)

    def test_the_limit_sentence_travels_with_every_templated_comparison(self):   # D-F4
        phase = fenced_block(self.skill, "PHASE n COMPLETE")
        self.assertIn(LIMIT, phase)
        restored = fenced_block(self.skill, "RESTORED <label>")
        self.assertIn(LIMIT, restored)
        # the final-report paragraph only, and the new sentence's own words — the older statement
        # near the end of the file ("They **do not prove…**") must not be able to satisfy this
        start = self.skill.index("Follow the outcome with the before and after trees")
        paragraph = self.skill[start:self.skill.index("No commits were made unless they asked for"
                                                      " them.", start)]
        self.assertIn("it carries the limit sentence: the comparison covers local file states and does"
                      " not prove the absence of reads, remote writes or temporary changes", paragraph)
        self.assertIn("wherever the ledger reports a fingerprint or checkpoint comparison as data-safety"
                      " evidence, the limit sentence", self.skill)

    def test_no_migration_required_lists_minor_findings_and_the_humans_option(self):   # D-F2
        self.assertIn("every finding judged Minor with its one-line reason", self.skill)
        self.assertIn("may still ask for a migration", self.skill)

    def test_secret_key_names_only_through_the_shown_form_never_an_ad_hoc_command(self):   # D-F3
        self.assertIn("are read for their key names only, never their values", self.skill)
        self.assertIn("can print nothing but the names", self.skill)
        self.assertIn("never through an ad-hoc command of your own", self.skill)


if __name__ == "__main__":
    unittest.main()
