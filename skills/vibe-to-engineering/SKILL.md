---
name: vibe-to-engineering
description: "Decides from evidence whether an existing software project's structure shows vibe-coded or ad-hoc development and, only if restructuring is justified, converts it into a project-specific engineered architecture through a controlled migration the human approves step by step: read-only inspection and diagnosis, current and target trees, a phased plan with Engineering-Migration-Plan.pdf, a verified recovery baseline, one approved phase at a time with tests and a checkpoint after each, failure investigation against the last known-good checkpoint, and a final review that reports ALL GREEN only when every final check passes. Use when the user invokes vibe-to-engineering, asks whether a project is vibe-coded or structurally sound, or asks to restructure a whole existing project into a proper engineering architecture. Not for building features, fixing bugs or small local refactors."
license: MIT
metadata:
  version: "0.1.0"
---

# vibe-to-engineering

Turns a structurally weak, ad-hoc ("vibe-coded") software project into an appropriately engineered one — only when the evidence says it needs it — through a migration the human approves one step at a time.

```
INSPECT → DIAGNOSE → DESIGN TARGET ARCHITECTURE → CREATE MIGRATION PLAN → GENERATE PDF
→ HUMAN APPROVAL → CREATE + VERIFY BACKUP → PHASE 1 → TEST + VERIFY → CHECKPOINT
→ HUMAN APPROVAL → NEXT PHASE → … → FINAL REVIEW → ALL GREEN
```

Engineering here means the right structure for this project — never more folders, layers or abstractions for their own sake. Many projects need no migration, and saying so is a correct result.

## Start here, every time

1. **Find the project.** It is the folder the human names. If none is named, it is the root of the current git repository, or else the current folder. If that is not clearly one software project (a home folder, a folder holding several projects, an empty folder), ask which one. Never guess, and name the project in your first line. The project folder itself is never moved or renamed.
2. **Resume if a migration exists.** If `<project>/.vibe-to-engineering/ledger.md` exists, read it. Its last entry says where the migration stands: tell the human in one line and continue from exactly there. Never redo a completed phase; never skip a gate. A phase recorded as started but not completed is handled as a break (section 8). If the last entry is a completion (ALL GREEN, or COMPLETE WITH APPROVED BASELINE FAILURES) or MIGRATION STOPPED, that migration is over: say so, and begin again at INSPECT only if the human asks. A new migration keeps the same ledger and store, and gives its checkpoints a run prefix (`r2-00-baseline`), because labels are never reused.
3. Otherwise begin at INSPECT.

**Conventions.** `<skill>` is this skill's folder and `<project>` the project's folder. `checkpoint.py …` is short for `python3 <skill>/scripts/checkpoint.py --project <project> …` — on Windows use `py -3` instead of `python3`.

## Human gates

The human owns every decision that changes the project. Stop and wait at:

| Gate | You stop when |
|---|---|
| Plan | the plan and its PDF are written |
| Next phase | a phase is complete (after the last one: before the final review) |
| Baseline not green | the starting checks fail or cannot prove the application works |
| Unexpected change | the project changed while you were waiting |
| Break | a failure you may not fix inside the phase (section 8), and before any restore |
| Restored | a restore is done and verified (section 8); the phase whose changes it undid is not complete |
| Plan change | reality contradicts the approved plan, or the human asks for a different target |
| Corrective phase | the final review found blocking findings |

**What counts as approval:** the human's explicit words approving that exact step ("approve", "approved", "yes, go ahead with phase 2"). A question, a comment, silence, or approval of something else is not approval — ask. **ONE APPROVAL = ONE STEP:** even if the human says "do all the phases", stop after each one, explaining that the protocol stops there so a failure is caught at the phase that caused it and the next approval takes one word. Record every approval in the ledger with the human's words, the time and what it approved.

### Stop, restore, correct, retry

Four separate transitions. Each is the human's decision, and none happens as part of another. A phase completes only when its whole verification passes — never because of a stop or a restore.

