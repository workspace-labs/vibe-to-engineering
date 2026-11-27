# Skill validation evidence

## Deep review fixes, Round 3 — 2026-11-28

Candidate **0.6.4-dev** builds on approved Round 2 commit `7b3236fe0c7fe121fd4f5ff36b5ec059562ef521`. See the validation instructions in the [README](README.md) for the portable scope and local macOS prerequisites.

- On macOS arm64, Apple Python 3.9.6 and Homebrew Python 3.12.14 each ran all 223 portable methods. Both runs reported 223 passes, zero failures, zero errors and zero skips. All 24 required groups were discovered. The unmodified base passed 206 portable methods on Apple Python.
- Each of the 15 original single-change mutations failed its own run of all 223 portable methods. Twelve mutations failed one method each and three failed two methods each. The completed-file mutation failed four subcases in one method. All mutant runs reported zero errors and zero skips. The checks include both workflow decisions and explicit editorial checks on protected wording.
- The separate native ACL regression also passed on the base, which already contained the refusal. Removing that guard in an isolated copy made the regression fail. The dated Round 3 delivery records the native selection, exclusions and commit-specific results.

## Deep review fixes, Round 2 — 2026-11-27

Candidate **0.6.3-dev** starts at the independently approved Round 1 commit `ef755b8`. Claude approved Round 2 on 2026-11-28 with two carryovers. Claude separately ran all 45 security methods on this Round 2 commit.

- On macOS arm64 the portable scope passed **206 tests** with Apple Python 3.9.6 and **206 tests** with Homebrew Python 3.12.14. Each run reported 0 failures, errors or skips. The unmodified base passed 196 on Apple Python.
- New checks cover confidential names, current approval and allocation, recoverable map publication, watched-file reporting, read-only inspection, protected project writes and runner enrollment. The private-map location guard already worked on the base. Removing it in a disposable copy made its new regression fail.
- Native macOS discovery on the final candidate ran **522 methods** with Apple Python. **495 passed, 0 failed, 0 errors and 27 named exclusions**. The disposable runner marked these active reproduction fixtures as skipped. Of the 45 previously omitted methods, 18 ran and passed on this revision. All four pinned-reader matrix methods passed. The unfiltered native result for this revision remains open.
- Positive printing controls ran with installed Google Chrome and Poppler. Both the base and candidate plans filled seven A4 pages with the landscape overview on page 2. A short map filled one portrait page and an extended map filled three.

## Deep review fixes, Round 1 — 2026-11-27

Claude independently approved **0.6.2-dev** on 2026-11-27 with two confidential-name findings carried into Round 2.

- Both portable selections ran on macOS arm64. Apple Command Line Tools Python 3.9.6 and Python 3.12.14 each passed **196 tests, 0 failures, 0 errors, 0 skips**. The unchanged Apple baseline passed 183.
- Native macOS 27.2.1 with Apple Python 3.9.6 passed **454 selected methods, 0 failures, 0 errors, 0 skips**. Discovery contained 499. The 45 other methods use active vulnerability-reproduction fixtures or share those setups and were excluded locally. Only the selection in the disposable runner changed. All four pinned reader-matrix methods ran with Node 20.20.2. The PDF checks used pinned Chrome Headless Shell revision 1248.
- Against the archived base, both confidential-name CLI tests failed, and the new helper was absent. All three candidate tests passed. The synthetic inventory and both PDFs shared neutral source labels. The printed files were read back with Poppler, and source counts and ordinary names were preserved.
- All three new tool-selection methods, all four secret-source and protected-reading methods, and all five ledger methods failed on the archived base and passed on this candidate. The 74-method portable map group passed. The 14-method native evidence group passed.
- All 23 engineering-standard payloads were compared with upstream commit `cc4e4f1259a439cb94faff651a26454e4ad5f9f9`. The only transformed files were the two guides with offline entrypoint backlinks.
- Selected mutations M08, M09 and M10 were detected. M15 still survived all 196 portable tests. The full native discovery run, hosted candidate validation and whole-skill release exam remain open.

## Migration Map layout on real plans — 2026-11-22

Claude accepted the layout change on 2026-11-22.

Candidate **0.6.1-dev** on `fix/map-real-plan-layout` is based on
`6ffdc45e11ff03164667bc00cc01d74731acf469`. Eight new layout regressions produced
**8 failures, 0 errors, 0 skips** against the archived base and passed on the candidate
with **0 failures, 0 errors, 0 skips**.

- The layout tests cover page breaks with many short source parts, fitting dense source
  headers, row connector positions, exact and inexact range text, whole filenames, shared
  and mixed folders, compact estimates, thousands commas, and the no-source message.
- The pinned browser printed a no-source page and a phase split across two sheets.
  All three are A4. The continuation repeats the title, keeps every file whole,
  and draws only the parts linked on each sheet with the source's full line count.
- The existing two-phase pagination test passes as written. The escaping test uses a
  shorter hostile part label so that it still exercises a visible label.

Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with Node v20.20.2. Native
validation used the pinned reader matrix and Chrome Headless Shell revision 1248 (156.0.8078.4).

- `python3 -B tests/run_validation.py --scope portable` ran **183 tests, 0 failures,
  0 errors, 0 skips**.
- `python3 -B tests/run_validation.py --scope macos` ran **484 tests, 0 failures,
  0 errors, 0 skips**.

The package validator passed. The read-only skill audit found zero structural errors
and the same 31 review notices as the base.

The layout check was a disposable rehearsal on a real-shaped synthetic map with a synthetic approval.
The rendered **one-page A4** PDF contains every one of the **15 whole filenames** and
**34 linked ranges**. The render was inspected as a page image, and both endpoints of
all **34 connectors** were matched against their source parts and destination rows.

## Migration Map re-review fixes J1–J4 — 2026-11-22

