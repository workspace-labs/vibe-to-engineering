"""Guards for the C documentation corrections (the frozen wording rules of the release decisions §3.7 and
the owner decision of 2026-09-30 on required checks): checkpoints promise their defined saved-file set,
never "the whole project"; fingerprint and checkpoint comparisons state their limit wherever they stand as
data-safety evidence; no text suggests editing a real .env so the tool accepts a project; the required-check
rule, the three outcomes and the VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED MANUAL CHECKS outcome are
present; the platform wording is macOS-only with Linux and Windows on the roadmap; no personal paths remain
in the skill folder. They guard the wording, not an agent's behavior — the convention of test_protocol.py.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = Path(os.environ.get("V2E_SKILL_DIR", ROOT / "skills" / "vibe-to-engineering"))  # seam: another copy
SKILL = Path(os.environ.get("V2E_SKILL_MD", SKILL_DIR / "SKILL.md"))
README = ROOT / "README.md"

TEXT_SUFFIXES = (".md", ".py", ".html", ".yaml", ".txt")


def skill_texts():
    """(path, text) for every user- or agent-facing text file in the skill folder."""
    for path in sorted(SKILL_DIR.rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path, path.read_text(encoding="utf-8")


class CWording(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.readme = README.read_text(encoding="utf-8")
        self.template = (SKILL_DIR / "assets" / "plan-template.html").read_text(encoding="utf-8")
        self.plan = (SKILL_DIR / "references" / "migration-plan.md").read_text(encoding="utf-8")
        self.env_boundary = (SKILL_DIR / "references" / "env-boundary.md").read_text(encoding="utf-8")
        self.acceptance = (SKILL_DIR / "references" / "stage1-acceptance.md").read_text(encoding="utf-8")
        self.registry = (SKILL_DIR / "references" / "supported-checks.md").read_text(encoding="utf-8")
        self.recovery = (SKILL_DIR / "references" / "recovery.md").read_text(encoding="utf-8")

    def test_checkpoints_promise_their_defined_saved_file_set_never_the_whole_project(self):
        for path, text in skill_texts():
            self.assertNotIn("whole project", text.lower(), path)
        self.assertNotIn("whole project", self.readme.lower())
        for words in ("every file git would not ignore", "watched, not saved",
                      "nested repositories are not saved"):
            self.assertIn(words, self.readme)
            self.assertIn(words, self.template)
        self.assertIn("save the project's defined saved-file set as a checkpoint", self.skill)
        self.assertIn("keeps its saved-file set", self.recovery)   # D1 spot 3
        self.assertNotIn("keeps everything", self.recovery)

    def test_fingerprint_and_checkpoint_comparisons_state_their_limit(self):
        for words in ("do not prove the absence of reads, remote writes or temporary changes",
                      "a file changed and changed back between two checkpoints looks unchanged"):
            self.assertIn(words, self.skill)
        self.assertIn("changed and changed back", self.readme)
        self.assertIn("changed and changed back", self.template)
        self.assertIn("does not prove the absence of reads, remote writes or temporary changes: a file"
                      " changed and changed back between two checkpoints looks unchanged",
                      self.recovery)   # D1 spot 4 (G10)

    def test_no_text_suggests_editing_a_real_env_to_gain_admission(self):
        forbidden = ("edit the .env", "edit your .env", "edit .env", "editing the .env",
                     "rewrite the .env", "rewrite your .env", "rewriting the .env",
                     "convert the .env", "convert your .env", "converting the .env",
                     "fix the .env", "fix your .env", "change the .env", "change your .env",
                     "simplify the .env", "simplify your .env", "make the tool accept")
        for path, text in skill_texts():
            for phrase in forbidden:
                self.assertNotIn(phrase, text.lower(), "%s in %s" % (phrase, path))
        for phrase in forbidden:
            self.assertNotIn(phrase, self.readme.lower(), phrase)
        for words in ("never edited, rewritten or converted",
                      "keep the file outside the project for the migration"):
            self.assertIn(words, self.env_boundary)
        self.assertIn("`--env` points it at throwaway data", self.skill)

    def test_required_check_rule_three_outcomes_and_the_manual_checks_outcome(self):
        for words in ("a passing check needs a matching wrapper 0 and child exit 0",
                      "a required check counts as passed only with that passing recorded evidence",
                      "exactly **three outcomes**",
                      "(a) a plan revision",
                      "(b) an owner-approved **manual alternative**",
                      "(c) a blocking finding",
                      "never silently skipped",
                      "MANUAL — OUTSIDE THE MASKING GUARANTEE",
                      "`VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED MANUAL CHECKS`",
                      "Manual: <check> — passed (reported by the human, <date>) — ran outside"
                      " the secret-masking guarantee (its output was not masked by the tool)",
                      "Never shorten either block to ALL GREEN"):
            self.assertIn(words, self.skill)
        self.assertGreaterEqual(self.skill.count("COMPLETE WITH APPROVED MANUAL CHECKS"), 4)
        self.assertIn("MANUAL — OUTSIDE THE MASKING GUARANTEE", self.plan)
        self.assertIn("outside the tool's secret-masking guarantee", self.readme)
        for words in ("requires every manual check to be reported PASSED",   # M1
                      "A manual check reported FAILED is a failing check like any other",
                      "in a phase the phase fails (section 8)",
                      "the human's own approving words and the reported result"):
            self.assertIn(words, self.skill)
        self.assertNotIn("Manual: <check> — ran outside", self.skill)
        self.assertIn("A manual check reported FAILED is a failing check like any other", self.plan)
        self.assertIn("the human's approving words and the reported result", self.plan)

    def test_no_personal_paths_in_the_skill_folder(self):
        for path, text in skill_texts():
            self.assertNotIn("~/Desktop", text, path)
            self.assertNotIn("/Users/", text, path)

    def test_platform_wording_is_macos_only_with_linux_and_windows_on_the_roadmap(self):
        checkpoint = (SKILL_DIR / "scripts" / "checkpoint.py").read_text(encoding="utf-8")
        evidence = (SKILL_DIR / "scripts" / "evidence.py").read_text(encoding="utf-8")
        render_pdf = (SKILL_DIR / "scripts" / "render_pdf.py").read_text(encoding="utf-8")
        self.assertNotIn("runs on macOS, Linux and Windows", checkpoint)
        self.assertIn("runs on macOS only", checkpoint)
        self.assertNotIn("py -3", evidence)
        self.assertNotIn("removed when", evidence)
        self.assertNotIn("py -3", render_pdf)
        self.assertNotIn("Supported and validated", self.readme)
        self.assertIn("release exam pending", self.readme)
        self.assertNotIn("run on every platform", self.recovery)   # D1 spot 1
        self.assertIn("runs on macOS only", self.recovery)
        self.assertNotIn("macOS — validated in 0.1.0", self.recovery)   # D1 spot 2
        self.assertIn("macOS — supported in 0.1.0 (all tests pass; release exam pending)", self.recovery)

    def test_runner_examples_and_stage1_platform_notes_read_as_roadmap(self):
        for text in (self.skill, self.registry):
            self.assertIn("sh <project-script>", text)
            self.assertNotIn("sh scripts/test.sh", text)
        for words in ("design investigation, not a support claim",
                      "roadmap; this release refuses to run there"):
            self.assertIn(words, self.acceptance)
        self.assertNotIn("**Linux** — no pin required.", self.acceptance)


if __name__ == "__main__":
    unittest.main()