| Transition | What happens | What the human's word authorizes |
|---|---|---|
| **STOP** | The migration ends where it is. Nothing is restored, undone or changed: at a failure gate the failed state stays in place (it is saved as `failed-NN-phase-n`). Report `MIGRATION STOPPED` and record the stop in the ledger. | Stopping only. Restoring a checkpoint later is a separate RESTORE. |
| **RESTORE `<label>`** | `checkpoint.py restore <label> --apply`, then its verification (section 8), then the `RESTORED <label>` report and a stop. | That restore and its verification — nothing after them. |
| **CORRECT** | The correction the failure report proposed, inside the failed phase, then the whole phase verification again (checks and architecture check). If everything passes, the phase finishes with `PHASE n COMPLETE`; if not, it is a new break. A correction that changes the target, later phases or anything outside this phase is a plan change: revise the plan first. | That correction and the re-verification of that phase. |
| **RETRY MIGRATION** | The migration moves on after a RESTORE or a CORRECT: phase n again from its first step (after a restore, from the restored checkpoint), or the next phase after a corrected one. | Only its own explicit approval ("retry phase 2", "go ahead with phase 3"). An approval to restore or to correct never includes it. |

```
MIGRATION STOPPED
Project: unchanged — <where it stands: after phase n, or the failed state saved as failed-NN-phase-n>
Last verified checkpoint: <label> (restoring it needs its own approval)
```

## Status lines

Print these exactly, each on its own line:

- `NO MIGRATION REQUIRED`
- `AWAITING HUMAN APPROVAL`
- `PHASE n COMPLETE` and `PHASE n FAILED` (the blocks in sections 7 and 8)
- `RESTORED <label>` and `MIGRATION STOPPED` (the blocks in section 8 and under Human gates)
- `VIBE-TO-ENGINEERING — ALL GREEN`, or `VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES` (section 9)

Never write PASS for a check that did not run: write `N/A — <reason>` or `FAIL`. Never write PASS for a check that fails, even when its failure was approved at the baseline.

## 1. INSPECT (read-only)