Candidate **0.6.0-dev** on `feat/plan-evidence-and-map` is based on
`6c31ca34f38ab04f675107b8403d6184d4d4457d`. All eight targeted test methods failed on
an archive of that commit, with ten failed assertions across their cases. All **62** focused
portable map tests passed on the candidate.

- **J1** An invalid revision that moved a Done phase's file wrote the v2 copy and blocked a
  corrected retry on the base. The candidate checks earlier completions before saving v2.
  The refusal leaves no v2 copy, and the corrected map renders under the same approval.
- **J2** The base accepted a mapped file with no evidence row. The candidate names the missing
  file, then accepts the kept file once its valid evidence row is present.
- **J3** The base left a temporary approval name in place and refused a copy with two links.
  The candidate removes only matching regular temporary files before approval I/O, recovers
  the linked copy and preserves look-alike names, directories and symbolic links. The H3 test
  now requires removal of the matching leftover file. A two-process fixture confirmed that
  a concurrent refresh waits through publication.
- **J4** The base accepted a stop after each of the three final outcomes. The candidate
  refuses each stop in the same run.

Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with Node v20.20.2. Native validation
used the pinned readers and Chrome Headless Shell revision 1248 (156.0.8078.4).

- `python3 -B tests/run_validation.py --scope portable` ran **176 tests, 0 failures,
  0 errors, 0 skips**.
- `python3 -B tests/run_validation.py --scope macos` ran **476 tests, 0 failures,
  0 errors, 0 skips**.

The skill package validator passed. The static audit found zero structural errors and the
same 31 review findings as the base.

A synthetic Harbor Notes plan used the shipped plan template. The invalid v2 exited with
code 1, preserved every fixture file hash and left no v2 approval copy. Correcting only the
map data let the same approved v2 render. The one-page macOS rasterization showed Phase 1
Done, Phase 2 Waiting, one of two files done and Phase 2 approval next. The labels, counts
and source connectors were legible on the page image.

## Migration Map re-review fixes H1–H3 — 2026-11-21

Candidate **0.6.0-dev** on `feat/plan-evidence-and-map`, based on
`f08f43becbfd09ea94df68b05001e034b63f5f48`. The new tests in `tests/test_render_map.py`
produced 28 failures across 12 regression methods on an archive of the base. The new-run
control passed there as well. All **55** focused portable map tests passed on the candidate.

- **H1** The base accepted an outcome with a phase Waiting, Now or Failed, and accepted
  phase and restore events after a final outcome. The candidate refuses those combinations.
  A later approval starts a fresh run.
- **H2** The base accepted swapped or partial exact ranges, `part of` under exact evidence,
  unlisted sources, malformed or out-of-bounds ranges, and mismatches in mixed or multi-source
  cells. The candidate rejects these cases and accepts valid mixed links, two-source cells,
  and equivalent adjacent ranges.
- **H3** The base refused the first render after Phase 1 and a retry following a bad theme
  at approval. The candidate saves the current approved copy before theme and completion
  checks and recovers in both cases. A missing earlier copy still refuses. An abandoned
  temporary file does not block a render. The injected `fsync` failure observed a final copy
  on the base and none on the candidate, where a retry saved the correct data.

Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with Node v20.20.2. Native validation
used the pinned reader matrix and Chrome Headless Shell revision 1248 (156.0.8078.4).

- `python3 -B tests/run_validation.py --scope portable` ran **169 tests, 0 failures,
  0 errors, 0 skips**.
- `python3 -B tests/run_validation.py --scope macos` ran **469 tests, 0 failures,
  0 errors, 0 skips**.

Each scope gained 13 tests. All four reader-matrix tests and the native map PDF test ran.
The governed fingerprints matched the base. The static skill audit reported zero structural
errors and the same 31 review findings on both copies.

The synthetic Harbor Notes plan used the shipped template. Its first map rendered after
Phase 1 and displayed solid and dashed links, one of two files done, and Phase 2 approval
next. The final map displayed All green, two of two files done, and next stop None. Each map
was one page and was rasterized with macOS PDF drawing and inspected. Swapped ranges and a
premature All green each exited with code 1 and preserved the fixture's file hashes.

## Migration Map re-review fixes G1–G4 — 2026-11-21

Candidate **0.6.0-dev** on `feat/plan-evidence-and-map`, based on
`6f27e0d7f6160c802a2d9ff8d7a528a50afe4f82`. The added tests exercised:

- **G1** Retitled and swapped phases, changed completed-file sets, missing and linked approved
  copies, changed map data under the same version, unsafe versions and write-once creation.
  A revision may still omit a completed phase. The original F1 revision test passes.
- **G2** Exact evidence requires the literal value `exact`. Provisional evidence requires
  `not yet exact: <reason>` with a nonempty reason.
- **G3** A file with old lines needs a source link. A new file with `none` in the old-lines
  cell needs exact evidence and an empty link list.
- **G4** Each of the three final outcomes has its own status and `None` as the next stop.

The archived base failed 18 subcases across the ten regression methods. All 42 focused
portable map tests pass on the candidate, including the new positive control for an omitted
completed phase. An injected disk-full error preserved the existing fixture state and let
a retry save the approved copy. A restore and retry case checked completion against the
approval in effect when the phase completed again.

Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with `node --version` reporting
`v20.20.2`. The native run used the pinned reader matrix and Chrome Headless Shell.

- `python3 -B tests/run_validation.py --scope portable` ran **156 tests, 0 failures,
  0 errors, 0 skips**.
- `python3 -B tests/run_validation.py --scope macos` ran **456 tests, 0 failures,
  0 errors, 0 skips**.

Each scope gained eleven tests. The governed fingerprints, PDF renderer and bundled
engineering standard matched the review base.

