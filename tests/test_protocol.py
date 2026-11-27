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

    def test_plan_only_confirmation_and_enrollment_at_every_entry_point(self):
        resume = self.text.split("2. **Resume", 1)[1].split("**Conventions.", 1)[0]
        backup = self.text.split("## 6. CREATE + VERIFY BACKUP", 1)[1].split("Before step 1", 1)[0]
        approval = self.text.split("Give the owner a concrete next reply", 1)[1].split("## 6.", 1)[0]
        reference = (SKILL_DIR / "references" / "standard-alignment.md").read_text()
        for name, instructions in (("README", (ROOT / "README.md").read_text()),
                                   ("standard router", reference), ("plan guide", self.plan),
                                   ("resume", resume), ("baseline", backup)):
            with self.subTest(entry=name):
                for word in ("disposable", "synthetic", "approval", "runner enrollment", "separate"):
                    self.assertIn(word, instructions.lower())
        for section in (approval, self.template.split("What your approval authorizes", 1)[1].split("</p>", 2)[1],
                        self.template.split('id="approval"', 1)[1]):
            self.assertIn("synthetic", section)
            self.assertIn("disposable", section)
        self.assertIn("check-approval", backup)
        self.assertIn("check-approval", self.text.split("## 7. PHASE n", 1)[1].split("Add `PHASE", 1)[0])
        self.assertIn("display-only failure", self.text)
        self.assertIn("fingerprint stops backup", self.text)

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

    def test_each_proposed_abstraction_earns_its_keep_and_is_recorded(self):
        standard = (SKILL_DIR / "references" / "engineering-standard.md").read_text(encoding="utf-8")
        criterion = standard.split("### C16 Overengineering risk", 1)[1].split("\n## ", 1)[0]
        for words in ("**Ownership or dependency direction:**", "**One shared rule:**",
                      "**Outside boundary:**", "**Testing:**", "**Change isolation:**", "**Platform split:**",
                      "the simplest design that solves that cost needs it", "An outside call alone is not enough",
                      "A future need is not a reason by itself"):
            self.assertIn(words, criterion)

        problem = criterion.split("- **Problem evidence in the current project:**", 1)[1].split("\n- ", 1)[0]
        self.assertIn("none of the reasons above shown", problem)
        self.assertNotIn("no boundary or testing reason", problem)

        design = self.text.split("## 3. DESIGN TARGET ARCHITECTURE (read-only)", 1)[1].split("\n## ", 1)[0]
        for words in ("however small", "the C16 reason it meets", "the concrete evidence",
                      "why the simpler alternative falls short"):
            self.assertIn(words, design)

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

    def test_checks_use_throwaway_data_and_prove_which_server_answered(self):   # RA-04, RA-05
        for words in ("**Checks use throwaway data:**", "a check that cannot be redirected is not run",
                      "where the application reads and writes data"):
            self.assertIn(words, self.text)
        for words in ("**Checks use throwaway data, never the owner's.**",
                      "A check that would touch the owner's data is refused at the plan stage",
                      "**A check that starts a server**", "bind to port 0", "answering instead is a failure, never a pass",
                      "stops its process and confirms it is gone", "records the port, the process id and the start-up log"):
            self.assertIn(words, self.plan)
        for words in ("<th>Data it uses</th>", "{{CHECK_DATA}}"):
            self.assertIn(words, self.template)

    def test_secret_values_are_never_read_or_written(self):   # RA-06
        standard = (SKILL_DIR / "references" / "engineering-standard.md").read_text(encoding="utf-8")
        for words in ("are read for their key names only, never their values", "**Secrets:** no secret value goes into",
                      "Every check runs through `<skill>/scripts/evidence.py`, never on its own"):
            self.assertIn(words, self.text)
        for words in ("for their key names only, never their values", "by file, line and key name, never its value"):
            self.assertIn(words, standard)

    def test_a_changed_ignored_file_is_a_break_like_a_gone_one(self):   # RA-03
        for words in ("no ignored file `changed`", "A changed ignored file is a break like a gone one",
                      "reports none `gone` or `changed`", "ignored files it reports `changed` included"):
            self.assertIn(words, self.text)

    def test_inspection_and_baseline_use_guarded_git_reads(self):
        inspect = self.text.split("## 1. INSPECT (read-only)")[1].split("\n## ")[0]
        baseline = self.text.split("## 6. CREATE + VERIFY BACKUP")[1].split("\n## ")[0]
        for words in ("checkpoint.py tree --current", "checkpoint.is_git_project(project)",
                      "nested.refuse_partial_clone", "gitrun.git", "committed objects",
                      "--no-ext-diff --no-textconv --no-show-signature",
                      "Never run direct `git status` or a Git diff against the working tree"):
            self.assertIn(words, inspect)
        self.assertIn("guarded committed-object reads in INSPECT", baseline)
        self.assertIn("uncommitted-change count: not safely established", baseline)
        self.assertNotIn("git --no-optional-locks", inspect + baseline)

    def test_runner_enrollment_requires_human_typed_approval(self):
        gates = self.text.split("## Human gates", 1)[1].split("\n## ", 1)[0]
        checks = (SKILL_DIR / "references" / "supported-checks.md").read_text(encoding="utf-8")
        self.assertIn("| Enrollment |", gates)
        approval = "not typed, not piped, not through stdin by any means"
        self.assertIn(approval, self.text)
        self.assertIn(approval, checks)

    def test_no_migration_verdict_keeps_the_human_option_open(self):
        verdict = next((line for line in self.text.splitlines() if line.startswith("- **No migration justified:**")), "")
        self.assertIn("every finding judged Minor with its one-line reason", verdict)
        self.assertIn("may still ask for a migration", verdict)
        standard = (SKILL_DIR / "references" / "engineering-standard.md").read_text(encoding="utf-8")
        severity = standard.split("\n## 4. ", 1)[1].split("\n## ", 1)[0]
        self.assertIn("not acted on unless the human asks", severity)

    def test_checkpoint_comparisons_report_their_limits(self):
        limit = "does not prove the absence of reads, remote writes or temporary changes"
        restored = self.text.split("```\nRESTORED <label>\n", 1)[1].split("\n```", 1)[0]
        self.assertIn(f"Limit: the comparison covers local file states; it {limit}", restored.splitlines())
        report = self.text.partition("\nFollow the outcome with")[2].split("\n\n", 1)[0]
        self.assertIn(limit, report)

    def test_refused_real_env_stays_outside_the_migration(self):
        boundary = (SKILL_DIR / "references" / "env-boundary.md").read_text(encoding="utf-8")
        self.assertIn("never edited, rewritten or converted to get it admitted", boundary)
        self.assertIn("throwaway data with `--env`", boundary)

    def test_approval_without_disposable_confirmation_stays_plan_only(self):
        status = self.text.split("**Development status", 1)[1].split("\n\n", 1)[0]
        for text in ("INSPECT, DIAGNOSE and DESIGN", "real project",
                     "plan HTML, PDF and ledger", "disposable projects with synthetic secrets"):
            self.assertIn(text, status)
        gate = self.text.split("## 5. GENERATE PDF, then stop", 1)[1].split("\n## 6.", 1)[0]
        self.assertIn("explicit statement that this project is disposable", gate)
        self.assertIn("Approving a plan is not that statement.", gate)
        self.assertIn("`PLAN ONLY`", gate)
        self.assertIn("record the approval, make the map", gate)
        self.assertIn("the human explicitly confirmed this project is disposable", self.text)

    def test_approval_explains_checkpoint_limits_and_work_guarantees(self):
        cover = self.template.split('class="authorize">', 1)[1].split("</div>", 1)[0]
        cover = " ".join(cover.split())
        self.assertIn(
            "Ignored files and nested repositories are outside checkpoint recovery; "
            "checkpoints are not a comprehensive backup of secrets or user data. "
            "These protected files stay untouched.",
            cover,
        )
        self.assertIn(
            "Every later phase waits for its own approval. The product's behavior stays the same, "
            "nothing is committed or published, and nothing is deleted without a saved copy.",
            cover,
        )
        self.assertNotIn("Checkpoint recovery covers the files named in the plan.", cover)

    def test_owner_sees_measured_totals_and_file_evidence_before_approval(self):
        summary = self.template.split('id="summary">', 1)[1].split("</section>", 1)[0]
        for field in ("TOTAL_FILES", "TOTAL_LINES", "LARGEST_FILE"):
            for state in ("BEFORE", "AFTER"):
                self.assertIn("{{%s_%s}}" % (field, state), summary)
        self.assertIn("Before (measured)", summary)
        self.assertIn("After (estimated)", summary)
        files = self.template.split('<section class="sheet" id="files">', 1)[1].split("</section>", 1)[0]
        self.assertIn('<td class="num">{{FILE_LINES_NOW}}</td><td class="num">{{FILE_LINES_AFTER}}</td>', files)
        evidence = files.split("Why each new file exists", 1)[1].split("Who owns each job", 1)[0]
        for field in ("NEW_FILE_PATH", "NEW_FILE_OLD_LINES", "NEW_FILE_FINDING",
                      "NEW_FILE_WHY", "NEW_FILE_EVIDENCE_STATE"):
            self.assertIn("{{%s}}" % field, evidence)
        for text in ("exact line ranges", "finding ID", "`not yet exact`", "before the split"):
            self.assertIn(text, self.plan)

    def test_map_uses_approval_and_ledger_and_preserves_the_protocol_gate(self):
        rule = self.text.split("## The migration map\n", 1)[1].split("\n## ", 1)[0]
        rule = " ".join(rule.split())
        for text in ("## <UTC time> — PLAN APPROVED v<version> — <state>",
                     "migration-map.json", "render_map.py --project <project>",
                     "Migration-Map.html", "Migration-Map.pdf", "git hash-object --no-filters",
                     "PHASE n STARTED", "PHASE n COMPLETE", "PHASE n FAILED",
                     "RESTORED <label>", "MIGRATION STOPPED", "Map: NOT UPDATED — <reason>",
                     "The ledger governs", "never counts as approval", "continue to the protocol's own gate"):
            self.assertIn(text, rule)
        backup = self.text.split("## 6. CREATE + VERIFY BACKUP", 1)[1].split("\n## ", 1)[0]
        self.assertIn("The migration map", backup)
        phase = self.text.split("## 7. PHASE n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("The migration map", phase)


if __name__ == "__main__":
    unittest.main()
