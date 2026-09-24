# F02 builder handoff (copy)

> Copy of the builder handoff delivered on 2026-09-24 for commit `99e1a6a` (the original is on the owner's Linux PC: `~/Documents/vibe-to-engineering-f02-builder-2026-09-24/HANDOFF.md`, next to its evidence files).
> After it, the owner accepted F02 and R1 as fixed and independently reviewed on Linux at `99e1a6a`. F02 stays open until the test suite passes on the owner's Mac — see [MAC-TEST-STEPS.md](MAC-TEST-STEPS.md).

```text
CORRECTIVE HANDOFF — F02 (including R1) — Full
STATUS: DELIVERED FOR INDEPENDENT REVIEW
This handoff replaces both earlier F02 handoffs (the one for 51e462b and the R1 one for 99e1a6a).

REVIEW TARGET
- Repository: github.com/workspace-labs/vibe-to-engineering (private)
- Branch fix/f02-store-writes-outside @ 99e1a6adf138c7a8e44d6d73d9cbb5784719ed16
- Base: main @ f709639a4d3159481b5ae23ede4041d96393f272 (unchanged)
- Commits: bcc3279 (the fix, the first tests, docs) → 51e462b (more unreadable-folder cases, FIX-FIRST status line) → 99e1a6a (R1: wording, plus an existing-log test)
- Whole change: git diff f709639..99e1a6a — 5 files, +130 −3
- Evidence folder (on the owner's Linux PC): /home/mohammad/Documents/vibe-to-engineering-f02-builder-2026-09-24/

BASELINE
- Before the first edit: a clean clone of main @ f709639. python3 -m unittest discover -s tests -v → 45 run: 39 passed, 6 skipped.
- Prior state: FIX-FIRST.md item 1 lists F02 (High) as reopened by the independent re-review of 2026-09-24 of 502d3c5.

SCOPE
- AUTHORIZED by the owner: fix FIX-FIRST item 1 (F02), then hand off for Codex review. Later, through the owner's corrective prompt relaying Codex: correct R1's wording, add one existing-log regression, and keep F02 pending.
- NOT AUTHORIZED: FIX-FIRST items 2–11 (including F03, F06, F08 and NEW-1), merging into main, making the repository public, a logging redesign.

OWNER DECISIONS
- Recorded: the repository stays private until the FIX-FIRST items are fixed; work stays on the branch, with no merge.
- Owner status (the owner, 2026-09-24): at work on a Linux PC; the macOS run will be done later on the owner's Mac.
- Still required: the merge decision after review; whether to take the two review suggestions not done here (see RISKS).

FINDINGS ADDRESSED
- F02 (High) — "the backup store can still change files outside it" (FIX-FIRST.md item 1).
  Required correction (FIX-FIRST "Fixed means", quoted): "no write into the store — git's own appends included — can reach another name for the same file, and a store the tool cannot fully read stops the command before any write. Tests for both routes check that the outside bytes are unchanged and the command refuses. The existing link, redirect, config, attribute and exclude tests still pass, and deep `refs`, object folders, `logs` and `packed-refs` are covered."
- R1 (Medium / BUG) — "existing reference logs still receive in-place appends." Raised by Codex's review of 51e462b (/home/mohammad/Documents/vibe-to-engineering-f02-review-2026-09-24/REVIEW.md). Verdict there (quoted): "CHANGES REQUESTED before merging. Keep the F02 re-review open."
  Required correction (the owner's corrective prompt, quoted): "Correct checkpoint.py's comment, recovery.md's G7 wording, and the changelog/handoff: the setting prevents automatic creation of missing logs; existing logs can still receive appends. The hard-link check protects outside files." · "Add a durable regression covering an existing log, distinguishing a permitted single-link log from a hard-linked log that must be refused before any write, with outside bytes unchanged."

ROOT CAUSE
1. F02, hard-linked file: check_state_folder refused symbolic links and special files, but not a regular file with a second name (a hard link). Git appends to a reference log in place, so update-ref appended to the outside file through the store's name for it.
2. F02, unreadable folder: os.walk, with its default onerror=None, silently skips a folder it cannot list, the store folder itself included. A symbolic-link config inside it went unseen, and `git config --file` wrote through it.
3. R1: the builder described core.logAllRefUpdates=false as switching reference logs off, without testing a log that already exists. Git creates a missing log only when that setting allows it, but appends to an existing one whatever the setting says. Codex cites git-update-ref "Logging updates" and refs/files-backend.c of Git 2.51.0, and its syscall trace shows O_WRONLY|O_APPEND.

IMPLEMENTATION — skills/vibe-to-engineering/scripts/checkpoint.py @ 99e1a6a
- :111-113 STORE_SETTINGS = ("core.logAllRefUpdates=false",). The comment says git creates no missing reference log, still appends to a log that already exists, and that the link-count check keeps that append from reaching another file (G7). At :169, git() passes it with -c to every call made with store=. Effect: it overrides a store config that asks for logs, so no missing log is created. It does NOT stop appends to an existing log.
- :242-245 check_state_folder: os.walk(..., onerror=unreadable) raises Fail "cannot read the folder <path> inside the store (...) ... Nothing was changed".
- :250 check_state_folder: any store file with st_nlink > 1 raises Fail "<path> inside the store is also another file's name (a hard link) ... Nothing was changed". The exception is :116 REPLACED_WHOLE = config, info/attributes, info/exclude. Writes to those three replace them whole (git config: lock file, then rename; write_lf: temporary file, then os.replace). When the contents already match, write_lf writes nothing, so a second name can remain until a later write replaces the store's name.
- Placement: both refusals run first in prepare_store, before the state folder, git init, git config and write_lf. Every command that uses the project's store reaches that point, through prepare_store (create) or open_store (verify, list, diff, tree <label>, extract, restore). `tree --current` never uses the project's store: it reads a git project directly, and a plain folder gets a new temporary store in the system's temporary folder.
- `git init --bare` and `git config --file` are called without store=, so they do not get the -c setting. Both run after the check.
- Architectural impact: NONE beyond the existing store boundary. No new module, dependency, store format or CLI change.

FILES CHANGED (all authored, nothing generated; git diff --numstat f709639..99e1a6a)
- skills/vibe-to-engineering/scripts/checkpoint.py (+16 −2): the correction and its comments
- tests/test_checkpoint.py (+107 −0): the identities() helper and three new tests; no existing test changed
- skills/vibe-to-engineering/references/recovery.md (+1 −1): the G7 row
- CHANGELOG.md (+4): the [Unreleased] F02 entry
- FIX-FIRST.md (+2): a status line under item 1
CONTRACT / DATA CHANGE: the store format, command line and exit codes are unchanged, and there is no migration. The G7 guarantee text is extended: the tool refuses an unreadable store and hard-linked store files (three exempt); core.logAllRefUpdates=false prevents creating missing logs, while existing logs still receive appends. The refusal messages are new.
PROTECTED AREAS: render_pdf.py, SKILL.md, README.md and the snapshot, verify and restore logic are not in the diff.

BEHAVIOR
- BEFORE: a store command could append to or rewrite a file outside the store, through a hard-linked store file or through a link hidden in an unreadable store folder, and exit 0.
- AFTER: every command that uses the project's store refuses such a store with exit 1, before any write. A missing reference log is never created. A single-name log that already exists inside the store still receives git's append, as it did before.
- UNINTENDED BEHAVIOR CHANGE: NONE FOUND within the checked surfaces. One new refusal is expected: a store copied with hard links (cp -al, rsync --link-dest) is refused until it is copied normally. Codex's review found that a normal copy then verifies.

TESTS (NEW REGRESSION TESTS, tests/test_checkpoint.py @ 99e1a6a)
- T1 :586 test_a_store_file_with_a_second_name_outside_is_refused_and_git_appends_to_no_file. The store config sets logAllRefUpdates = always. A hard link to an outside file holding "KEEP THESE BYTES\n" is placed, one at a time, at logs/refs/checkpoints/01-next, logs/HEAD, refs/checkpoints/deep/er/label, packed-refs and one loose object. For each, create, list and verify must exit 1 with "hard link", with the outside bytes and the project unchanged. Last, with no link, create 01-next creates no log for 01-next. Its name describes only these cases (a refused hard link; a missing log not created), not a general no-append guarantee.
- T2 :622 test_an_existing_reference_log_takes_an_append_with_one_name_and_is_refused_before_any_write_with_two. First, an existing log hard-linked to an outside file: create must refuse with "hard link", and the outside bytes, the project, and every store name, inode, mtime_ns and byte (identities, :79) must be unchanged. That shows it refused before any write, including inside the store. Then the same 17 bytes as a single-name store file: create must exit 0, the outside bytes stay unchanged, and the log keeps its first 17 bytes and grows.
- T3 :646 test_a_store_folder_that_cannot_be_read_stops_every_command_before_a_write (skipped on Windows and as root). A symbolic link to an outside git config holding "autocrlf = true" is hidden in a folder set to 0300. Four cases: the store itself (the link is store/config), a deep reference folder, an object folder and a reference-log folder. For each, list, create, verify and diff must exit 1 with "cannot read the folder", with the outside bytes and the project unchanged. Afterwards, verify passes again.
- OLD IMPLEMENTATION: T1–T3 at 99e1a6a, with V2E_CHECKPOINT set to checkpoint.py from f709639 → Ran 3, FAILED (failures=11): T1 ×6 (all 5 places plus its last step), T3 ×4 (every folder), T2 ×1. Evidence: new-tests-old-code.log.
- NEW IMPLEMENTATION: T1–T3 pass.
- MUTATION PROBES (builder-only; variant files in the evidence folder, mutation.log):
  | variant of 99e1a6a's checkpoint.py | T1 | T2 | T3 |
  | link-count check disabled          | FAIL (6) | FAIL | pass |
  | -c core.logAllRefUpdates=false removed | FAIL (1, its last step) | pass | pass |
  | store check moved after the config write | pass | FAIL (store inode changed) | FAIL (1, the store case) |
  Every variant fails at least one test, and each test catches at least one variant. T2 passing without the log setting is R1's point: the setting has no effect on an existing log.

VERIFICATION
- VERIFIED: the full suite at 99e1a6a, python3 -m unittest discover -s tests -v → Ran 48: 42 passed, 6 skipped, 0 failures, 0 errors (suite-99e1a6a.log). Earlier runs: f709639 had 45 run / 39 passed / 6 skipped, and 51e462b had 47 / 41 / 6. Codex's runs report the same.
- Skipped (the same 6 on every commit): 4 need a case-insensitive disk ("this file system tells letter cases apart"): test_a_rename_that_only_changes_letter_case_is_saved_under_its_one_real_name_and_restored, test_create_refuses_when_git_leaves_a_file_out_without_saying_so, test_restore_puts_back_a_name_whose_only_change_was_letter_case, test_verify_fails_a_checkpoint_holding_two_names_for_one_file_on_this_disk. 2 need a Chrome-family browser (test_render_pdf). The 4 letter-case tests pass through the new store check, so they matter for the macOS run.
- NOT RUN: macOS (PENDING; the owner will run it on the Mac, and Linux results do not count for it); Windows; FAT, exFAT and network drives; reftable-format stores; performance.

REPRODUCTION (repro.sh in the evidence folder; builder-only; old f709639 against new 99e1a6a; logs repro-f709639.log and repro-99e1a6a.log)
1. FIX-FIRST item 1, "See it" 1: the store config sets logAllRefUpdates = always; logs/refs/checkpoints/second is hard-linked to a 17-byte outside file; then create second.
   EXPECTED: refusal, outside file unchanged. OBSERVED f709639: exit 0, outside 17 → 177 bytes. OBSERVED 99e1a6a: exit 1 ("a hard link"), 17 bytes. RESULT: PASS
2. "See it" 2: the store config is replaced by a symbolic link to an outside config holding autocrlf = true; the store folder is set to 0300; then list.
   EXPECTED: refusal, outside file unchanged. OBSERVED f709639: exit 0, the outside file now says autocrlf = false. OBSERVED 99e1a6a: exit 1 ("cannot read the folder"), still autocrlf = true. RESULT: PASS
3. R1: a 17-byte single-link file at logs/refs/checkpoints/second (no outside name); then create second.
   EXPECTED (corrected G7): permitted; git appends to the store's own log. OBSERVED at both commits: exit 0, 17 → 177 bytes, 1 link. RESULT: matches the corrected wording.
   Usage: sh repro.sh <path to a checkpoint.py> <label>

FAILURE TESTING
- Exercised by the builder:
  - hard links at 5 store paths × 3 commands (T1);
  - hidden links in 4 unreadable folders × 4 commands (T3);
  - a hard-linked existing log, with the no-write-before-refusal check (T2);
  - a hard-linked exempt config (probe: list exits 0, the outside sha256 is unchanged, the link count is 1 afterwards);
  - normal use (create, create, restore --apply, verify → no store file with a link count above 1).
- Reported by Codex's independent review of 51e462b (REVIEW.md; not rerun by the builder):
  - 117/117 hard-link refusals across 13 store paths × 9 command forms;
  - 162/162 unreadable-folder refusals across 6 folders × 3 modes × 9 command forms;
  - exempt-file probes that preserved the outside bytes;
  - a valid hard-linked loose object: the old code changed the outside file's mtime, the new code refused.
- Not exercised: concurrent commands on one store, bind mounts, macOS, Windows.

REGRESSION REVIEW
Surfaces checked: the existing store-safety tests (links as store files, commondir and alternates redirects, a hard-linked info/attributes replaced rather than written through, hooks and hostile git settings); every command path in the full suite; link counts after normal use; the exempt config. → NO REGRESSION FOUND WITHIN THE CHECKED SURFACES (Linux only).

KEY CLAIMS AND EVIDENCE
- Both FIX-FIRST F02 routes are refused, and outside bytes are kept → T1, T3; repro lines 1 and 2.
- A hard-linked existing log is refused before any write, even inside the store → T2's identities comparison; the "check after config write" variant fails T2.
- core.logAllRefUpdates=false only stops missing logs being created → T1's last step (fails without the setting), T2's single-name case (the append happens), repro line 3.
- No existing test changed → git diff f709639..99e1a6a -- tests/ removes no line.
- 99e1a6a changes only comments in checkpoint.py → git diff 51e462b..99e1a6a -- skills/vibe-to-engineering/scripts/checkpoint.py.

GIT
- f709639 → bcc3279 → 51e462b → 99e1a6a on fix/f02-store-writes-outside. Working tree clean. Pushed to origin, fast-forwards only. No pull request. main is untouched, and the repository is still private.
- All three commits are authored as itsmk91 <workspacelabs91@gmail.com>, the identity of the repository's existing commits, because no git identity is configured on this PC. The owner may amend them.

DEVIATIONS
1. Interpretation: config, info/attributes and info/exclude are exempt from "refuse any store file with more than one name" (a FIX-FIRST idea). "Fixed means" requires the existing attribute test to keep passing (it verifies with a hard-linked info/attributes), and writes to those three replace them whole. Codex's review of 51e462b found the exemption sound within its tested scope.
2. FIX-FIRST.md and CHANGELOG.md were updated to record the status without being asked.
3. The commit author identity (see GIT).

CORRECTIONS TO THE EARLIER HANDOFFS
- The 51e462b handoff said "git keeps no reference log in the store". That is FALSE. See IMPLEMENTATION and R1.
- The 51e462b handoff said T1 "catches either mechanism being removed". That holds only for T1's own cases; appends to an existing log are covered by T2 alone.
- The 51e462b handoff gave "Ran 47, OK (skipped=6)": 41 of those passed.

SIDE EFFECTS
- EXTERNAL: three commits pushed to the private GitHub branch. Undo with: git push origin --delete fix/f02-store-writes-outside.
- Local: the evidence folder above was created in ~/Documents. Codex's review folder was only read. No deletions.
- DEPENDENCIES: UNCHANGED (standard library only).
ROLLBACK POINT: main @ f709639, unchanged. The correction exists only on the branch.
REPEATED RUNS: a refused command changes nothing, so running it again refuses the same way (the tests run 3–4 commands in a row per case). Once the link is removed or the permissions restored, commands work again (the last step of each test).
PERFORMANCE: NOT MEASURED. Every command does one extra os.stat per store file (FIX-FIRST item 11).
ENVIRONMENT: Linux 6.17, Python 3.13.7, git 2.51.0, tests on tmpfs, as a normal user (uid 1007).

LIMITATIONS
- macOS: PENDING — NOT RUN. Windows: NOT RUN; st_nlink through os.stat and the backslash paths in REPLACED_WHOLE are untested there, and T3 skips there. FAT, exFAT, network drives and reftable-format stores were not tried.
- Check, then act: a link that another process makes after the check is not caught.
- Mount points (bind mounts) inside the store are not detected. Making one needs administrator rights.
- An unreadable state folder (.vibe-to-engineering, 0300) is not refused while its store can still be walked. Codex saw list and verify succeed there and found no outside write. The guarantee is a full walk of the store, not of the whole state folder.
- A folder that can be listed but not entered is refused with the "link or a special file" message rather than "cannot read".

RISKS (not changed: owner decision)
- Two commands running on one store at the same moment may be refused, because git briefly gives a new object file two names (link, then unlink). Codex's trace showed both steps but did not force the timing. Smallest correction: state in recovery.md that commands run one at a time on a store.
- A hard-link copy of a project is refused, and the message does not say that a normal copy fixes it. Smallest correction: add that hint to the message or to the user docs.

FINDINGS
- F02 — CORRECTED / DELIVERED FOR RE-REVIEW (stays open until the independent re-review and the macOS run)
- R1 — CORRECTED / DELIVERED FOR RE-REVIEW
- F03, F06, F08, NEW-1 — NOT IN SCOPE / REMAIN OPEN (FIX-FIRST items 2–5)
- No builder-discovered problems.

CODEX RE-REVIEW HANDOFF — independent verification requested
The owner is on a Linux PC now. Please re-review on Linux; the macOS run follows later from the owner's Mac.
1. Confirm the target: 99e1a6a on fix/f02-store-writes-outside, with parents 51e462b → bcc3279 → f709639, and that git diff f709639..99e1a6a touches only the 5 files above.
2. Reproduce FIX-FIRST item 1 "See it" 1 and 2 and R1, at f709639 and at 99e1a6a (repro.sh, or your own probes). Determine whether the outside bytes survive at 99e1a6a and whether each refusal happens.
3. Rerun the suite at 99e1a6a (builder: 48 run, 42 passed, 6 skipped). Rerun T1–T3 against f709639's checkpoint.py through V2E_CHECKPOINT (builder: FAILED, failures=11).
4. Determine whether the corrected wording (checkpoint.py:111-112, recovery.md G7, CHANGELOG) matches what git does with missing and existing logs, and whether any other in-place git write into the store could reach a second name.
5. Determine whether T2's identities comparison is strong enough to show "refused before any write".
6. Judge the LIMITATIONS and RISKS for this gate, and decide whether T1's name should change.
7. Decide whether R1 closes, and whether F02 closes now or stays open until the macOS run.
WEAKEST POINTS, BUILDER'S VIEW: the three-file exemption (write_lf's matching-bytes return keeps a second name); git writes in the store the builder did not enumerate (reftable stores were not tried); concurrency; untested macOS and Windows behavior.

NEXT GATE: DELIVERED FOR CODEX REVIEW (re-review of F02 and R1) → macOS suite run on the owner's Mac (PENDING) → the owner's decision on merging fix/f02-store-writes-outside into main.
```