The synthetic Harbor Notes fixture used the shipped plan template. The v1 map saved its
approved copy before Phase 1. The valid v2 revision preserved Phase 1 Done and showed
Phase 2 approval next. The retitled revision exited with a Phase 1 refusal and preserved
the snapshot and existing outputs. The finished map showed All green, two of two files
done and next stop None. All three pages were rasterized with macOS PDF drawing and
inspected. Text and source-link endpoints were legible.

## Migration Map review fixes F1–F6 — 2026-11-21

Candidate **0.6.0-dev** on `feat/plan-evidence-and-map` after review of
`37391a25293c9f8067795244e54bd79263c4f15e`. Each of the six new tests failed on
the base renderer or plan template and passed after correction.

- **F1** `test_fix_f1_carries_completed_phases_through_plan_revisions` saw Phase 1
  lose its Done state on the base. The fix carries it into the revised plan and
  starts fresh after a completed or stopped run.
- **F2** `test_fix_f2_refuses_an_omitted_planned_new_file` saw the base accept an
  incomplete map. The fix refuses when a new-file row is missing from the map.
- **F3** `test_fix_f3_requires_plan_version_and_fingerprint_from_its_approval` saw
  the base accept an updated hash without approval. The fix checks the visible
  version and the recorded fingerprint before its approval and after any previous approval.
- **F4** `test_fix_f4_requires_map_links_to_match_approved_evidence` saw the base
  accept mismatched or unknown evidence. The fix enforces the plan's evidence
  while allowing mixed links for a file marked `not yet exact`.
- **F5** `test_fix_f5_verifies_listed_source_counts_before_the_first_phase_starts`
  saw the base accept a false count and an unlisted source. The fix checks
  source membership and measures the file before work starts in the current run.
- **F6** `test_approval_explains_checkpoint_limits_and_work_guarantees` saw the
  missing safety wording on the base. The corrected cover restores the exact
  statements and removes the overclaim about named files.

Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with `node --version`
reporting `v20.20.2`. The isolated native run used the pinned reader matrix and browser.

- `python3 -B tests/run_validation.py --scope portable` ran **145 tests, 0 failures,
  0 errors, 0 skips**.
- `python3 -B tests/run_validation.py --scope macos` ran **445 tests, 0 failures,
  0 errors, 0 skips**.

Each scope gained the six regression methods. All governed fingerprints matched the
review base. The existing PDF renderer and engineering standard also matched the base.

The one-page synthetic Lighthouse Log map proved the revision case. On the review base,
the v2 map showed Phase 1 Waiting, zero of two new files done and Prepare baseline.
The corrected PDF showed Phase 1 Done, one of two files done and Phase 2 approval next.
It measured the completed file at 12 lines against the planned range of 10–14. The page
was rasterized with macOS PDF drawing and inspected for legibility and connector placement.

## Plan evidence and Migration Map — 2026-11-21

Candidate **0.6.0-dev** on `feat/plan-evidence-and-map`, based on
`639fc30deffc6f5cda44777207c1846ce9470ecb`. Both scopes used CLT Python 3.9.6
on macOS 27.2.1 arm64 with `node --version` reporting `v20.20.2`. Native validation
used the pinned reader matrix and Chrome Headless Shell revision 1248. The browser startup
refused in the default sandbox. The isolated native run used that same executable with
elevated execution.

- `python3 -B tests/run_validation.py --scope portable` ran **139 tests with 0 failures,
  0 errors and 0 skips**. The increase from 110 is 26 portable map tests and three protocol tests.
- `python3 -B tests/run_validation.py --scope macos` ran **439 tests with 0 failures,
  0 errors and 0 skips**. The increase from 409 includes those 29 tests and one real PDF test
  for the embedded solid and dashed connectors.
- Only the fingerprint for `form: every-file rows` changed.
  It moved from `3c46c5c70ebe418fa6e5745681b01bc47fc424da30b97492ca65c176d8e0163a`
  to `f6669d7c4c53bdde537c3c4a7c21d8aee48744b80b5116c9c7ae19672e3744c3`.
  The bundled standard and PDF renderer matched the base.

### Disposable Harbor Log exercise

- **Planning observed.** A fresh agent used a candidate copy and found two material issues
  in a 444-line source file. The plan showed measured totals of 3 files and 479 lines and
  estimated totals of 5 files and 230 lines, with the largest file in each column. It
  showed line counts on each file row and three new-file rows with source evidence and
  findings. The agent stopped at `AWAITING HUMAN APPROVAL`. All three original files
  matched their starting SHA-256 hashes.
- **Map states observed.** Five playback copies used synthetic ledger headings for approved
  and waiting, started, failed, restored to the checked baseline, and all phases done.
  The done map measured the three synthetic output files, including the approved
  characterization check in the state folder.
- **Visual checks observed.** All 11 plan pages and five one-page maps were rasterized
  with macOS PDF drawing and inspected. Text fit, and solid and dashed connectors reached
  their intended file rows. The fixture plan used compact print spacing. A separate
  render with the shipped stylesheet also showed readable totals and evidence tables.
  Additional large-map renders kept phases together across pages at the original text size.

The playback tested reporting with staged fixture files and ledger events. Real-project use
and independent review remain outside this build evidence.

## Engineering standard 1.11.0 bundle — 2026-11-20

Candidate **0.5.0-dev** on `update/engineering-standard-1.11.0`, based on `main` at
`46f8b759483d34383d048af278156bf9390a4a0d`. The snapshot came from upstream
`v1.11.0` at `15d76887f5b06ac1e22a8b452fe17d425ec196b3`.

- Compared all 23 payloads with the tagged Git blobs. Twenty-two matched byte for byte.
  Only `references/repository-and-delivery.md` differed, by the two exact link substitutions.
  Its upstream and bundled SHA-256 values matched their recorded bytes. All 20 governed
  passages retained their fingerprints.
