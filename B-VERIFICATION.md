# B — release regression verification (2026-09-30)

Builder: Kimi. Reviewer: Claude (independent). Owner decides acceptance.
Branch `fix/f03-f06-f08-new1`, base `f524fb6` (the C acceptance record on top of `28f5e85`).
Scope: the frozen §5 **B** line and §8(c) of the release handoff
(`~/Desktop/vibe-to-engineering-v01-release-handoff-2026-09-27.md`). A1, A2, A3, A4 and C are
accepted and were not reopened. **No product code changed; no tests added — no gaps were found.**
Every run below used disposable copies and isolated HOMEs; the real `~/.vibe-to-engineering/`
was never touched; old code was run from preserved snapshot trees or `git archive` extractions,
never by checking out the shared tree.

Environment for every run: macOS arm64, CLT Python 3.9.6 (`/Library/Developer/CommandLineTools/usr/bin/python3 -B`),
Node v20.20.2 where required, the hash-verified reader matrix at `/tmp/v2e-r123-work-tzvzLCWM/readers`.
Raw logs: `/tmp/v2e-B-verify/runs/` (this machine's scratch; the table below is the record).

## 1. Old-code candidates — found, identity-checked, or missing

Every snapshot tree used was re-verified file-by-file against its own bundle manifest
(sha256 + size + mode) before any run: **all six matched, zero mismatches, zero missing, zero
extra files** (verifier: `/tmp/v2e-B-verify/check_tree.py`). The snapshot lineage was also
cross-checked by content hash: the `evidence.py` chain A2-delivery `after` == A2-fix `before`
(`ee893b1a…`), A2-fix `after` == R2-slice `before` (`b1ac4677…`), R2-corrective `after` ==
F3-R1-fix `before` (`af13a5fe…`, with `emission.py` `2a90b133…`), and today's `emission.py` ==
F3-R1-fix `after` (`b4525b02…`). Commit `014e979`'s `evidence.py`/`emission.py` are
byte-identical to the F3-R1-fixed snapshot — the git archive and the snapshot chain agree.

| Candidate | Where | Identity proof | Guards |
|---|---|---|---|
| pre-A2 (post-A1 acceptance) | `~/Desktop/vibe-to-engineering-A2-2026-09-28/before/` | 49/49 files match `evidence/source-before.json`; no `enroll_runner` in evidence.py | R2-F5 |
| post-A2, pre-confidentiality/status-slice | `~/Desktop/vibe-to-engineering-R2-F2-F3-F4-F6-fix-2026-09-28/before/` | 52/52 match `evidence/before-manifest.json`; bundle records byte/mode/hash equality with the accepted A2 tree; `evidence.py` == A2-fix `after`; no `emission.py` | R2-F2, F3, F4, F6; confidentiality battery; exit-status matrix |
| R2-slice-reviewed (slice v1) | `~/Desktop/vibe-to-engineering-R2-F2-F3-F4-F6-corrective-2026-09-28/before/` | 55/55 match `evidence/before-manifest.json`; == review-candidate manifest sha256 `c2be392f…` | R2-F2/F3/F6 corrective regressions |
| F3-R1-reviewed | `~/Desktop/vibe-to-engineering-F3-R1-fix-2026-09-28/before/` | 60/60 match `evidence/before-manifest.json`; `evidence.py`/`emission.py` == R2-corrective `after` | F3-R1 |
| A2-reviewed (A2-F01–F03 present) | `~/Desktop/vibe-to-engineering-A2-fix-2026-09-28/before/` | 51/51 match `evidence/before-manifest.json`; `evidence.py` == A2-delivery `after` | A2 corrective |
| A1-reviewed (A1-F01–F04 present) | `~/Desktop/vibe-to-engineering-A1-fix-2026-09-28/before/` | 46/46 match `evidence/source-before.json` | A1 corrective |
| Slice parents / review bases | `git archive` of `014e979` (A3 parent), `569c8f9`, `9204241`, `cc5b862`, `87709ab`, `46114bc`, `89d8151`, `79bd7a2` (A3 rounds), `ef21f2b` (A4 parent), `99c8ebf` (C parent), `7dd2193` (C-round parent) | real commits; `014e979` cross-checked byte-identical to the F3-R1-fixed snapshot | A3 and sub-rounds, A4, C |
| **R1-reviewed candidate — MISSING** | was `/private/tmp/v2e-stage1-review.XDXqmT` (recorded in `~/Desktop/vibe-to-engineering-r2-resume-2026-09-27.md` §"Candidates"); wiped with `/tmp`; never committed; the 2026-09-25/26 resume folders preserve only the pre-stage-1 round-9 state, not the reviewed stage-1 tree | — | R1's 16 (historical record below) |
| **pre-A1 (pre-boundary) tree — MISSING** | was `/tmp/v2e-r2.W7i5Qq` (same resume doc); wiped; the boundary's own fail-before from pre-boundary code exists only as the retained logs in the A1 bundles (`matrix-red.log` FAILED failures=20; `boundary-red-corrected.log`) | — | A1 slice's own boundary tests (see §2 row A1) |

No candidate is a copy of today's tree; every "before" tree predates its slice and fails the
slice's tests on the old behavior, which no copy of today's code can do.

## 2. Traceability table — every frozen B obligation

"Fail-before" runs are today's (2026-09-30) test files against the old code named, by one of
two equivalent harnesses: (a) `V2E_EVIDENCE=<candidate>/skills/vibe-to-engineering/scripts/evidence.py`
from the repository root (the seam the R2 files document — used for the snapshot candidates);
(b) overlaying today's `tests/` onto a disposable copy of the old tree and running there (used
for the git-archive slice bases and the A1 corrective — covers seam-less files such as
`test_childenv.py`, `test_a4_platform.py` and the docs tests, which resolve code and documents
via the tree root). Both mean the same thing: old product code, current tests. "Pass-now" for
every row is the full suite in §6 plus the per-file green runs it contains.