Read-only means: read files, list folders, search, and run git commands that only read — `git --no-optional-locks -c core.fsmonitor=false` before `status`, `log`, `ls-files`, `diff` or `show` (plain `status` may rewrite git's index), and `--no-ext-diff --no-textconv` on anything that shows file contents or changes, so no diff program configured on the machine starts. Do not run builds, tests, installers, formatters, auto-fixing linters, project scripts, or anything that writes files or uses the network — they create caches and outputs. Write nothing anywhere in the project.

Files that hold secrets — `.env` and its variants, key and credential files, anything the project's own rules call secret — are read for their key names only, never their values (`sed 's/=.*//' .env` lists the names). A committed secret is reported by file, line and key name, and at most by the first 4 characters of its value when the human needs to recognize which key it is.

Establish, with paths as evidence:

- the project type, stack and frameworks, and the layout conventions they impose; the runtime and deployment model;
- the entry points and how the application is composed;
- the current tree — `checkpoint.py tree --current` prints every file and writes nothing: files git ignores, nested repositories and the skill's own folder are marked where they sit, and a folder holding only ignored files (dependencies, build output) is one line with its count. Show the human this full tree, never a shortened one;
- where each responsibility lives: UI and frontend, backend, API, domain rules, services, persistence and data, configuration, tests, build and packaging;
- the main data and control flows — trace one or two real features end to end;
- how the project is built, tested and run, from its manifests and CI files, without running them;
- its size: source files, lines, the largest files, the most-imported modules and, with git history, which files change together;
- where the application reads and writes data — database files, upload and export folders — and the environment variables or settings that choose them: checks must be pointed away from all of it;
- **external contracts** that must keep working: entry points, public API or package exports, command names, routes and URLs, configuration and environment-variable names, data and database files, and paths used by CI, containers, deploy scripts or other projects;
- the project's own rules and decisions (README, CONTRIBUTING, architecture notes, ADRs, AGENTS.md, CLAUDE.md). They outrank this skill's standard.

If part of the project cannot be inspected, say which part and why. Never judge what you did not read.

## 2. DIAGNOSE (read-only)

Load `references/engineering-standard.md` and judge the project against it. Record every finding with: an ID (F1, F2…), the criterion, the evidence (paths, line ranges or counts, import edges, duplicate locations — enough for someone else to re-check it), the practical impact, and the severity (Material or Minor).

Never make a finding because the tree differs from a preferred layout. Framework conventions, documented decisions, generated or vendored code and a small project being simple are not findings.

Apply the verdict rule in the standard:

- **No migration justified:** report `NO MIGRATION REQUIRED`, explain in plain language why the current structure fits this project (with its evidence), list any Minor findings as optional notes, and stop. Write nothing.
- **Migration justified:** continue straight to design. Nothing in the project changes until the plan is approved.

## 3. DESIGN TARGET ARCHITECTURE (read-only)

Load `references/migration-plan.md`. Design the target for this project only:

- derive it from the responsibilities you found, the stack's conventions and the project's size;
- give every folder in the target tree a one-line responsibility — if you cannot write one, the folder should not exist;
- trace every structural change to a finding ID;
- keep every external contract working;
- add no layer, abstraction, framework, dependency or empty folder that the findings do not require;
- prefer moving and splitting existing code over rewriting it.

Produce the CURRENT TREE, the TARGET TREE and the reason for each major decision, including the simpler alternative you rejected. Then account for every file: one before → after row per file of the project — what happens to it, what it holds today and afterwards — including every file the migration never touches, and who owns each job (database access, settings, routes, UI, tests…) before and after. Together the rows must cover every file `checkpoint.py tree --current` counts (a folder row counts its files).

## 4. CREATE MIGRATION PLAN

Cut the migration into phases with the rules in `references/migration-plan.md`: one objective per phase, the application works at the end of every phase, moves are kept apart from logic edits, remnants are removed last, and the documentation phase ends every plan — it leaves a short record of the new structure and the reasons for it inside the project, in the form the project already uses, and the plan shows its exact text. Leave it out only when the human declines it ("no docs"). Each phase states its objective, finding IDs, exact changes (old path → new path; what is split into what), files in scope, expected tree afterwards, verification and risks.

Define the checks that prove the application still works — build, type check, tests and a smoke run of the real entry point — and what counts as a pass. If the project lacks the checks to prove its behavior is preserved, the first phase adds a safety net of characterization checks; that phase is part of the plan the human approves.

Create `<project>/.vibe-to-engineering/` with a `.gitignore` file holding the single line `*`, so the folder never enters the project's git. Write `Engineering-Migration-Plan.html` there from `<skill>/assets/plan-template.html`. This folder is the only thing written before approval.

## 5. GENERATE PDF, then stop

```
python3 <skill>/scripts/render_pdf.py <project>/.vibe-to-engineering/Engineering-Migration-Plan.html <project>/.vibe-to-engineering/Engineering-Migration-Plan.pdf
```

Look at the result — open it or render its pages as images — and make sure the CURRENT → MIGRATION → TARGET page is readable. If no browser is found, the tool says so: tell the human, give the HTML file's path (it opens in any browser) and still stop here.

Fingerprint the plan with `git hash-object --no-filters <the .html file>` and start `.vibe-to-engineering/ledger.md` with the plan's version and fingerprint.

Report in plain language: where the project is now → what is wrong → the proposed architecture → how it gets there (one line per phase) → the PDF's path → what approval authorizes (creating the backup and Phase 1, nothing more). End with:

```
AWAITING HUMAN APPROVAL
```

## 6. CREATE + VERIFY BACKUP

Only after the human approves this plan version. Load `references/recovery.md`.

1. `checkpoint.py create 00-baseline`, then `checkpoint.py verify 00-baseline`. If either fails, stop: no migration without a verified recovery point. `create` refuses, for example, while a folder cannot be read or a nested repository holds uncommitted work; report what it names — resolving it is the human's decision.
2. Record the starting point in the ledger: the time, the checkpoint name and — if the project uses git — its branch, commit and number of uncommitted changes (`git --no-optional-locks status`).
3. Run the plan's checks once, each through `evidence.py` (section "The checkpoint tool"), which saves its output in `.vibe-to-engineering/evidence/00-baseline/` with secret values masked; record the results with numbers (tests found, passed, failed, skipped).
4. If running the checks changed project files (`checkpoint.py diff 00-baseline`, ignored files it reports `changed` included), record which files and create `00-baseline-checked`. Files the checks rewrite by themselves are not unplanned changes in later phases.
5. Stop if any check failed. Also stop if the checks cannot prove the application works, unless the plan begins with a safety-net phase that adds exactly that proof. When you stop, report the baseline, ask whether to continue with "no new failures" as the bar or to fix it separately first, and end with `AWAITING HUMAN APPROVAL`. If the human approves continuing, record in the ledger every check that fails at the baseline, with its numbers: these are the approved baseline failures, and they stay visible to the end (sections 7 and 9).
6. If everything passed, start Phase 1 — the plan approval covers it.

## 7. PHASE n — one per approval

Before starting, confirm all three; if one fails, stop and report:

- the plan's fingerprint equals the approved one (otherwise the plan changed and needs approval again);
- the project equals the last checkpoint — `checkpoint.py diff <last>` reports no changes (otherwise someone changed it while you waited: show the changes and ask);
- the human approved this phase (for Phase 1: the plan approval).

Add `PHASE n STARTED` to the ledger, then:

1. State the phase's scope in a few lines.
2. Make only this phase's planned changes, then update every reference to what it moved or renamed: imports, paths in configuration, scripts, build files, CI, documentation.
3. Run the plan's checks through `evidence.py` (into `evidence/NN-phase-n/`) and compare them with the baseline: everything that passed then passes now, the number of tests is not lower, and the smoke run behaves the same. A check that still fails under an approved "no new failures" bar is reported as `FAIL — no new failures (<numbers>; the same failures as the approved baseline)`, never as PASS.
4. Architecture check: `checkpoint.py diff <last>` shows exactly the phase's planned changes and their reference updates — nothing else — it reports no ignored file or nested repository `gone` and no ignored file `changed` (apart from files the checks rewrite, recorded at the baseline), and no reference to an old path remains anywhere. A changed ignored file is a break like a gone one: no checkpoint can bring back what it held.
5. Record in the ledger what changed (with the diff summary), every check with its numbers, and where the evidence is.
6. `checkpoint.py create NN-phase-n`, then `checkpoint.py verify NN-phase-n`.
7. Report and stop:

```
PHASE n COMPLETE
Build: PASS
Tests: PASS (212 passed, 0 failed; baseline 212)
Architecture Check: PASS
Recovery Checkpoint: CREATED (02-phase-2)
NEXT: Phase n+1 — <title>
AWAITING HUMAN APPROVAL
```

After the last phase, write `NEXT: Final review`. Follow the block with a few plain-language lines: what changed and what stayed the same.

**The only fix allowed inside a phase:** while doing steps 2 and 3, you may use the build, type checker and tests to find references you missed, and fix exactly those — the error names a path or name this phase changed, and the fix points it at the new one. Anything else is a break.

## 8. When something breaks

A break is: a failure that is not a missed reference to this phase's own change; a failure you cannot explain; a fix that would change behavior, touch a file outside the phase's scope, alter a test's expectations, skip or delete a test, loosen a check, or need a restore; the same check still failing after two rounds of reference fixes; or a phase found half-done when resuming.

1. Stop changing the project.
2. `checkpoint.py create failed-NN-phase-n` — keep the failed state.
3. `checkpoint.py diff <last-good> failed-NN-phase-n` — everything that changed since the last known-good checkpoint.
4. Find the root cause: read the failure output, re-run the failing check once to see whether it is deterministic, and tie the failure to specific changes in the diff. Test ideas in a scratch copy (`checkpoint.py extract <label> <empty folder outside the project>`), never by undoing things in the project.
5. Report and stop:

```
PHASE n FAILED
Failing check: <command>
Observed failure: <exact excerpt; full output in evidence/…>
Changes since last good checkpoint (<label>): <list>
Root cause: <cause> | NOT ESTABLISHED — <what was ruled out>
Proposed action: CORRECT — <correction> (recommended) · or RESTORE <label> · or STOP
AWAITING HUMAN APPROVAL
```

6. Do exactly the transition the human chose (Human gates → Stop, restore, correct, retry) and record it in the ledger. After a CORRECT, the architecture check counts the approved correction as planned. A RESTORE never completes the phase, and nothing moves on after it without a RETRY MIGRATION approval.

**Restoring is never automatic.** `checkpoint.py restore <label>` only shows what it would change. Run it with `--apply` only after the human approves that restore. Before it changes anything, it saves the current state as a new checkpoint and proves that this checkpoint and `<label>` both come back byte for byte; it refuses, changing nothing, when either does not, or when the restore would overwrite or remove something no checkpoint holds (files git ignores, nested repositories, a folder holding them). Report a refusal as it is and stop. After a restore it checks its own result; verify it with `checkpoint.py diff <label>` (no changes) and the plan's checks, then report and stop:

```
RESTORED <label>
Restore: VERIFIED — checkpoint.py diff <label> reports no changes; the state before it is saved as pre-restore-<time>
Checks: <results, compared with those recorded for <label>>
Phase n: NOT COMPLETE — its changes were undone
AWAITING HUMAN APPROVAL
```

## 9. FINAL REVIEW

After the human approves it:

1. **Re-inspect independently.** If your environment can start a fresh agent, give it only the approved plan and the project and have it make the comparison below; it reads and runs checks, and changes nothing. Otherwise redo INSPECT from scratch before you read your own phase notes.
2. Compare the APPROVED TARGET TREE with the ACTUAL FINAL TREE (`checkpoint.py tree --current`), marked lines included — an ignored file or nested repository that moved or disappeared is a difference too. Every difference must be covered by an approved plan revision; anything else is a finding.
3. Verify: responsibility boundaries and dependency direction as designed; no dependency added or removed unless planned (compare the manifests and lockfiles with `00-baseline`); the build; the tests (none fewer than at the baseline, no new failures); the smoke run behaves as at the baseline; every ignored file and nested repository of `00-baseline` still there and unchanged, apart from files the checks rewrite (`checkpoint.py diff 00-baseline` reports none `gone` or `changed`); no migration remnants (references to old paths, temporary shims not meant to stay, empty folders, backup or scratch files, migration notes left in code); documentation that describes the structure matches it — above all the record the documentation phase wrote: every folder and file it names exists and holds what it says, and a mismatch is a finding. If the human declined the record, say that the project holds none.
4. Final architecture and code review: judge the final project with `references/engineering-standard.md`. A Material finding that the migration left or introduced blocks completion.
5. Blocking findings: report them and propose a corrective phase as a plan revision — new version, new PDF, new fingerprint (`references/migration-plan.md`, section 6) — and end with `AWAITING HUMAN APPROVAL`.
6. None: `checkpoint.py create NN-final` and `checkpoint.py verify NN-final`, then report exactly one outcome:

```
VIBE-TO-ENGINEERING — ALL GREEN
```

only when every check the plan requires ran in this review and passed — no check fails, whatever was approved at the baseline. Otherwise, when the migration is complete but checks approved as failing at the baseline still fail:

```
VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES
Still failing (approved at the baseline): <check> — <numbers now> (baseline: <numbers>)
```

with one `Still failing` line per such check. Never shorten it to ALL GREEN, and never present those checks as passing.

Follow the outcome with the before and after trees (every file, as `tree` prints them), the plan's two tables — every file before → after, and who owns each job — as they actually came out, so the human can compare them with the approved plan line by line, the checks compared with the baseline, and the checkpoint list. Tell the human where the project's own record of its structure is (or that they declined one), that `.vibe-to-engineering/` holds the plan, ledger, evidence and checkpoints, and that keeping or deleting it is their decision — the record in the project stays either way. No commits were made unless they asked for them.

## Always

- **Behavior:** preserve the product's intended behavior. No new features, no bug fixes (write down bugs you notice for the human), no dependency changes (adding, removing or upgrading), no formatting sweeps, no renames for taste.
- **Scope:** only planned changes. Files git ignores, secrets, databases, user data and nested repositories (folders with their own git, which checkpoints do not save) are never moved, edited or deleted — so move files by name, never with wildcards or whole-folder moves that could carry them along. External contracts keep working.
- **The skill's own folder:** no phase moves, edits or deletes the plan, ledger, evidence or checkpoints in `.vibe-to-engineering/`; the only files a phase adds there are a safety net's checks, in `checks/`.
- **Checks stay local:** a check never installs or updates dependencies, deploys, publishes, migrates a database or sends anything anywhere. If running a check changes a dependency manifest or lockfile, stop and ask: that is a dependency change.
- **Checks use throwaway data:** a check never reads or writes the owner's data. The plan names, for each check, the data it uses and how it is redirected (an environment variable pointing at a temporary file, a temporary copy, a test fixture); a check that cannot be redirected is not run — the human decides. A check that starts a server takes a free port and proves the answers come from the process it started (`references/migration-plan.md`, section 3).
- **Git:** never push. Never commit, branch, reset, clean, stash or rewrite history in the project's repository unless the human asks; if they ask for commits, commit one completed phase at a time.
- **Tests:** never edit expected values or snapshots, skip, delete or silence tests, or loosen type, lint or build settings to reach green.
- **Deletions:** only files the plan names, and only when a checkpoint holds them.
- **Evidence:** every PASS rests on a command and its numbers; every claim can be checked in the ledger or in `evidence/`.
- **Secrets:** no secret value goes into the plan, the PDF, the ledger, `evidence/` or your own messages. Every check runs through `evidence.py`, which prints and saves its output with secret values masked; secret files are read for their key names only.
- **Plan changes:** when reality contradicts the plan — a framework constraint, a hidden dependency, a contract the plan missed — stop and propose a revised plan (new version, new PDF, new fingerprint). Never deviate silently. Record the human's own instructions given during the migration in the ledger; a change to the target needs a revised plan.
- **No network and no installs** for this skill's own work.

## Files written in the project

```
<project>/.vibe-to-engineering/          ignores itself — never enters the project's git
├── .gitignore                           the single line: *
├── Engineering-Migration-Plan.html      the plan: its one source of truth
├── Engineering-Migration-Plan.pdf       what the human reads and approves
├── ledger.md                            append-only record: approvals (quoted), baseline, phases, failures, restores
├── evidence/                            check output (secret values masked), trees and diffs, one folder per step
└── checkpoints.git/                     the recovery store (a separate git store; the project's own repository is only read)
```

Ledger entries are appended, never edited. Each starts with a heading `## <UTC time> — <EVENT> — <state it leaves>`, for example `## 2026-09-23 14:30 UTC — PHASE 2 COMPLETE — AWAITING HUMAN APPROVAL`, so the last heading always says where the migration stands.

## The checkpoint tool

`<skill>/scripts/checkpoint.py` implements the recovery contract in `references/recovery.md` with Python 3.8+ (standard library only) and git. Always pass `--project <project>`.

| Command | What it does |
|---|---|
| `create <label>` | save the project's current files as a checkpoint; a label can never be reused |
| `verify <label>` | prove the checkpoint restores byte for byte |
| `list` | list the checkpoints |
| `diff <from> [<to>]` | changes between two checkpoints, or from a checkpoint to the current files, plus any ignored file or nested repository that disappeared and any ignored file whose contents changed; `--patch` shows the lines |
| `tree [<label>]`, `tree --current` | a tree of every file of a checkpoint or of the current files — ignored files, nested repositories and the skill's own folder marked where they sit; `--current` writes nothing; `--saved-only` shows only what checkpoints save |
| `extract <label> <folder>` | copy a checkpoint into an empty folder outside the project, for investigation |
| `restore <label> [--apply]` | show a restore; with `--apply` and the human's approval, do it |

If Python 3 or git is unavailable, stop before changing anything and tell the human what is missing. Never improvise a backup.

Every check runs through `<skill>/scripts/evidence.py`, never on its own:

```
python3 <skill>/scripts/evidence.py --project <project> --out <project>/.vibe-to-engineering/evidence/<step>/<check>.txt [--env NAME=VALUE]… -- <command> [<argument>…]
```

It runs the command in the project folder — `--env` points it at throwaway data — then prints and saves its output with secret values masked, and exits with the command's own exit code. Masked: every value the project's secret files give a name (`.env` and its variants, key, credential and certificate files — read for masking, never shown), in every form it may be printed — `NAME=VALUE`, `name: value`, `"name": "value"`, quoted or not, with or without an inline comment — and anything shaped like a private key, an access token or a password, wherever it appears. Left readable, and named in the summary line: a number or a yes/no word under a name that does not say secret (`PORT=8000`, `DEBUG=true`) — a setting, not a secret. A secret file that is a link is read through the link. The run stops before the check when a folder cannot be listed or is a link: a secret file inside it would not be found. It writes only inside `.vibe-to-engineering/evidence/`.

## References

| File | Load when |
|---|---|
| `references/engineering-standard.md` | DIAGNOSE, checking your own target design, FINAL REVIEW |
| `references/migration-plan.md` | DESIGN TARGET ARCHITECTURE, CREATE MIGRATION PLAN, GENERATE PDF, plan revisions |
| `references/recovery.md` | CREATE + VERIFY BACKUP, every phase, any break or restore |