- `python3 -B tests/run_validation.py --scope portable`: **110 passed, 0 failures, 0 errors,
  0 skips**. `--scope macos`: **409 passed, 0 failures, 0 errors, 0 skips**, including the
  four required reader-matrix tests.
- Both scopes used CLT Python 3.9.6 on macOS 27.2.1 arm64 with `node --version` reporting
  `v20.20.2`. Native validation used Bash 3.2.57, the prepared reader matrix, pinned
  Chrome Headless Shell 156.0.8078.4 (revision 1248) and Poppler 26.07.0.
- Checked out the candidate in a disposable local clone with `core.autocrlf=true`.
  All four snapshot checks passed. The control README used CRLF and all 24 bundle paths
  including the manifest matched the candidate byte for byte.

### Independent planning exercises

Three fresh agents used an exact copy of the candidate skill with disposable synthetic
projects. The first setup copies had indentation errors. Those attempts were set aside
and rerun with fresh agents on syntax-checked copies. Source inventories, transcripts
and planning artifacts were retained outside the repository.

- **Greeting — observed.** The transcript identifies 1.11.0 and its full pin, and the agent
  returned `NO MIGRATION REQUIRED`. All six original files and their inventory matched.
  No migration directory was created and no project check ran.
- **Invoice — observed.** Six commands repeat calculation and formatting, with the recorded
  8% and 9.5% rates. The 12-page PDF, HTML and ledger carry the full pin. The plan preserves
  the six command paths and both rates, and schedules characterization before moving code.
  All nine original files matched. The agent ended at `AWAITING HUMAN APPROVAL` without
  baseline checks, checkpoints or enrollment.
- **Speed target — observed.** The agent cited §45 and applied the layout map's
  `tests/performance/` rule to the check that ran at module import. The plan preserves
  the 50,000-integer workload, five timed runs of the report function and the accepted
  0.050-second maximum on the reference macOS arm64/Python 3.9 workstation. The 10-page PDF,
  HTML and ledger carry the full pin. All four source files matched. The agent ended at
  `AWAITING HUMAN APPROVAL` without baseline checks, checkpoints or enrollment.

Both planning agents retained only the four documented planning files in their fixtures.
The first renderer attempts hit sandbox browser exits. Isolated retries with the same
pinned browser produced the recorded PDFs. Each ledger fingerprint matched its final HTML.

Candidate Windows CI, approved migration execution and release readiness were outside
these checks. The speed target was kept in the plan and was not measured during planning.

## f03 gap fixes — 2026-11-20

Candidate **0.4.1-dev** on `fix/f03-gaps`, based on `main` at `460c3a2`.
The run used macOS 27.2.1 arm64, CLT Python 3.9.6, Node v20.20.2, Bash 3.2.57
at `/bin/sh`, pinned Chrome Headless Shell 156.0.8078.4 (revision 1248) and Poppler 26.07.0.
All four reader-matrix tests ran and passed.

- `/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos`
  with the prepared reader matrix, pinned browser and Node v20.20.2 first on `PATH`.
  **409 passed, 0 failures, 0 errors, 0 skips.** The runner reported `Ran 409 tests in 361.284s` and `OK`.
- All five new regression tests failed as expected against `460c3a2` and passed with the
  candidate wording. All 31 focused protocol, package and standard-alignment tests passed.
- The first native run selected the wrong Node version. It reported 405 tests and one
  reader-matrix setup error. The rerun selected Node v20.20.2 explicitly and passed.

## Abstraction rule — 2026-11-20

Candidate **0.4.0-dev** on `feat/abstraction-rule`, based on `main` at `b9a1b1e`.
The source and tests validated here were committed as `29f23b480393a65a46abb34e9347a8ca3ec142fa`.
The run used macOS 27.2.1 arm64, CLT Python 3.9.6, local Node v20.20.2, Bash 3.2.57
at `/bin/sh`, pinned Chrome Headless Shell 156.0.8078.4 (revision 1248) and Poppler 26.07.0.
The pinned reader matrix ran all four tests.

- `/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos`
  with the prepared reader matrix and browser. **404 passed, 0 failures, 0 errors, 0 skips.**
  The runner reported `Ran 404 tests in 357.240s` and `OK`.
- The new protocol test failed against the original C16 as expected. With the approved
  wording in place, all 26 focused protocol, standard-alignment and package tests passed.
- The first run under the workspace sandbox reported 7 failures and 1 error in 404 tests
  with 0 skips. The loopback bind was denied and the headless browser exited with signal 5.
  The approved rerun used the same source and prerequisites and passed the renderer checks.

## Chrome PDF and FIFO test repairs — 2026-11-20

Candidate **0.3.2-dev** on `fix/chrome-keychain-and-fifo-test`, based on `main` at `728856c`.
Local host was macOS 27.2.1 arm64 with CLT Python 3.9.6, Node v20.20.2 and Poppler 26.07.0.
The native scopes used the pinned reader matrix and ran all four of its tests.

- `tests/run_validation.py --scope macos` with `V2E_BROWSER` pointing to pinned Chrome Headless
  Shell 156.0.8078.4, revision 1248. **403 passed, 0 failures, 0 errors, 0 skips** in 360.319 seconds.
- The same macOS scope with `V2E_BROWSER` unset and installed Google Chrome 157.0.8103.80.
  **403 passed, 0 failures, 0 errors, 0 skips** in 360.811 seconds.
- `tests/run_validation.py --scope portable` with CLT Python 3.9.6.
  **104 passed, 0 failures, 0 errors, 0 skips** in 4.253 seconds.

