"""Portable integrity checks for the offline engineering-standard snapshot.

These checks validate package provenance, completeness and discoverability. They do
not claim that an agent obeys an approval gate; that needs a separate workflow exam.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "vibe-to-engineering"
BUNDLE = SKILL / "references" / "build-standard"
COMMIT = "d671ceb987084da7bc0103666bc12fc3d29e6758"
VERSION = "1.9.0"
REPOSITORY = "https://github.com/workspace-labs/software-engineering-build-standard"
UPSTREAM_SKILL = "skills/software-engineering-build-standard/"
GUIDES = {
    "architecture-and-boundaries.md", "backend.md", "coverage-and-evidence.md",
    "data-state-and-runtime.md", "frontend.md", "layout-map.md",
    "platform-services.md", "repository-and-delivery.md", "review-and-completion.md",
    "team-and-lifecycle.md",
}
TREES = {
    "ai-service.md", "api-backend.md", "cli-tool.md", "data-pipeline.md",
    "desktop-app.md", "library.md", "mobile-app.md", "monorepo.md",
    "webapp.md", "website.md",
}
EXPECTED_FILES = ({"standard.md", "LICENSE"}
                  | {"references/" + name for name in GUIDES}
                  | {"references/trees/" + name for name in TREES | {"README.md"}})
LINK = re.compile(r"\[[^\]\n]+\]\(([^)\n]+)\)")
# SHA-256 of each governed passage (StandardAlignment.governed_blocks).
LOCKS = {
    "plan: old or partial proof": "6ef949872b4584e7db1911c6e69339503f4bc6d526615924763a0122b3c80481",
    "skill: restored report": "a7a824eb64b07d0f5087511e4f3addea4f4b07779bd91fbf09caf7f7081a5cd7",
    "skill: baseline failure of a covering check": "4dcf4808c5b2b6cecddc68820f13e2bdeb5275e8b1ff9afc44ee09d47faeeaea",
    "form: every-file rows": "3c46c5c70ebe418fa6e5745681b01bc47fc424da30b97492ca65c176d8e0163a",
    "form: check rows": "31b603a9cbef514d2ea79073665925653d7869bf1ee47d72ec2e904c6a8e6ec6",
    "plan: review candidates": "73b458fbf9e34fc452866f03b5c8e536fbf103e84b78815cf5230f128b53aba7",
    "skill: resume": "f5490b6e19ce551bcdeed5622908343098b3f3c7b5bbf9ca866864eb0382c94f",
    "skill: status lines": "84ebd5d68a2f82e7313c97f5b903f1a4dc4b41b6cb286218eacf70d6566ae93c",
    "skill: before -> after rows": "36a689dfe88158620049072fff6e16168887d8842760be25b0ec5333d58463bf",
    "skill: plan gate": "5fcbefffe4949532c41f3a472ddd993df3f318741175dc84779cc93556b02d16",
    "skill: baseline gate": "eab6ded76fd87ca94ea6d27dd9dc24ef6260901c1faeb36b997bdaa54a5da4f7",
    "skill: phase precondition": "ad8bd95e15afff0835fc56401d8ece38f8f2581b25e54947c3deca2c3a1d7ff3",
    "skill: phase report": "12a2233f5273a52d3f32468faa72f9d26d9541254e9aed6df876c37bb85042bb",
    "skill: failed report": "50fee596680331e9bed0d0e52fbc931d921046a1087df6b72cd6b605f5721ba2",
    "skill: final review": "0af62ff7e3ca3fc3d21ece589657f33ce8be7cf1b40661a2b232b61060c72690",
    "skill: evidence rule": "e085f5bfd7f0c8cb0dda53295ca914ee98497fa4cb58bc0a67662b333ead33a6",
    "criteria: C12": "d9ebb49ae1525979e80fc9045b638801b6e9e8d447e28eb2bcd1ca79ff03c58f",
    "criteria: C16": "e2e73d3b4c1983ff0b8e48bd75211af6d72f510849e6e080892c4bf97ac7a74a",
    "router: file size": "1c09c42bb4ab293b9ff562645810a94d4ffe539fe1055804dd0fa28dab86c2da",
    "router: maintenance": "1b97c9ae23eed84a542733b179084cd2c025e6ee85343ebd0bb5fc242043667f",
}


class StandardAlignment(unittest.TestCase):
    def manifest(self):
        path = BUNDLE / "source.json"
        self.assertTrue(path.is_file(), "the offline standard snapshot manifest is missing")
        for directory in (SKILL / "references", BUNDLE):
            self.assertFalse(directory.is_symlink(), "a snapshot directory must not be a symlink")
        self.assertFalse(path.is_symlink(), "the snapshot manifest must not be a symlink")
        self.assertIn(SKILL.resolve(), BUNDLE.resolve().parents)
        return json.loads(path.read_text(encoding="utf-8"))

    def local_links(self, source):
        """Check real Markdown targets component by component, even on a case-folding disk."""
        targets = set()
        text = source.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            address = raw.strip().strip("<>")
            parsed = urlsplit(address)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            relative = unquote(parsed.path)
            self.assertNotIn("\\", relative, str(source))
            self.assertFalse(PurePosixPath(relative).is_absolute(), str(source))
            candidate = source.parent
            for part in PurePosixPath(relative).parts:
                if part == "..":
                    candidate = candidate.parent
                elif part != ".":
                    self.assertTrue(candidate.is_dir(), "%s: missing parent for %s" % (source, raw))
                    self.assertIn(part, {p.name for p in candidate.iterdir()},
                                  "%s: missing or incorrectly capitalized link %s" % (source, raw))
                    candidate = candidate / part
                self.assertFalse(candidate.is_symlink(), "%s: linked target %s" % (source, raw))
                self.assertTrue(candidate.resolve() == SKILL.resolve()
                                or SKILL.resolve() in candidate.resolve().parents,
                                "%s: link escapes the installable skill: %s" % (source, raw))
            targets.add(candidate.resolve())
            if parsed.fragment and candidate.suffix == ".md":
                self.assertIn(unquote(parsed.fragment), self.anchors(candidate),
                              "%s: no such heading for %s" % (source, raw))
        return targets

    def anchors(self, document):
        """GitHub-style anchors of a Markdown document's headings (fenced examples excluded)."""
        found, fenced = set(), False
        for line in document.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                fenced = not fenced
            match = None if fenced else re.match(r"#{1,6} +(.*?)\s*$", line)
            if match:
                slug = re.sub(r"[^\w\- ]", "", match.group(1).lower()).replace(" ", "-")
                found.add(slug)
        return found

    def test_snapshot_records_the_known_upstream_revision_and_version(self):
        manifest = self.manifest()
        self.assertEqual(manifest["schemaVersion"], 2)
        self.assertEqual(manifest["repository"], REPOSITORY)
        self.assertEqual(manifest["commit"], COMMIT)
        self.assertEqual(manifest["version"], VERSION)
        text = (BUNDLE / "standard.md").read_text(encoding="utf-8")
        versions = re.findall(r"(?m)^Standard version: (\d+\.\d+\.\d+)$", text)
        self.assertEqual(versions, [manifest["version"]])

    def test_manifest_accounts_for_every_bundled_file_and_all_project_families(self):
        manifest = self.manifest()
        self.assertEqual(set(manifest["files"]), EXPECTED_FILES)
        actual = set()
        for path in BUNDLE.rglob("*"):
            self.assertFalse(path.is_symlink(), "a bundled reference must not be a symlink: %s" % path)
            self.assertTrue(path.is_dir() or path.is_file(), "nonregular bundled resource: %s" % path)
            if path.is_file():
                actual.add(path.relative_to(BUNDLE).as_posix())
        self.assertEqual(actual, EXPECTED_FILES | {"source.json"})

    def test_snapshot_bytes_match_the_manifest_and_source_paths(self):
        for relative, entry in self.manifest()["files"].items():
            with self.subTest(file=relative):
                path = PurePosixPath(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertNotIn("\\", relative)
                self.assertEqual(path.as_posix(), relative)
                destination = BUNDLE / relative
                self.assertTrue(destination.is_file(), relative)
                self.assertFalse(destination.is_symlink(), relative)
                self.assertIn(BUNDLE.resolve(), destination.resolve().parents)
                upstream = ("LICENSE" if relative == "LICENSE" else UPSTREAM_SKILL
                            + ("SKILL.md" if relative == "standard.md" else relative))
                self.assertEqual(entry["upstream_path"], upstream)
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
                data = destination.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
                # Provenance: undoing the one recorded link rewrite gives the upstream bytes back.
                rewrite = self.manifest()["link_rewrite"]
                self.assertEqual((rewrite["from"], rewrite["to"]), ("](../SKILL.md", "](../standard.md"))
                self.assertNotIn(rewrite["from"].encode(), data, "a bundled link to a missing SKILL.md")
                if "upstream_sha256" in entry:
                    self.assertRegex(relative, r"^references/[^/]+\.md$")
                    self.assertIn(rewrite["to"].encode(), data)
                    upstream_bytes = data.replace(rewrite["to"].encode(), rewrite["from"].encode())
                    self.assertEqual(hashlib.sha256(upstream_bytes).hexdigest(), entry["upstream_sha256"])
                    self.assertNotEqual(entry["upstream_sha256"], entry["sha256"])
                else:
                    self.assertNotIn(rewrite["to"].encode(), data, "an unrecorded rewrite")

    def test_the_snapshot_is_self_contained_with_case_correct_markdown_links(self):
        self.manifest()
        for source in sorted(BUNDLE.rglob("*.md")):
            with self.subTest(source=source.relative_to(BUNDLE)):
                self.local_links(source)

    def test_alignment_router_exposes_the_standard_layout_and_tree_chooser(self):
        source = SKILL / "references" / "standard-alignment.md"
        self.assertTrue(source.is_file(), "the migration-to-standard routing reference is missing")
        targets = self.local_links(source)
        for relative in ("standard.md", "references/layout-map.md", "references/trees/README.md"):
            self.assertIn((BUNDLE / relative).resolve(), targets,
                          "the alignment router must link the installable offline reference: " + relative)

    def test_the_snapshot_cannot_be_discovered_as_a_second_agent_skill(self):
        self.assertEqual(list(SKILL.rglob("SKILL.md")), [SKILL / "SKILL.md"])
        self.assertFalse(any(BUNDLE.rglob("openai.yaml")), "do not bundle a second skill's UI metadata")

    def test_plan_form_records_its_standard_and_project_specific_choices(self):
        template = (SKILL / "assets" / "plan-template.html").read_text(encoding="utf-8")
        for field in ("STANDARD_VERSION", "STANDARD_COMMIT", "PROJECT_TYPE", "TREE_GUIDES",
                      "STANDARD_DECISIONS", "PROJECT_RULES"):
            with self.subTest(field=field):
                self.assertTrue("{{" + field + "}}" in template, "missing plan form field: " + field)
        # The filled form must identify the approved plan independently of the standard version.
        self.assertIn("{{PLAN_VERSION}}", template)

    def own_instructions(self):
        """This skill's own instruction text, the bundled standard excluded."""
        files = [SKILL / "SKILL.md", SKILL / "assets" / "plan-template.html"]
        files += sorted((SKILL / "references").glob("*.md"))
        return {path.relative_to(SKILL).as_posix(): path.read_text(encoding="utf-8") for path in files}

    def bundled_alarms(self):
        guide = (BUNDLE / "references" / "architecture-and-boundaries.md").read_text(encoding="utf-8")
        section = re.search(r"(?ms)^## §7 Prevent God files\n(.*?)(?=^## )", guide).group(1)
        self.assertIn("### File-size alarms", section, "the bundled §7 must carry the alarms")
        review = re.search(r"(?m)^\| (\d+) to \d+ lines \| Review \|", section)
        reason = re.search(r"(?m)^\| Over ([\d,]+) lines \| Written reason \|", section)
        self.assertTrue(review and reason, "the bundled §7 needs its review and written-reason rows")
        return review.group(1), reason.group(1)

    def governed_blocks(self):
        """The passages whose exact wording carries the size and warning rules."""
        own = self.own_instructions()
        skill, plan = own["SKILL.md"], own["references/migration-plan.md"]

        def between(text, start, end):
            self.assertEqual(text.count(start), 1, "governed passage missing or repeated: " + start)
            begin = text.index(start)
            return text[begin:text.index(end, begin)]

        return {
            "plan: old or partial proof": between(plan, "**Warn when the proof is old", "**Thin safety net?**"),
            "plan: review candidates": between(plan, "**Review candidates:**", "\n"),
            "skill: resume": between(skill, "2. **Resume if a migration exists.**", "\n"),
            "skill: status lines": between(skill, "## Status lines", "\n## "),
            "skill: before -> after rows": between(skill, "Produce the CURRENT TREE", "\n"),
            "skill: plan gate": between(skill, "Define the checks that prove the application still works", "\n"),
            "skill: baseline gate": between(skill, "Before step 1, the ledger holds", "\n"),
            "skill: phase precondition": between(skill, "- no open `VERIFICATION WARNING`", "\n"),
            "skill: phase report": between(skill, "While any verification warning is open or accepted", "\n"),
            "skill: failed report": between(skill, "Open and accepted verification warnings appear", "\n"),
            "skill: restored report": between(skill, "Verification warnings that are still open or accepted", "\n"),
            "skill: baseline failure of a covering check": between(
                skill, "When a failing check is the covering check of a verification warning", "\n"),
            "form: every-file rows": between(own["assets/plan-template.html"],
                                             "<!-- repeat: one row per file, grouped by folder.", "<!-- /repeat -->"),
            "form: check rows": between(own["assets/plan-template.html"],
                                        "<!-- repeat: one row per check", "<!-- /repeat -->"),
            "skill: final review": between(skill, "6. Verification warnings come before the final checkpoint",
                                           "Follow the outcome with"),
            "skill: evidence rule": between(skill, "- **Evidence:** every PASS rests", "\n"),
            "criteria: C12": between(own["references/engineering-standard.md"],
                                     "### C12 Oversized multi-responsibility modules", "\n### "),
            "criteria: C16": between(own["references/engineering-standard.md"],
                                     "### C16 Overengineering risk", "\n## "),
            "router: file size": between(own["references/standard-alignment.md"],
                                         "## File size has one home", "\n## "),
            "router: maintenance": between(own["references/standard-alignment.md"],
                                           "## Maintaining this bundle", "A migration already approved"),
        }

    def test_governed_wording_changes_only_on_purpose(self):
        """A reversal that keeps the listed phrases still changes these bytes.

        After a deliberate, reviewed change to a passage, replace its fingerprint here.
        """
        for name, text in self.governed_blocks().items():
            with self.subTest(passage=name):
                self.assertEqual(hashlib.sha256(text.encode("utf-8")).hexdigest(), LOCKS.get(name),
                                 "governed wording changed: review it, then update LOCKS")
        self.assertEqual(set(LOCKS), set(self.governed_blocks()))

    def test_file_size_numbers_live_only_in_the_bundled_standard(self):
        alarms = set(self.bundled_alarms())
        cited, lines_with_numbers = set(), {}
        for name, text in self.own_instructions().items():
            for line in text.splitlines():
                # Any spelling: 400, 1,000, 1000, 1 000, 1k — followed by "line(s)" or "LOC".
                found = re.findall(r"(?i)(?<![\d,.])(\d{1,3}(?:[, ]\d{3})+|\d{3,}|\d+k)[ -]?(?:lines?|loc)\b", line)
                for number in found:
                    with self.subTest(file=name, number=number):
                        self.assertIn(number, alarms, "a file-size number the standard does not define")
                        # The plan form's comment sits under the section that states the rule.
                        if not name.endswith(".html"):
                            self.assertIn("§7", line, "a file-size number must point to §7")
                        cited.add(number)
                if found:
                    lines_with_numbers[name] = lines_with_numbers.get(name, 0) + 1
        self.assertEqual(cited, alarms, "the report rule uses the standard's two alarms")
        # One sentence each, all inside governed passages: no second, independent size rule.
        self.assertEqual(lines_with_numbers, {"SKILL.md": 1, "references/migration-plan.md": 1,
                                              "assets/plan-template.html": 1})
        criteria = self.own_instructions()["references/engineering-standard.md"]
        self.assertIn("this skill keeps no file-size number of its own", criteria)
        self.assertIn("build-standard/references/architecture-and-boundaries.md", criteria)

    def test_report_marks_review_candidates_and_size_alone_is_still_not_a_finding(self):
        review, _ = self.bundled_alarms()
        own = self.own_instructions()
        plan = own["references/migration-plan.md"]
        rule = next(line for line in plan.splitlines() if "**Review candidates:**" in line)
        self.assertIn("**Every file: before → after**", rule, "the mark belongs to the before → after table")
        for words in ("estimated at over %s lines" % review, "`review candidate (~N lines)`",
                      "list its jobs", "File size alone is not a finding",
                      "every file the plan creates, moves, renames, edits, merges or splits",
                      "a file moved intact and an edit that leaves the length unchanged included",
                      '"over" means 401 or more', "over 1,000 lines (1,001 or more)",
                      "carries the written reason §7 asks for", "or is split by responsibility",
                      "a review candidate with one job stays whole"):
            with self.subTest(words=words):
                self.assertIn(words, rule)
        self.assertIn("estimated at over %s lines as a review candidate and list its jobs" % review,
                      own["SKILL.md"])
        # In the form, the instruction sits in the every-file table and nowhere else.
        form = own["assets/plan-template.html"]
        files = form.split('<section class="sheet" id="files">')[1].split("</section>")[0]
        self.assertEqual(form.count("review candidate"), 1)
        self.assertIn('A proposed file estimated at over %s lines: begin Holds after with '
                      '"review candidate (~N lines)" and list its jobs. -->\n'
                      '      <tr><td class="path">{{FILE_PATH}}</td>' % review, files)
        self.assertNotRegex(form, r"(?i)\bsplit any\b|\bmust be split\b|\balways split\b")
        criteria = own["references/engineering-standard.md"]
        self.assertIn("Size alone is never a finding.", criteria)
        never = criteria.split("## 6. What is never a finding")[1].split("\n## ")[0]
        self.assertIn("- File size alone.", never)

    def test_old_or_partial_verification_results_get_a_warning(self):
        own = self.own_instructions()
        plan = own["references/migration-plan.md"]
        section = plan.split("## 3. Verification: proving behavior is preserved")[1].split("\n## ")[0]
        for words in ("- **Old:**", "- **Does not cover:**",
                      "a page reload but never with a full restart",
                      "`VERIFICATION WARNING — <what is old or not covered> — <what the plan changes there> — "
                      "<the check that would close it>`",
                      "not a failure and never a pass", "never called verified",
                      "The human decides"):
            with self.subTest(words=words):
                self.assertIn(words, section)
        skill = own["SKILL.md"]
        planning = skill.split("## 4. CREATE MIGRATION PLAN")[1].split("\n## ")[0]
        self.assertIn("`VERIFICATION WARNING`", planning)
        always = skill.split("\n## Always")[1]
        self.assertIn("is a `VERIFICATION WARNING`, never a PASS", always)
        # In the form, the warning rows belong to the checks table of "Verification and recovery".
        form = own["assets/plan-template.html"]
        self.assertEqual(form.count("VERIFICATION WARNING"), 1)
        heading = form.index("</span>Verification and recovery</h2>")
        checks = form[heading:form.index("</table>", heading)]
        self.assertIn("Add one row per VERIFICATION WARNING: what is old or not covered, and the check "
                      "that would close it. -->\n        <tr><td>{{CHECK_NAME}}</td>", checks)

    def test_a_warning_stays_visible_in_every_report_and_an_accepted_gap_is_never_all_green(self):
        own = self.own_instructions()
        plan = own["references/migration-plan.md"]
        section = plan.split("## 3. Verification: proving behavior is preserved")[1].split("\n## ")[0]
        for words in ("- **Open** —", "- **Closed** —", "- **Accepted** —",
                      "planning stays read-only and runs nothing to close them",
                      "An approval that does not answer an open warning does not accept its gap",
                      "No phase that changes the behavior a warning names starts while it is open",
                      "Only that fresh run closes a warning",
                      "acceptance is permission to continue, never a pass",
                      "Before presenting the plan, and again in every phase report and the final review",
                      "Run the check again where this stage allows it; otherwise warn.",
                      "it stands in the plan's summary and its Verification and recovery section and in every report",
                      "Authorizing a check never accepts the gap, and accepting the gap never authorizes a check.",
                      "Every phase report, a failed one and a `RESTORED` report included, carries one "
                      "`Verification Warning` line "
                      "per open or accepted warning",
                      "`COMPLETE WITH APPROVED BASELINE FAILURES` with its `Not verified` lines — never as ALL GREEN"):
            with self.subTest(words=words):
                self.assertIn(words, section)
        skill = own["SKILL.md"]
        phase = skill.split("## 7. PHASE n")[1].split("\n## ")[0]
        for words in ("no open `VERIFICATION WARNING` names behavior this phase changes",
                      "`Verification Warning: OPEN — <what is not covered>`",
                      "`Verification Warning: ACCEPTED BY OWNER — <what is not covered>`",
                      "Passing checks never remove such a line"):
            with self.subTest(words=words):
                self.assertIn(words, phase)
        final = skill.split("## 9. FINAL REVIEW")[1].split("\n## ")[0]
        for words in ("ALL GREEN also needs every verification warning closed by a fresh run of its check",
                      "An open warning gets no outcome",
                      "VIBE-TO-ENGINEERING — COMPLETE WITH ACCEPTED VERIFICATION GAPS\n"
                      "Not verified (accepted by the owner): <behavior> — <the check that would close it>",
                      "An accepted gap is never ALL GREEN, however many checks pass."):
            with self.subTest(words=words):
                self.assertIn(words, final)
        self.assertIn("Approving the plan does not accept an open warning unless the human's approval says so",
                      skill.split("## 4. CREATE MIGRATION PLAN")[1].split("\n## ")[0])
        # The decision comes before the one final checkpoint, and a later session knows the outcome.
        self.assertLess(final.index("6. Verification warnings come before the final checkpoint"),
                        final.index("`checkpoint.py create NN-final`"))
        self.assertEqual(final.count("checkpoint.py create NN-final"), 1)
        for words in ("If one is open, create no checkpoint", "On resume, continue at this step",
                      "once, after every warning is closed or accepted",
                      "VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES\n"
                      "Still failing (approved at the baseline): <check> — <numbers now> (baseline: <numbers>)\n"
                      "Not verified (accepted by the owner): <behavior> — <the check that would close it>",
                      "Never leave out either kind of line."):
            with self.subTest(words=words):
                self.assertIn(words, final)
        start = skill.split("## Start here, every time")[1].split("\n## ")[0]
        self.assertIn("(ALL GREEN, COMPLETE WITH APPROVED BASELINE FAILURES, or COMPLETE WITH ACCEPTED "
                      "VERIFICATION GAPS) or MIGRATION STOPPED, that migration is over", start)
        self.assertIn("- `VIBE-TO-ENGINEERING — COMPLETE WITH ACCEPTED VERIFICATION GAPS` (section 9)",
                      skill.split("## Status lines")[1].split("\n## ")[0])
        baseline = skill.split("## 6. CREATE + VERIFY BACKUP")[1].split("\n## ")[0]
        self.assertLess(baseline.index("Before step 1, the ledger holds an answer for every verification warning"),
                        baseline.index("1. `checkpoint.py create 00-baseline`"))
        self.assertIn("If one has no answer, create nothing", baseline)
        failed = skill.split("## 8. When something breaks")[1].split("\n## ")[0]
        self.assertIn("one `Verification Warning:` line each, above `Proposed action`", failed)
        self.assertIn("A failure neither closes nor accepts a warning.", failed)
        restored = failed.split("RESTORED <label>\n")[1]
        for words in ("one `Verification Warning:` line each, above `Phase n: NOT COMPLETE`",
                      "A restore neither closes nor accepts a warning, and listing one is not an approval to retry."):
            with self.subTest(words=words):
                self.assertIn(words, restored)
        # A covering check that fails at the baseline: approved continuation has a path, the failure stays visible.
        for words in ("and leaves its warning open",
                      "the stop report names that warning beside it",
                      "Continuing then needs the human's words on the warning as well",
                      "`ACCEPTED BY OWNER — covering check fails at the baseline`",
                      "the phase that changes that behavior may start",
                      "Without them the warning stays open and blocks that phase — ask",
                      "Report what the owner actually decided.",
                      # the two report states: open until explicitly accepted
                      "While the warning is open, every report shows the check's real `FAIL` with its numbers "
                      "and `Verification Warning: OPEN`.",
                      "Only after the owner's explicit acceptance do reports show "
                      "`Verification Warning: ACCEPTED BY OWNER`",
                      "only then does the final outcome carry a `Not verified` line for it, beside the check's "
                      "`Still failing` line",
                      "Write `FAIL — no new failures` only for a later run that matches the approved baseline "
                      "failure; the baseline run itself is `FAIL`.",
                      "Only a later fresh pass of that check closes the warning."):
            with self.subTest(words=words):
                self.assertIn(words, baseline)
        covering = next(line for line in baseline.splitlines()
                        if "When a failing check is the covering check" in line)
        self.assertNotIn("Either way", covering, "the report must follow the decision, not be the same for both")
        self.assertLess(covering.index("Without them the warning stays open"),
                        covering.index("`Verification Warning: OPEN`"))
        self.assertEqual(covering.count("ACCEPTED BY OWNER"), 2)   # the ledger record and the accepted report only
        self.assertIn("A covering check that runs and fails closes nothing: the warning stays open.", section)
        self.assertIn("never create it again; verify it, confirm `checkpoint.py diff NN-final` reports no changes",
                      final)
        maintenance = own["references/standard-alignment.md"].split("## Maintaining this bundle")[1]
        self.assertIn("rewrite each link target `](../SKILL.md` to `](../standard.md`", maintenance)
        self.assertNotIn("relative links intact", maintenance)

    def test_a_project_without_an_example_tree_still_has_a_route(self):
        router = self.own_instructions()["references/standard-alignment.md"]
        self.assertFalse((BUNDLE / "references" / "trees" / "game.md").exists())
        for words in ("A project with no matching example tree — a game, for instance — is still judged",
                      "conventions of its engine or framework", 'record "no example tree"',
                      "never force it into another family's tree"):
            with self.subTest(words=words):
                self.assertIn(words, router)


if __name__ == "__main__":
    unittest.main()
