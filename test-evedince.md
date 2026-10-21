# Test evidence — 2026-10-21

Requested filename: `test-evedince.md`.

## Result and how many

**PASS: 378 distinct unittest test methods in the final native macOS suite.**
There were **zero failures, zero errors and zero skipped tests**. The run took
415.309 seconds (about 6 minutes 55 seconds).

The original GitHub snapshot passed 359 tests. This repair adds **19 regression
methods**, bringing the complete suite to **378**. Passing the original suite did
not expose the five problems reproduced by the additional checks.

The final portable scope separately passed **90 tests** with no failures, errors
or skips. Those 90 methods are included in the 378-test suite: they must not be
added together as 468 unique tests.

## Source and environment

- Repository: https://github.com/workspace-labs/vibe-to-engineering
- Baseline commit: `bd8133fa474a36694a11452138a1110c0c1ba860` (clean checkout).
- Repair branch: `codex/test-repair-2026-10-21`; package version `0.1.1-dev`.
- Host: macOS 27.0.1, Apple Silicon arm64.
- Native interpreter: Apple Command Line Tools Python 3.9.6.
- Local Node: v20.20.2; shell: GNU Bash 3.2.57 at `/bin/sh`.
- Browser: installed Chromium headless shell 149.0.7827.55, Playwright cache revision 1228.
- Reader preparation: 93 pinned artifacts downloaded and SHA-256 verified. All four
  differential-reader matrix tests ran in both complete native runs.
- Tests used disposable synthetic projects, isolated user profiles and Git
  configuration, and a test-owned scratch directory. No live project or real user
  runner registry was used. The installed skill was not changed.

The native harness copies source/tests before execution. After the final suite's
snapshot, only one evidence-path docstring was shortened and reporting documents
were updated; runtime behavior and test logic were unchanged.

## Recorded harness runs

Each folder below contains `summary.json` and `tests.log` under the local evidence
folder named later in this file.

- **Original portable baseline:** 84 tests passed; 0 failures/errors/skips; 4.916 seconds. Evidence: `portable-before/`.
- **Original complete native baseline:** 359 tests passed; 0 failures/errors/skips; 423.396 seconds. Evidence: `macos-before/`.
- **Portable run after scalar/restore/PDF repairs:** 90 tests passed; 0 failures/errors/skips; 5.565 seconds. Evidence: `portable-after/`.
- **Final portable run after destination repair:** 90 tests passed; 0 failures/errors/skips; 5.007 seconds. Evidence: `portable-final/`.
- **Final complete native repaired suite:** 378 tests passed; 0 failures/errors/skips; 415.309 seconds. Evidence: `macos-after/`.

These five harness runs account for **1,001 test executions**, including repeats.
That is a run count, not 1,001 distinct tests. Focused tests and exploratory probes
below are separate and overlap the complete suite.

## What we found, fixed and tested

1. **Restore backup names collided within one second.** Added one test that freezes
   the clock, restores three times, verifies earlier checkpoint IDs remain unchanged,
   and extracts all three prior states. It failed on the original implementation
   and passed after the suffix fix. The existing 38 checkpoint tests also passed.
2. **Decoded boolean secrets could remain visible.** Added six tests covering JSON,
   TOML and YAML mappings/lists, YAML flow values, tags, aliases and tags on preceding
   lines. Ordinary settings and quoted strings remain readable as intended. The
   first six-method run exposed 188 failing subcases, and an expanded tag run exposed
   29 failing subcases before correction. All six final methods pass. A supplementary
   comparison against installed PyYAML passed 168 cases; these are reader cases,
   not 168 additional unittest methods.
3. **The read-only inspection recipe could execute Git callbacks.** Reproduced a
   clean-filter write from `git status` and a signature-verifier write from history
   display. Replaced the recipe with guarded inventory/history reads and explicit
   signature suppression. One forward regression verifies unchanged project/Git
   bytes, inodes and modification times, with no callback or trace-file writes.
   Its positive controls prove the unsafe commands trigger the traps. This is a
   documentation correction plus a forward control, not a new runtime Git feature.
4. **Harmless quoted URLs/CSS were rejected in migration plans.** Added one test
   with four quoted-code inputs; three failed before the fix. The focused three-test
   run passed afterward, including actual-resource refusal controls. Independent
   renderer probes passed 15 static cases (10 active loads refused, five harmless
   text cases accepted) and three native malformed-markup cases. The native cases
   produced no PDF and sent zero requests to the loopback recorder.
5. **A check could redirect its saved evidence outside the project.** Added ten
   methods covering state/evidence-folder symlink swaps, in-tree links, replaced
   directories, new ancestor links, normal missing folders, ordinary replacement,
   temporary-name collisions and preexisting directory/FIFO outputs. The initial
   seven-method run exposed five failures. Separate collision and preflight tests
   also failed before their corrections. All ten final methods pass. Post-launch
   changes report integrity status 3 with the child's result retained and no saved
   log; invalid preexisting outputs refuse before launch with status 2. The existing
   25-test scratch/platform/protocol compatibility selection also passed.