| # | Obligation | Guarding tests (file → class/tests) | Old code it must fail on | Fail-before result (2026-09-30 runs) | Pass-now |
|---|---|---|---|---|---|
| F1 | R2-F1 scratch deletion — closed by A3 (never deletes) | `tests/test_evidence_stage1.py::test_the_scratch_root_is_retained_when_the_run_ends_however_it_ends`; `tests/test_childenv.py` retention set (8 tests); `tests/test_final_review_r1.py` F1 retention battery (4 tests); `tests/test_stage1_acceptance.py::test_every_refusal_means_no_launch_and_no_evidence` (retained-root counts) | `014e979` (deletion era) | FAIL/ERROR as promised: the retention test and the refusal-count test FAIL (0 roots left where 2/4 retained now; the `test_evidence_stage1.py` constructed-environment test also fails on the `/tmp` base); the 8 retention-API tests ERROR (`childenv.retain` absent pre-A3); preserved behavior passes | suite §6 |
| F2 | R2-F2 complete-output masking | `tests/test_final_review_r2.py::Emission` (6 F2 methods: mask label, mutual name/value, short/numeric, mask-syntax collisions, settings summary, every argument order/spelling) + confidentiality battery (row CB) + `test_emission_corrective.py` | post-A2 pre-slice | All 6 methods FAIL on the leaked bytes (the file: 24 failures total incl. F3/F4/F6) | suite §6 |
| F3 | R2-F3 (+F3-R1) refusal diagnostics | `…::Emission` (5 F3 methods: the original duplicate counterexample, early-argument, prohibited/held names, malformed settings, parser errors) + `tests/test_f3_ambiguous.py` (7) | post-A2 pre-slice; F3-R1-reviewed | All 5 FAIL on the old candidate; `test_f3_ambiguous.py`: **51 failures, 0 errors/skips** — exactly the recorded historical 51 | suite §6 |
| F4 | R2-F4 recorded paths | `…::RecordedPaths` (2) | post-A2 pre-slice | Both FAIL (header attested the retargeted folder; a removed link threw the run's evidence away as exit 2) | suite §6 |
| F5 | R2-F5 runner identity (A2) | `…::RunnerIdentity` (10: untrusted-candidate execution, enrollment disclosure/approval, approval never reused, launched-bytes hash, replaced binary, retargeted symlink, mid-run swaps both pin modes, malformed registry, script under a runner's name, neither-pin-mode) + `tests/test_a2_corrective.py` (15) + `tests/test_check_registry.py` (5, current-contract; no old-code seam — see §5 caveats) | pre-A2 (RunnerIdentity); A2-reviewed (corrective) | RunnerIdentity: **all 10 FAIL, 46 failures file-wide, 0 errors/skips**; `test_a2_corrective.py`: **failures=11, errors=2** (the 2 error on `no_acl`, an API the corrective added — absent on the reviewed code) | suite §6 |
| F6 | R2-F6 wrapper status namespace | `…::WrapperStatus` (3) + exit-status matrix (row SM) + `tests/test_emission_result.py` (7) | post-A2 pre-slice; R2-slice-reviewed | WrapperStatus: all 3 FAIL (child exit 2 → wrapper 2; signal collapsed; failed check not recorded); `test_emission_result.py`: 235 errors — `emission.report`/`read_result` absent pre-corrective (representation unit tests; the behavioral F6 proof is WrapperStatus/StatusMatrix) | suite §6 |
| F7 | interpolation models removed/unreachable | A1 refusal tests (`test_evidence_stage1.py::test_old_npm_dotenv_interpolation_is_refused_by_the_boundary`, `test_final_review_r1.py::test_a_shell_reading_the_file_does_not_decide_is_refused_by_the_boundary`, the `test_evidence_readings.py` refusal sets) + matrix (row MX) | — (state proof, §3) | models unreachable — §3 grep proof; refusals green | suite §6 |
| F8 | (same class as F7) | same | — | same | suite §6 |
| CB | confidentiality battery over the single emission choke point, incl. adversarial `--env` name/value pairs | `tests/test_r2_confidentiality.py` (12-case deterministic adversarial CLI battery over evidence/stdout/stderr + 9 emission unit tests) + `tests/test_r2_emission_corrective.py` (15) | post-A2 pre-slice; R2-slice-reviewed | Battery: **12/12 cases FAIL on leaked bytes** (failures=12); the 9 unit tests SKIP by design (emission module absent pre-slice — the file's documented convention; the CLI battery is the fail-before proof). Corrective regressions: **failures=39** (behavioral) | suite §6 (0 skips there: emission present) |
| SM | full exit-status matrix (wrapper 0/1/2/3; child outcome as data) | `tests/test_r2_status.py` (7: child exits 0/1/2/3/7 + SIGTERM/SIGKILL as data under wrapper 0; launch-failure and evidence-write-failure wrapper 1; four pre-launch refusal shapes wrapper 2; post-launch and integrity failures wrapper 3) | post-A2 pre-slice | **failures=9, errors=1**: every child-outcome/signal row fails (old wrapper leaked child codes/signals); the post-launch row fails (came back exit 2); the evidence-write row fails on the missing recorded outcome; the integrity row ERRORs — it patches `childenv.retain`, the A3 hook absent pre-A3 (era equivalent: `cleanup`); the preserved rows (pre-launch refusals, launch failure) PASS, exactly as the file's header documents | suite §6 |
| SB | swap battery at the runner gate | `…::RunnerIdentity` swap tests (replaced binary, retargeted symlink, mid-run swap under pin copy and pin path — compiled lookalike binaries with marker payloads) + `test_a2_corrective.py` swap/race battery | pre-A2; A2-reviewed | RunnerIdentity swap tests all FAIL on pre-A2 (substitutes executed/markers written; unenrolled probed-and-launched); corrective battery 11 failures + 2 absent-API errors on the A2-reviewed code | suite §6 |
| R1 | R1's 16 regressions green | `tests/test_final_review_r1.py` (16 tests) | R1-reviewed candidate — **MISSING** (§1) | not re-runnable — candidate gone; historical record: "one regression test per R1 finding, each failing against the reviewed candidate: **20 failures + 1 error** there, all passing after" (`references/stage1-acceptance.md`, 2026-09-27). Today's file (re-pointed at A3 retention) vs `014e979`: failures=2, errors=1 (retention battery) | suite §6 (16/16 green) |
| A1 | literal `.env` boundary + corrective | `tests/test_env_literal.py` (9), `tests/test_literal_matrix.py` (4, row MX), `tests/test_a1_boundary_regressions.py` (7), `tests/test_a1_matrix_regressions.py` (13) | pre-A1 tree MISSING (§1); A1-reviewed for the corrective | Corrective: era boundary file (assertions identical to today's — only the HOME fixture predates A2 enrollment) + today's matrix file vs A1-reviewed: **20 tests, 282 failing subtests**, exactly the bundle's recorded `final-fail-before.log`. Today's boundary file vs the same pre-A2 candidate: 24 errors at the A2 enrollment fixture (`enroll_runner` absent) — era-fixture caveat, §5. Slice-level: historical red logs retained in the A1 bundles | suite §6 |
| A2 | runner identity slice | row F5 files | pre-A2; A2-reviewed | see F5/SB rows | suite §6 |
| A3 | scratch retention slice | A3-touched guard files: `test_childenv.py`, `test_final_review_r1.py`, `test_evidence_stage1.py`, `test_stage1_acceptance.py` | `014e979` (slice parent) | failures=2+2+1 and errors=8+1 across the four files — every failure/error is the retention semantics (roots deleted at end then; `/tmp` base; no `retain`); all preserved behavior passes | suite §6 |
| A3-F1–F5 | first corrective | `tests/test_a3_corrective.py` F classes | `569c8f9` | failures=13, errors=3 (the 3 errors are later-round hooks — N3 containment, held-descriptor — absent at this base; the file header documents "fails (or errors)") | suite §6 |
| A3-N1–N5 | second corrective | same file, N classes | `9204241` | failures=16, errors=0 | suite §6 |
| A3-P1–P5 | third corrective | same file, P classes | `cc5b862` | failures=9, errors=2 (2 errors = Q-era hooks absent) | suite §6 |
| A3-Q1–Q2 | fourth corrective | same file, Q tests + held-descriptor companion | `87709ab` | failures=7, errors=0 — fails, never errors (the R3 hygiene repair holds) | suite §6 |
| A3-R1–R3 | owner's three Low leftovers | `tests/test_a3_r1_r2.py` (6); companion "a failed base check" case in `test_a3_corrective.py`; R3's Q1 hygiene in the 87709ab row | `46114bc` | `test_a3_r1_r2.py`: **6/6 FAIL**, each on the defect-proving assertion (e.g. descriptor never closed on the failed-base-check path); companion proof fails on exactly its new "a failed base check" case; `test_final_review_r1.py` vs `46114bc`: 16/16 OK (R3's changes there are test hygiene — nothing in that file was promised to fail on this base) | suite §6 |
| A3-L1–L2 | review's two Low findings | `tests/test_a3_r1_r2.py` (L1 swap-then-fail-open test; L2 true-Q2-mismatch test) | `89d8151` | failures=1 — exactly L1's test. L2's passes on `89d8151` by design (the branch was already correct; the gap was coverage) and fails on `46114bc` (shown in the R1–R3 run) | suite §6 |
| A3-L3 | canary de-flake, tests only | `tests/test_env_literal.py` + `tests/test_evidence_stage1.py` (full-canary assertions) | `79bd7a2` with forced root names | disposable `79bd7a2` copy patched to force root names starting `9137` (`v2e-run-9137…`): its own `test_env_literal.py` → **6 failures** (the six refusal subtests trip on `-9137`), its `test_evidence_stage1.py` OK. Same forcing on the final code: **both files OK** — reproduces the recorded history exactly | suite §6 |
| A4 | platform refusal | `tests/test_a4_platform.py` (4: 3 entry points × {linux, win32, freebsd14} + darwin control) | `ef21f2b` (slice parent) | **failures=9** (3×3 refusal grid), darwin control passes — matches the recorded 9 | suite §6 |
| C | documentation correctness | `tests/test_c_wording.py` (7) | `99c8ebf` (slice parent); `7dd2193` (review-round base) | vs `99c8ebf`: **failures=7** (all seven); vs `7dd2193`: **failures=4** — exactly the four methods the M1/D1 round extended. Both match the recorded counts | suite §6 |
| PROTO | `test_protocol.py` green after the wording changes | `tests/test_protocol.py` (8) | — (current-contract wording guard; no old-code obligation) | — | suite §6 (8/8 green) |

## 3. F7/F8 — interpolation models and their tests

- `scripts/nodekeys.py` (the ported Node/dotenv loader profiles incl. `old_npm_interpolated`)
  **is present but unreachable**: no `import nodekeys` / `from nodekeys` exists in any `.py`
  file in the repository (grep-verified 2026-09-30; the two mentions in `evidence.py:495` and
  README are comments/"provenance record; not wired"). `references/env-boundary.md` records the
  retention-as-provenance decision; physical removal is a separate owner decision (checklist B1).
- The shell word/expansion machinery in `secretforms.py` is no longer called by the `.env`
  reader: `secretformats.py` reads `.env` exclusively through `envliteral`
  (`from envliteral import NotLiteral, assignments`, line 24).
- The models' tests are gone as model tests: no test file imports `nodekeys`; the era's
  interpolation/computation expectations survive only as refusal tests (mapping in §4).
- A1's differential-refusal matrix covers the class: `tests/test_literal_matrix.py`'s four tests
  (`test_every_divergent_form_refuses`, `test_every_claimed_reader_stays_inside_the_masked_set`,
  `test_a1_counterexamples_are_real_reader_disagreements_and_refused`,
  `test_dotenv_0_5_0s_recorded_limitation_stands`) run live against the sha256-verified reader
  set (95 readers: bash 3.2 `/bin/sh`, Node v20.7.0/v20.20.2/v22.0.0/v22.16.0/v24.21.0/v26.10.0,
  dotenv 0.4.0–18.0.4, python-dotenv 1.2.3). Under `V2E_REQUIRE_MATRIX=1` a missing/unverified
  reader is a failure, never a skip. All four ran and passed in the §6 suite — not skipped.

## 4. Superseded expectations (§8(c)) — mapping and reasons on record

Owner-approved rule: regressions preserved where behavior stays supported; superseded
expectations replaced by explicit refusal tests with the mapping and reason recorded.

A1 era — mapping recorded in `references/env-boundary.md` ("Regression supersession mapping")
plus a `# SUPERSEDED (A1 literal boundary, 2026-09-27):` comment at each changed test:

1. `test_old_npm_dotenv_interpolation_is_computed_from_known_inputs` →
   `test_old_npm_dotenv_interpolation_is_refused_by_the_boundary` (`test_evidence_stage1.py`) —
   a `$` anywhere in a value refuses before launch; the ported model is unwired.
2. `test_a_value_python_dotenv_takes_from_the_environment_is_computed_never_guessed` (B6) →
   refusal cases in `test_evidence_readings.py`; one case (`DB_PASSWORD=from-file`) kept green
   as literal — reason recorded at env-boundary.md.
3. The two B4 skipped-part masking tests (`test_a_construct_in_a_part_the_shell_skips…`,
   `test_valid_syntax_in_a_part_the_shell_skips…`) → refusal: `${…}` refuses regardless of skip
   analysis; refused cases retained.
4. `test_a_shell_reading_the_file_does_not_decide_is_computed_from_the_constructed_environment`
   (the R1-F7 mechanism) → `…_is_refused_by_the_boundary` (`test_final_review_r1.py`) — declared
   and undeclared reference cases both refuse.
5. The shell-expansion masked cases in `test_a_yaml_tag_or_a_shell_expansion…` → refusal (`$` or
   backtick anywhere; a line past one literal assignment); YAML masked cases and refused cases
   retained.
6. The arithmetic/`${#NAME}`/`~` parts of `test_a_real_shell_reads_only_what_the_model_reads` →
   refusal assertions (`test_stage1_acceptance.py`), the test rewritten over the literal subset
   against the real `/bin/sh`.
7. The further recorded mechanical supersessions, each with its reason at env-boundary.md:
   `test_a_shell_value_is_read_with_the_shell_s_own_variables…`,
   `test_a_reference_the_file_does_not_decide_is_computed…`,
   `test_a_value_the_file_does_not_decide_stops_the_run…`, `test_no_inherited_function…`,
   `test_json_text_in_a_env_file…` (*one masked case mechanically contradicted — recorded*),
   `test_a_home_folder_the_user_database_decides_stops_the_run` (B5),
   `test_a_name_followed_by_anything_but_an_operator…`,
   `test_a_backslash_before_a_byte_bash_keeps_its_escape_byte_for_stops_the_run`,
   `test_the_reader_alone_without_the_mapping_still_refuses` (with-mapping half),
   `test_evidence_node.py`'s two NODE-PRECEDENCE tests (three comment-only fixtures kept green),
   and `test_evidence.py`'s contradicted `.env` cases across seven methods (six
   admitted-but-reclassified fixtures kept with corrected exact-output expectations, recorded in
   the tests' supersession comments).

R2 slice era — mapping recorded in the slice's regression-mapping record
(`~/Desktop/vibe-to-engineering-R2-F2-F3-F4-F6-fix-2026-09-28/evidence/regression-mapping.md`)
and `references/emission-boundary.md`:

8. `test_evidence.py::test_no_secret_value_reaches_the_evidence_file_or_the_screen` — the child
   exit-3 passthrough → wrapper 0 + `the check exited 3` as data (owner decision 5.3); every
   original masking assertion stands.
9. `test_childenv.py::test_construct_builds_profile_plus_declared_over_one_fresh_root` —
   `construct()` returns the validated `--with-path` entries (R2-F4); new retargeted-symlink
   boundary test added.
10. `test_r2_confidentiality.py`'s body-only scan exception for single-character values and its
    conditional outcome exemption → whole-surface scan and a recoverable-outcome assertion for
    every case (R2-F2/F6 corrective; emission-boundary.md).

A3 era — an owner-decided behavior replacement (decision 3.4), mapped with its reason in the
CHANGELOG's 2026-09-29 A3 entry and the test comments (`test_childenv.py` retention section,
`test_final_review_r1.py`'s F1 note):

11. Scratch-root deletion at run end (`childenv.cleanup`) → retention (`childenv.retain`): the
    deletion-era expectations re-pointed — the end-of-run test now asserts the root is RETAINED
    (`test_evidence_stage1.py`), the R1 swap/link/moved-root battery re-pointed at retention
    (`test_final_review_r1.py` F1 tests), refusal root-count expectations updated
    (`test_stage1_acceptance.py`, `test_evidence_stage1.py`), and the wrapper-3 wording updated
    (`test_r2_status.py` header). Reason: a tool that never deletes can never delete data the run
    did not make (R2-F1 closed by construction).

No superseded expectation lacks a replacement test or a recorded reason.

## 5. F03 seal (re-verified 2026-09-30 at this gate)

- `scripts/gitrun.py`, `scripts/nested.py`, `tests/test_nested.py`: **byte-identical to
  `04d941d`** (git blob hashes equal at both commits).
- `references/recovery.md` differs from `04d941d` by exactly the two approved narrow unseals and
  nothing else (per-commit diffs):
  - **A4 (`ef21f2b`→`b3ad397`), 3 lines:** the `(Windows: py -3 …)` usage suffix dropped; the
    Linux and Windows bullets become "roadmap, not yet validated — this release refuses to run
    there".
  - **D1 (`b3ad397`→`28f5e85`), 4 spots:** G10 gains the comparison-limit sentence ("does not
    prove the absence of reads, remote writes or temporary changes…"); section 3's "so the same
    files run on every platform" becomes macOS-only-with-roadmap; the macOS bullet reads
    "supported in 0.1.0 (all tests pass; release exam pending)"; the Windows bullet's "keeps
    everything" becomes "keeps its saved-file set". `7dd2193` (C's doc commit) did not touch the
    file; `04d941d`→`ef21f2b` and `28f5e85`→HEAD are empty for it.

## 6. Full suite — final tree

_RUN_1 (pre-commit, disposable copy of the exact final content; identity with the commit proven
in §7):_

```
HOME=<disposable empty dir> \
PATH=/Users/mohammadaljaziri/.nvm/versions/node/v20.20.2/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin \
V2E_REQUIRE_NODE=1 V2E_REQUIRE_MATRIX=1 \
V2E_READER_MATRIX_DIR=/tmp/v2e-r123-work-tzvzLCWM/readers \
V2E_BROWSER=/Users/mohammadaljaziri/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell \
/Library/Developer/CommandLineTools/usr/bin/python3 -B -m unittest discover -s tests -v
```

Result: **346 tests, OK — zero failures, errors or skips — in 296.6 s** (2026-09-30; log
`/tmp/v2e-B-verify/runs/full-suite-run1.log`). The four reader-matrix tests all ran and passed
(`ok`, none skipped); the reader artifacts were re-verified by the matrix itself under
`V2E_REQUIRE_MATRIX=1`. The tested copy holds this file and the three status docs with the
suite-result strings filled in after the run — files no test reads (grep-verified); the
delivery handoff reports the commit hash, the byte-identity check against the committed tree,
and the confirmation re-run on the committed archive.

## 7. Gaps, caveats, limitations

- **Gaps: none.** Every frozen B obligation has a working guard that was proven fail-before on
  the real old code it guards and pass-now on the final tree. No tests were added; no behavior
  changed.
- **R1's 16:** the R1-reviewed candidate is gone (§1) — the fail-before stands on the recorded
  2026-09-27 evidence (20 failures + 1 error, all passing after), quoted from
  `references/stage1-acceptance.md`; the 16 pass now. This row is "historical evidence +
  pass-now", not a fresh fail-before.
- **A1 slice (pre-boundary):** the pre-A1 tree is gone (§1); the boundary-era fail-before is the
  retained red logs in the A1 bundles. The A1 *corrective* fail-before was re-run fresh (282
  failing subtests, matching the recorded log exactly). Today's `test_a1_boundary_regressions.py`
  cannot itself run against the pre-A2 candidate (its A2 enrollment fixture errors there — 24
  errors, `enroll_runner` absent); the era version of that file differs only in the HOME fixture
  and carries byte-identical assertions.
- **`test_emission_result.py`** fail-before is API-absence errors (235), not behavioral failures
  — the result-transport representation it unit-tests did not exist pre-corrective; the
  behavioral F6 proof is carried by `WrapperStatus`/`StatusMatrix`.
- **`test_r2_status.py`'s integrity row** errors on pre-A3 candidates (it patches the A3
  `retain` hook; the era hook was `cleanup`) — recorded, not rounded up; the sibling post-launch
  row fails behaviorally on the same candidate.
- **`RunnerIdentity` vs the post-A2 candidate:** 9/10 pass (the A2 repair is present there); the
  tenth fails only on the A3-repointed scratch-base assertion (the pin-copy path moved from
  `/tmp` to `~/.vibe-to-engineering/runs` in A3) — an expected era mismatch, not an F5 defect.
  F5's designated fail-before candidate is pre-A2, where all ten fail.
- **`test_check_registry.py`** (5 tests) has no old-code seam and exercises the current
  enrollment API in-process; it is a current-contract guard — pass-now only, no fail-before run.
- The readers folder `/tmp/v2e-r123-work-tzvzLCWM/readers` was present and is re-verified by the
  matrix tests themselves (artifact sha256, extracted trees, entry paths, harness) on every run
  under `V2E_REQUIRE_MATRIX=1`.
- macOS arm64 only, CLT Python 3.9.6, Node v20.20.2 — this establishes nothing about Linux or
  Windows (A4's boundary, not B's).