A direct render of the filled plan template with a fresh empty home and default browser discovery
produced a seven-page PDF in 0.873 seconds with installed Chrome. No blocking keychain dialog was
observed. The modified landscape test also rendered from a fresh empty home under both browser
configurations. The mocked launch regression failed with the macOS switch removed from a disposable
copy and passed with the switch restored. A separate missing-browser check produced the expected
skip for `test_renders_the_template_with_a_landscape_overview_page`
(`no Chrome-family browser installed`). That skip was outside the validation scopes above.

The directory/FIFO regression runs each writer invocation in a subprocess with a five-second
timeout. With the historical writer extracted from `1f44989`, the FIFO reached the timeout and failed
with `Evidence wrapper did not refuse the fifo within 5 seconds`. The old writer also failed the
separate directory assertion. The focused test exited 1 in 5.378 seconds wall time on that writer
and exited 0 in 0.599 seconds on the branch.

This is builder verification on one host. Independent review, full workflow exams and release
approval remain pending.

## Historical safety repairs candidate — 2026-11-20

Candidate **0.3.1-dev** on `fix/unmerged-safety-repairs`, based on `main` at `1f44989`.
The local host ran macOS 27.2.1 arm64, CLT Python 3.9.6, Node v20.20.2, and Poppler 26.07.0.
The workflow pins Chrome Headless Shell 156.0.8078.4 (revision 1248).

- Portable baseline at `1f44989`, `python -B tests/run_validation.py --scope portable` with
  CLT Python 3.9.6. **97 passed, 0 failures, 0 errors, 0 skips.**
- Candidate portable workflow runner with CLT Python 3.9.6 and separately with Python 3.12.14.
  **104 passed, 0 failures, 0 errors, 0 skips** on each interpreter.
- The standard alignment and package tests passed. The bundled standard 1.9.0 and its manifest
  match `1f44989` byte for byte, including after checkout with `core.autocrlf=true`.
- The read-only audit of the source package reported 33 existing findings and the same
  Workspace-specific classification before and after.

The same 10 CLI tests ran on isolated copies of the baseline and candidate. Four methods failed
on the baseline. The checkpoint symlink loop and both unknown-home commands printed tracebacks.
The two trailing-LF label cases reached Git's ref write and left a checkpoint store. Six methods
already passed, including the maximum-length label, invalid UTF-8, same-file paths, symlink aliases,
hard-link aliases and a real browser launch failure. All ten passed on the candidate.

The first native runs used the installed Google Chrome 157.0.8103.80. Chrome wrote the temporary
PDF and then exited with code 2 and a teardown watchdog error in renderer cases. The direct
suite ran **402 tests with 2 failures, 0 errors and 0 skips**. The native workflow runner ran
**402 tests with 3 failures, 0 errors and 0 skips**.

With the workflow's pinned Chrome Headless Shell, the focused `test_render_pdf.py` run passed
**28 tests, 0 failures, 0 errors, 0 skips**.

Both full native runs then used that same pinned browser, mandatory Node and all four tests
in the pinned, hash-verified reader matrix. Both commands used CLT Python 3.9.6.

- README direct suite, `python3 -B -m unittest discover -s tests -v`.
  **402 passed, 0 failures, 0 errors, 0 skips** in 376.902 seconds.
- Workflow runner, `python3 -B tests/run_validation.py --scope macos --output validation-results`.
  **402 passed, 0 failures, 0 errors, 0 skips** in 376.819 seconds.

This is builder verification on one host. The full agent workflow and release gates remain pending.

## File-size alarms and verification warning candidate — 2026-11-20

Candidate: **0.3.0-dev**, branch `feat/file-size-alarms`, based on
`2665259` (`update/engineering-standard-1.4`). Shared standard: **1.9.0** from the local,
unpublished commit `d671ceb987084da7bc0103666bc12fc3d29e6758`. Instruction text, the bundled
snapshot and tests changed. Runtime scripts are unchanged.

Host: macOS 27.2 arm64.

- Portable scope, `python3 -B tests/run_validation.py --scope portable`: **97 tests,
  0 failures, 0 errors, 0 skips** with Homebrew Python 3.15.2 and with system Python 3.9.6
  (91 before this change; six new tests: three in round 1, two in round 2, one in round 3).
- `/usr/bin/python3 -B -m unittest discover -s tests -p test_render_pdf.py`: **27 tests,
  0 failures**. With Homebrew Python 3.15.2 the same file has 3 failures in
  `test_the_browser_runs_no_script_and_loads_no_local_file_whatever_markup_gets_past_the_checks`;
  they fail the same way on the unchanged base and were not investigated here.
- `test_protocol.py`: 8 tests pass.
- **22 of the 23 upstream files** match the pinned commit byte for byte (read from the commit,
  not from a working tree). The other, `references/repository-and-delivery.md`, differs only
  by the recorded link rewrite (two links); undoing it gives the upstream hash in the manifest.
  The link test now also checks each local link's heading anchor.
- Review round 2, on temporary copies, each of eleven reversals made a test fail: the 400 and
  1,000 boundaries made inclusive; the pure-move wording removed; the written reason dropped;
  warning lines dropped from phase reports; a phase allowed to start with an open warning; an
  accepted gap allowed as ALL GREEN; acceptance counted as a pass; a bundled link pointed back
  to the missing `SKILL.md`; a bundled link pointed to a missing heading; the route for a
  project without an example tree removed.
- On disposable copies, each of four changes made a test fail: a 600-line rule added to
  SKILL.md; "File size alone is not a finding" removed from the review-candidate rule; the
  reload/restart example removed; one byte added to the bundled §7 guide.

- Review round 3 added `test_governed_wording_changes_only_on_purpose`, which fingerprints
  fifteen passages, and a wider size-number pattern (1000, 1 000, 1k). On temporary copies,
  21 of 21 reversals made a test fail, among them: an independent 1000-line split rule;
  warnings reassessed only at planning; reruns forced during read-only planning; the warning
  moved out of the Verification section; a baseline started without the warning decision; a
  mixed outcome that hides accepted gaps; a final checkpoint created before the decision;
  a resume list without the accepted-gap outcome; refresh instructions that restore the
  broken links.