The 19 new methods are: restore **1**, scalar masking **6**, inspection **1**,
quoted plan content **1**, evidence destinations **10**.

## Final full-suite breakdown by test file

Counts are extracted from the final native log and total 378 methods. Multiple
subcases inside one method are counted once.

- `test_a1_boundary_regressions.py`: **7 passed**.
- `test_a1_matrix_regressions.py`: **13 passed**.
- `test_a2_corrective.py`: **15 passed**.
- `test_check_registry.py`: **5 passed**.
- `test_checkpoint.py`: **38 passed**.
- `test_childenv.py`: **25 passed**.
- `test_emission_corrective.py`: **7 passed**.
- `test_emission_result.py`: **7 passed**.
- `test_enrolled_isolation.py`: **4 passed**.
- `test_env_literal.py`: **9 passed**.
- `test_evidence.py`: **14 passed**.
- `test_evidence_destination.py`: **10 passed**.
- `test_evidence_node.py`: **2 passed**.
- `test_evidence_readings.py`: **15 passed**.
- `test_evidence_stage1.py`: **9 passed**.
- `test_f3_ambiguous.py`: **7 passed**.
- `test_final_review_r1.py`: **16 passed**.
- `test_final_review_r2.py`: **26 passed**.
- `test_inspection_git.py`: **1 passed**.
- `test_literal_matrix.py`: **4 passed**.
- `test_nested.py`: **12 passed**.
- `test_package.py`: **3 passed**.
- `test_platform_evidence.py`: **6 passed**.
- `test_platform_render.py`: **3 passed**.
- `test_protocol.py`: **8 passed**.
- `test_r2_confidentiality.py`: **10 passed**.
- `test_r2_emission_corrective.py`: **15 passed**.
- `test_r2_status.py`: **7 passed**.
- `test_reader_platform.py`: **5 passed**.
- `test_recovery_review.py`: **7 passed**.
- `test_render_pdf.py`: **28 passed**.
- `test_restore_labels.py`: **1 passed**.
- `test_scratch_retention.py`: **11 passed**.
- `test_secret_scalars.py`: **6 passed**.
- `test_stage1_acceptance.py`: **8 passed**.
- `test_tree.py`: **3 passed**.
- `test_watched.py`: **11 passed**.

## Other validation

- Skill metadata/structure validator: **PASS** (`Skill is valid!`).
- Static skill audit: **0 structural errors before and after**. Seven review
  warnings remain: five subprocess-execution indicators and two historical Desktop
  provenance paths. They are unchanged categories, not seven newly found defects.
- `git diff --check`: **PASS**.
- Final package tests include Python 3.8 syntax compatibility; runtime execution
  here used Python 3.9.6, not native Python 3.8.
- Independent agents reviewed the changed recovery, rendering, scalar parsing,
  destination handling and Windows fixture adapter; no blocking regression was
  found within those diffs. That does not replace the project's release review.

## How to reproduce the main runs

From the repository root, with the documented reader versions and browser prepared:

```sh
/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope portable --output <fresh-evidence-dir>
PATH=<node-v20.20.2-bin>:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin V2E_READER_MATRIX_DIR=<verified-reader-dir> V2E_BROWSER=<headless-browser-path> /Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos --output <fresh-evidence-dir>
```

The native harness requires Node and the complete matrix, and treats a skipped test
as incomplete validation. Browser/localhost tests were run outside the tool sandbox
with approved execution permissions.

## Evidence, backup and limitations

Local evidence folder:
`/Users/mohammadaljaziri/vibe-skill-repair-wRATWw/`.

- Raw main logs and JSON counts: the five run folders listed above.
- Focused raw logs: `render-quoted-*.log`, `v2e-secret-scalars-*.log`,
  `evidence-destination-*.log`, `destination-preflight-*.log`.
- Reviewer records: `checkpoint-render-evidence/result-records.json`. Some earlier
  focused stdout was not redirected to disk; its excerpts are explicitly labeled
  transcriptions. The retained renderer inputs/probe are copied source artifacts.
- Original source backup: `backup-before/`; its digest matched the clean checkout
  before repairs. `baseline.json` records this and the untouched installed copy.
- Static audit packets: `audit-before.json` and `audit-final.json`.

Before package audit digest: `f3901f8408890badff7a4e1e219e069d087467db7d15784ccdaa1ba0aeee2ad2`.

After package audit digest: `7997698f284f02491e5470aa84acac94ac856540635c51e83bb3263de8102b60`.

This is a locally tested development repair candidate, not an approved release.
No new native Windows/Linux run, full human migration workflow exam, fresh-user exam
or owner release acceptance was performed in this task. Those existing gates remain.
No commit, push or installed-skill replacement was performed during testing.