- Review round 4 fingerprints nineteen passages (the two instructions in the plan form
  included) and checks each form instruction inside its own table. Still **97 tests**. On
  temporary copies, 12 of 12 new reversals made a test fail, among them the two form changes
  the reviewer named: a forced split added to the 400-line marker line, and the warning
  instruction moved from Verification to Approval. The 21 round-3 reversals still fail.

- Review round 5 corrected one sentence: after a covering check fails at the baseline, reports
  show `Verification Warning: OPEN` until the owner explicitly accepts, and `ACCEPTED BY OWNER`
  only afterwards. Still **97 tests**. Six reversals of the two report states each failed
  twice on temporary copies: with the fingerprint, and with the phrase test run alone.

Not run: the complete native macOS regression suite, the reader matrix, the skill validator,
and any agent exercise of the new wording. These checks show the text and bundle are
consistent; they do not show that an agent follows them.

## Engineering-standard alignment candidate — 2026-11-09

Candidate: **0.2.0-dev**, branch `update/engineering-standard-1.4`, based on Vibe
`bd8133fa474a36694a11452138a1110c0c1ba860`. Shared standard: **1.4.0** from
`a27317b9f7885b18dc6b5eedc24b5dd29d27fdb9`. This is a development source update,
not an installed or released skill. Existing runtime scripts are unchanged.

### Package and renderer checks actually run

Host: macOS 27.2 arm64. Portable checks ran with Homebrew Python 3.15.2 and
system/Xcode Python 3.9.6. The real-browser checks below used system Python 3.9.6.

- Before-change portable baseline: **84 tests, 0 failures, 0 errors, 0 skips**.
- New snapshot checks before implementation: **7 tests, 11 expected assertion failures,
  0 errors** with the bundle/router/form fields absent. After implementation they pass.
- Updated isolated portable scope: **91 tests, 0 failures, 0 errors, 0 skips** on each
  interpreter. The seven new tests are included in the normal portable CI selection.
- `/usr/bin/python3 -B -m unittest discover -s tests -p test_render_pdf.py -v`:
  **27 tests, 0 failures, 0 errors, 0 skips**. The final run was after the template's
  checkpoint-coverage correction. It required isolated headless Chrome and a temporary
  localhost listener outside the tool sandbox. No real browser profile was used.
- Skill Creator `quick_validate.py`: **Skill is valid**, using system Python with its
  already installed YAML package; no dependencies were installed.
- All **24 upstream files** match the pinned commit byte for byte. Tests check manifest
  inventory and hashes, relative link existence and exact case, eleven project families,
  standard/version consistency and absence of a discoverable second skill.
- Read-only skill audit: **0 hard errors**. It reports 34 heuristic review notices:
  seven existing execution/path notices and 27 nesting/navigation notices from preserving
  the upstream snapshot and its relative links. These are not runtime-verification results.
- A seven-page sample plan rendered successfully. Every page was inspected in a contact
  sheet; the changed approval and engineering-basis sections are readable, with no clipped
  content or overlapping tables. This is a layout fixture, not an approved project plan.
- Independent source review: no confirmed defect; the reviewer separately ran the seven
  new tests, checked the 24 upstream files and confirmed unchanged runtime scripts.
  A follow-up review cleared the two corrected checkpoint-coverage paragraphs against G1/G10.

The initial exploratory renderer run under sandboxed Python 3.15.2 failed: localhost binding
was denied, Chrome exited before printing, and that Python parser rejected several legacy
malicious-markup fixtures before they reached the expected browser-policy check. These are
recorded failed attempts, not passes. The documented system-Python run above passed without
changing the renderer or weakening assertions. Python 3.15 browser-suite compatibility is
not established. The default Python also lacked YAML for the external validator; the existing
system-Python installation supplied it.

### Independent agent exercises

The requests and observable conditions are in `tests/behavioral-cases.md`. Fresh agents were
given the actual candidate skill and disposable projects, without the expected architecture.

- Small greeting CLI: agent read the six-file project, verified the 24 manifest hashes,
  selected the CLI guide, returned **NO MIGRATION REQUIRED**, ran no application checks,
  and wrote nothing. Independent before/after inventory and SHA-256 comparison confirmed
  all six files unchanged and no migration directory created.
- Invoice CLI: agent read nine files, verified the same 24 manifest hashes, diagnosed
  duplicated responsibility ownership, and produced a three-phase plan and 13-page PDF.
  It preserved the differing report formula as existing behavior, planned characterization
  before extraction, mapped every file/owner and pinned the standard and selected CLI guide.
  It ended at **AWAITING HUMAN APPROVAL**. Independent source hashes confirmed all nine
  original files unchanged; only plan, ledger, ignore file and an overview preview exist in
  its migration folder. No baseline checks, checkpoint store, enrollment or registry reads
  occurred. The recorded fingerprint matches the actual HTML. The first sandboxed render
  failed before printing; isolated rendering outside the sandbox succeeded. The overview
  page was visually inspected by the exercising agent.

The full native runtime/reader-matrix suite, approved phase execution, interrupted migration,
restore and fresh-user enrollment were not run for this instruction-only update. Earlier
whole-workflow and owner release gates remain open; these results are not whole-skill approval.
Raw local logs, backups and exercise artifacts are retained outside the candidate repository. Installed skills and the older
review checkout are unchanged.

## Repair validation — 2026-10-19

Tested repair revision: [`5dc2245182c6cd3a6e7ccbb227617a3bb362bb31`](https://github.com/workspace-labs/vibe-to-engineering/commit/5dc2245182c6cd3a6e7ccbb227617a3bb362bb31).
Baseline: `7663622963991941a0ca336844e9dbeb6ff4bff3`. Dates in this repair record
use Asia/Dubai; the CI run began on October 18 UTC. The reporting update adds no
runtime or test changes to that repair revision.

**PASS for the completed scopes below.** The current repair has local portable and
renderer/platform evidence, plus completed portable CI on three operating systems.
The complete native macOS CI regression is **PENDING**, observed at
`2026-10-19 00:00 UTC`; no current-revision full-suite count is claimed yet.
The October 8 result of 346 native tests is historical evidence below.

### Local verification

Host: macOS 27.0.1, arm64, Xcode Python 3.9.6. The installed browser's metadata was
checked separately: Google Chrome 155.0.8059.80. Source/revision binding was checked
by comparing the exact repair diff and all 25 package files with the validated
installation before commit; the raw test logs themselves do not embed a commit ID.

```text
python3 -B tests/run_validation.py --scope portable --output <local-evidence-directory>
84 tests; 0 failures; 0 errors; 0 skips; PASS; 4.751 seconds

PYTHONPATH=tests python3 -B -m unittest test_render_pdf test_platform_render -v
Ran 30 tests in 9.674s
OK (0 failures, 0 errors, 0 skips)
```

The portable run used the existing disposable-copy harness and isolated user/Git
configuration. The focused renderer tests used disposable plans and destinations;
the real-browser cases required execution outside the macOS tool sandbox so Chrome
and a localhost test server could start. No production project or real runner
registry was used.

The 30-test selection contains 14 renderer tests, 13 new output-safety regressions
and three renderer platform-boundary tests. The same three platform tests also
occur in the 84-test portable scope: these are **114 test executions covering 111
distinct test methods**, not 114 unique tests. Three renderer methods exercise real
Chrome: landscape rendering, network-fetch prevention, and malicious markup/local
file/script protection. Output-safety cases use a mocked browser.

The new regressions cover input/output collisions, unsafe destinations, native
`/tmp` and `/var/folders` aliases, nonexecutable browser overrides, successful
replacement, and preservation of existing PDFs after launch errors, timeout,
nonzero browser exit, missing/invalid output, content-policy refusal and replacement
failure. Rendering now promotes a temporary output only after successful validation.

Before the Chrome logging correction, the original baseline also failed five
content-policy cases across two existing test methods. Explicit stderr logging
made browser policy reports visible to the existing refusal check; the same
assertions then passed without weakening them. Earlier sandbox-blocked runs and
that failing native run are not counted as passes.

Additional checks passed: the skill-creator package validator, `git diff --check`,
reference-anchor checks, exact installed-package comparison, and the installed
skill's structure/trigger/Claude/Codex audit profiles. Seven static review warnings
remain: five subprocess-execution indicators and two historical Desktop provenance
paths. They were reviewed; zero structural errors or duplicate-name/trigger
conflicts were found for this skill. A workflow dry run checked repeated-failure
labels, historical/approved path references, secret-reporting rules and unsafe
migration-state links. That dry run is not a complete migration workflow exam.

Local raw artifacts are retained outside this repository as
`validation-final/summary.json`, `validation-final/tests.log` and
`renderer-final-tests.log`, alongside the installation proof and repair patch.

### Repair CI

[CI run 39178732501 for the repair revision](https://github.com/workspace-labs/vibe-to-engineering/actions/runs/39178732501)
was inspected directly. Downloaded portable `summary.json` artifacts report:

- Windows Server 2025, AMD64, Python 3.12.10: **84 passed**, zero failures/errors/skips.
- Linux, x86_64, Python 3.12.15: **84 passed**, zero failures/errors/skips.
- macOS 26.6.2, arm64, Python 3.12.10: **84 passed**, zero failures/errors/skips.

The artifacts are `portable-windows-latest`, `portable-ubuntu-latest` and
`portable-macos-latest`; each includes `tests.log` and `summary.json`.
The native arm64 job had passed its Apple-Python portable preflight and reader/browser
preparation, and was executing the complete regression with mandatory readers at
the observation time. Its final result and downloadable native summary must be
checked before replacing PENDING with a full-suite verdict.

### Remaining release gates

These checks do not approve a release or establish migration support on Windows or
Linux. Execution remains macOS-only, and the skill remains `0.1.0-dev` for disposable
projects with synthetic secrets. Complete current-revision native regression,
agent workflow exams, fresh-user verification, final independent release review
and owner release approval remain required under `LASTUPDATE.md`.

## Historical platform validation — 2026-10-08

The following evidence belongs to its explicitly named historical revisions and
CI run. It is retained for provenance and is not a full-suite result for the
October 19 repair.

Repository: workspace-labs/vibe-to-engineering. Baseline: `014e97909f1976993217bb13877e38c9f678b433`.
Review branch: `fix/platform-boundary-review`.

### Scope and verdict

**PASS for the tested scopes:** 346 native macOS regression tests and 84 portable tests
on each of Windows, Linux and macOS, with zero failures, errors or skips. The skill
remains in development with macOS-only execution. Windows and Linux checks
establish safe refusal and selected portable behavior; they do not establish support
for running migrations on those systems. A complete agent workflow exam and owner
release approval remain outstanding.

### Original Windows result

On Windows 11 (10.0.26100), AMD64, Python 3.12.10, the unmodified baseline was tested
in a disposable checkout with isolated HOME, USERPROFILE, AppData, temporary directories
and Git configuration:

```text
python -B -m unittest discover -s tests -v
Ran 303 tests in 24.566s
FAILED (failures=43, errors=555, skipped=57)
```

Failures/errors include subtest events, not that many distinct test methods. This is
not a Windows pass. The original suite assumes macOS execution and reader prerequisites;
unsupported execution is now refused explicitly rather than represented as supported.

### Corrections and focused proof

- Recovery: two issues reproduced in three failing scenarios before fixes; ignored-file changes and
  edited store ignore rules now refuse/report correctly, with a successful-restore control.
- A3: check scratch is retained outside the project; permission and identity checks remain;
  foreign sentinels survive; paths and sensitivity are disclosed through governed output.
- A4: evidence, checkpoint and renderer refuse unsupported platforms before project access,
  enrollment, scratch allocation or check launch. Plain-Python startup tests also guard
  against writing import caches into the skill copy. On macOS the unsupported-platform
  simulation measures a bare Apple-Python startup first: that interpreter may populate
  its own user cache before any script starts. The candidate must add no files afterwards.
  Windows/Linux use their native, unprimed CLI invocation. This does not claim control
  over interpreter startup, operating-system bookkeeping or externally configured hooks.
- Tests isolate Windows and POSIX home resolution before enrolling any runner.
- Reader preparation requires native macOS arm64, Bash 3.2 and local Node v20.20.2.
  Artifact identity tests use synthetic offline fixtures separately from native reader proof.
- Codex metadata, install guidance and the bundled MIT license were corrected.

The standard skill-creator package validator reports `Skill is valid!` on this PC.
Package tests separately check metadata limits, the exact bundled license and Python 3.8
runtime syntax. Syntax validation is not a native Python 3.8 execution test.

### Reproducible validation

```text
python -B tests/run_validation.py --scope portable --output validation-results
```

The selected portable scope is enumerated in `tests/run_validation.py`. It includes
pure logic, protocol wording, fixture containment, recovery unit regressions and platform
refusal. Some tests simulate platforms or filesystem metadata; native Windows/Linux CLI
refusal is also exercised. Unit simulations are not native macOS execution evidence.

On macOS arm64, use Apple Command Line Tools Python 3.9+, Git and cc, Bash 3.2 at
`/bin/sh`, Node v20.20.2, and Poppler's `pdftotext` and `pdfinfo`. CI selects Playwright
1.64.0's headless shell revision 1248. This local example selects full Chrome. The JSON
summary identifies the selected executable with its absolute path, version and SHA-256.

```bash
# Start in the reviewed checkout or its git archive on native macOS arm64.
# Select the installed Node v20.20.2 and either full Chrome or the pinned CI shell.
export V2E_NODE="$(command -v node)"
export V2E_BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
validation_tmp="$(mktemp -d)"
export V2E_READER_MATRIX_DIR="$validation_tmp/readers"
"$V2E_NODE" --version
/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/reader_matrix_prepare.py "$V2E_READER_MATRIX_DIR"
/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos --output "$validation_tmp/results"
```

The runner copies source/tests into a disposable tree, isolates the user profile and Git
configuration, and redirects only that copy's fixed scratch base to a harness-owned
directory. The harness removes its own test fixtures afterwards; production runtime
retains scratch. It never relaxes platform, enrollment or reader gates. The macOS scope
requires Node and the complete matrix; any failure, error or skip fails validation.
Logs and machine-readable counts are saved in `tests.log` and `summary.json` and uploaded
by CI. CI dependency preparation is separate from skill runtime behavior.

### Results and remaining gates

Verified code/test revision: `01f25876205ab1cfaddf6d8a9ebc668cf7583fe6`.
The subsequent evidence update changes only top-level reporting documents.

Portable scope:

| Host | Python | Tests | Failures / errors / skips | Result |
|---|---|---:|---|---|
| This PC: Windows 11, AMD64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |
| GitHub Windows Server 2025, AMD64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |
| GitHub Linux, x86_64 | 3.12.14 | 84 | 0 / 0 / 0 | PASS |
| GitHub macOS 26.6.2, arm64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |
| GitHub macOS 26.6.2, arm64, Apple CLT preflight | 3.9.6 | 84 | 0 / 0 / 0 | PASS |

Complete native macOS regression:

| Host | Python | Tests | Failures / errors / skips | Result |
|---|---|---:|---|---|
| GitHub macOS 26.6.2, arm64 | Apple CLT 3.9.6 | 346 | 0 / 0 / 0 | PASS |

The native run took 644.7 seconds. All four `test_literal_matrix.DifferentialMatrix`
tests ran and passed; Node and matrix requirements were mandatory. Local Node was
v20.20.2; the other readers came from the repository's pinned, hash-verified provenance.
Real PDF tests ran with Playwright 1.64.0's Chromium headless shell, revision 1248.

[Successful CI run, job logs and downloadable summaries](https://github.com/workspace-labs/vibe-to-engineering/actions/runs/37769123814).
Artifacts are `portable-windows-latest`, `portable-ubuntu-latest`, `portable-macos-latest`
and `macos-native-regression` (including the Apple-Python preflight). Each contains
`tests.log` and `summary.json`; the native artifact groups them by validation scope.
Local copies were also retained for this review.

Earlier attempts are not counted as passes. They exposed a simulated-Windows import
failure on macOS and Apple-Python startup-cache writes. The tests now use an explicit
Linux simulation on macOS and the measured startup control described above. A superseded
full-Chrome run stalled during real rendering and was cancelled; final CI uses the
headless browser type used by the historical review. No test was skipped to obtain a pass.

The literal parser (`envliteral.py`), masking/result module (`emission.py`), core Git
guards (`gitrun.py`, `nested.py`) and existing nested-repository fixtures
(`tests/test_nested.py`, `tests/support.py`) have no diff from the baseline. Focused
independent agent reviews found no additional serious regression in the changed recovery,
execution and rendering code. These reviews are not the separately required release review.

The historical September 29 macOS result of 307 passing tests belongs to the baseline
and is not reused as current evidence.
Workflow migrations, no-migration behavior, interruption/resume, approved restore/retry,
baseline failures, data-safety checks, fresh-user validation and final release review
remain required under the existing release checklist in `LASTUPDATE.md`.
