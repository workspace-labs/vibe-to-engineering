# Latest update — 2026-11-21

## November 21 Migration Map re-review fixes

Version **0.6.0-dev** on `feat/plan-evidence-and-map` addresses G1–G4 from the review of
`6f27e0d`. The map uses a write-once copy of each approved version to check which work
was completed. It enforces the plan's evidence wording and source links and displays the
recorded outcome when the migration finishes.

Portable validation passed **156** tests and native macOS validation passed **456**, with
zero failures, errors or skips. A synthetic run kept Phase 1 Done through a valid revision,
refused a retitled Phase 1 and showed All green with next stop None after the final outcome.
See [TEST-EVIDENCE.md](TEST-EVIDENCE.md). Claude's re-review follows.

## November 21 Migration Map review fixes

Version **0.6.0-dev** stays on `feat/plan-evidence-and-map`. This fix round addresses Claude's
six findings on `37391a2`. The map preserves completed work across revisions and checks every
planned new file, evidence flags, the approved plan fingerprint and the source counts before
work begins. The plan cover again gives the checkpoint limits and work guarantees.

Each regression failed against the review base and passed with the fix. Portable validation
passed **145** tests and native macOS validation passed **445**, with zero failures, errors or
skips. The synthetic revision proof showed Phase 1 Done and Phase 2 approval next. See
[TEST-EVIDENCE.md](TEST-EVIDENCE.md). Claude's re-review follows.

## November 21 plan evidence and Migration Map

Version **0.6.0-dev** on `feat/plan-evidence-and-map` starts from `main` at `639fc30`.
Real-project planning can produce a PDF, and approval produces a separate ledger-backed map.
Backup, baseline checks, runner enrollment and migration phases remain limited to disposable
projects with synthetic secrets. The plan shows measured and estimated sizes and the source
ranges, findings and reasons for new files.

Portable validation passed **139** tests and native macOS validation passed **439**, both with
zero failures, errors or skips. A fresh agent stopped at plan approval on the synthetic Harbor
Log project. Five simulated ledger states produced five one-page maps. The test and PDF evidence
is in [TEST-EVIDENCE.md](TEST-EVIDENCE.md). This candidate is ready for Claude's independent review.

## November 20 engineering standard 1.11.0 bundle

Version **0.5.0-dev** on `update/engineering-standard-1.11.0` is based on `main` at
`46f8b75`. The offline bundle now pins standard **1.11.0** at
`15d76887f5b06ac1e22a8b452fe17d425ec196b3`. The tagged Git blobs matched 22 bundled
files exactly. The remaining guide differed only by its two prescribed link substitutions,
and both hashes matched.

Portable validation passed 110 tests and native macOS validation passed 409, each with
zero failures, errors or skips. The CRLF checkout passed four snapshot checks. The greeting
exercise stopped without a plan. The invoice and speed-target exercises presented plans
with the new pin and stopped for owner approval. See [validation evidence](TEST-EVIDENCE.md)
for the commands, observations and limits.

## November 20 f03 gap fixes

Version **0.4.1-dev** on `fix/f03-gaps` is based on `main` at `460c3a2`.
The skill removes machine-specific paths from evidence references, reserves runner enrollment
approval for the human, and explains the owner's migration option after a no-migration verdict.
It states the limits of checkpoint comparisons in reports and directs checks to throwaway data
when the boundary refuses a real `.env`.

Native macOS validation passed all 409 tests with zero failures, errors or skips. Each of the
five new regression tests failed on the baseline and passed on the candidate. See the
[validation evidence](TEST-EVIDENCE.md).

## November 20 abstraction rule

Version **0.4.0-dev** on `feat/abstraction-rule` is based on `main` at `b9a1b1e`.
The tested source commit is `29f23b480393a65a46abb34e9347a8ca3ec142fa`.
C16 now requires evidence that an abstraction solves a present problem and that the
simplest design needs it. Each proposed abstraction gets its own Key decisions row.

Native validation passed all 404 tests with zero failures, errors or skips on macOS 27.2.1
arm64 with CLT Python 3.9.6, Node v20.20.2, Bash 3.2.57, pinned Chrome Headless Shell
156.0.8078.4 (revision 1248) and Poppler 26.07.0. See the [validation evidence](TEST-EVIDENCE.md).

## November 20 Chrome PDF and FIFO test repairs

Version **0.3.2-dev** on `fix/chrome-keychain-and-fifo-test` is based on `main` at `728856c`.
The macOS renderer uses a mock keychain for its disposable browser profile. The FIFO test
fails at a five-second timeout if the writer blocks. See the
[builder validation evidence](TEST-EVIDENCE.md).
Independent review, owner acceptance and the release workflow remain pending for this candidate.

## November 20 safety repairs (merged baseline)

Version **0.3.1-dev** on `fix/unmerged-safety-repairs` brings the October 21 and October 7
repairs together on top of `main` at `1f44989`. The changes cover restore checkpoints, CLI
errors, boolean secret masking, guarded Git inspection, escaped plan examples and evidence
destination checks. The candidate also includes the standard 1.9.0 alignment and the Windows
line-ending fix. It was merged into `main` at `728856c`. All four jobs passed in its
[CI run](https://github.com/workspace-labs/vibe-to-engineering/actions/runs/44715989493).

## November 20 file-size alarms and verification warning candidate

The 0.3.0-dev instruction update bundles engineering standard 1.9.0 from commit
`d671ceb987084da7bc0103666bc12fc3d29e6758`, a local commit of the standard that is not yet
merged or published. If that commit changes before merge, the bundle must be pinned again.
File-size alarms are read from §7 of the bundled standard; the before → after table marks
proposed files over the review alarm as review candidates, and a `VERIFICATION WARNING`
names check results that are old or do not reach what the plan changes. A warning stays in
every phase report until a fresh run of its check closes it; a gap the owner accepts finishes
as `COMPLETE WITH ACCEPTED VERIFICATION GAPS`, never as ALL GREEN. An open warning is answered
before the final checkpoint is created. A covering check that fails at the baseline has a
defined, visible path when the owner approves continuing. (Review rounds 2 to 4.)

This work was reviewed on branch `feat/file-size-alarms`. An independent review approved it
after five rounds and the owner accepted it on 2026-11-20. It is on `main` in `2462218`.
Validation is recorded in `TEST-EVIDENCE.md`. No agent exercise was run for the new wording, and the
earlier whole-workflow and release gates stay open.

## November 9 engineering-standard alignment candidate

The 0.2.0-dev instruction update bundles engineering standard 1.4.0 from commit
`a27317b9f7885b18dc6b5eedc24b5dd29d27fdb9`. Diagnosis, target design and final review now
share its layout map and project-type trees, applied to structural migration scope.
Plans record that fixed basis and explicitly wait for human approval before baseline checks,
checkpoint creation or code changes. The existing phase, recovery and failure gates remain.

Validation for this candidate is recorded in `TEST-EVIDENCE.md`. It does not close earlier
whole-workflow or release gates. The older results below describe their tested revisions;
the migration runtime, runner registry and platform support are unchanged by this update.

## October 8 review candidate

The PC review reproduced failure of the original complete suite on Windows. The approved
release scope remains macOS-only; Windows/Linux are tested for safe refusal and selected
portable logic, not claimed as supported migration platforms.

Branch `fix/platform-boundary-review` implements A3 scratch retention, A4 early platform
refusal, recovery-store ignore-rule protection, restore-time ignored-file change detection,
Windows fixture isolation, package corrections and reader prerequisite validation.
Separate CI jobs distinguish portable checks from the full native macOS arm64 regression.
See [TEST-EVIDENCE.md](TEST-EVIDENCE.md) for current test results and limitations.

**Current validation:** code/test revision `01f25876205ab1cfaddf6d8a9ebc668cf7583fe6`
passed 346 complete native macOS arm64 tests using CLT Python 3.9.6, mandatory Node and
the pinned reader matrix, and Chromium headless shell. All four matrix tests ran.
The 84-test portable scope passed on this Windows PC and GitHub Windows, Linux and
macOS runners, including an additional CLT-Python preflight. Every run reported zero
failures, errors and skips. [CI evidence](https://github.com/workspace-labs/vibe-to-engineering/actions/runs/37769123814).

This candidate is not an owner-accepted release. Full workflow exams, the remaining
documentation corrections, fresh-user validation and final release gates remain pending.
The accepted A1/A2/confidentiality behavior is preserved; the September results below
describe the earlier snapshot, not this changed candidate.

## September 29 accepted snapshot (historical)

### Status at that update

The latest F3-R1 repair passed Kimi's independent re-review and was accepted by the owner
on 2026-09-29. A1 and A2 were already accepted. The confidentiality/status work has no
remaining defect reported by that review: R2-F2, F4 and F6 were verified in the preceding
review, and F3-R1 closes its remaining ambiguous-option leak.

**The whole skill is still in development.** This GitHub update preserves the reviewed
implementation and its tests; it is not a v0.1.0 release or approval for use on real projects.
A3, A4 and the remaining release exam are pending. NEW-5 is not declared closed.

Development branch: `fix/f03-f06-f08-new1`.

## What is fixed

- **A1 — literal `.env` boundary:** admit the approved literal assignment grammar and refuse
  unsupported or reader-divergent forms before a check runs. Corrective tests cover consecutive
  single-quoted backslashes, Unicode controls and quoted-edge whitespace. The differential
  matrix checks the claimed readers and verifies its artifacts instead of treating failed
  reads as passing empty results.
- **A2 / R2-F5 — runner identity:** require deliberate per-user enrollment, disclose the
  executable identity before approval, and pin the launched bytes to that identity. Corrective
  checks cover approval/copy races, writable ancestors, changed binaries and malformed registries.
  A changed or unsafe identity refuses; re-enrollment remains manual.
- **R2-F2 — complete-output masking:** protect assembled output, labels, prefixes and message
  boundaries so pieces cannot reconstruct a protected value. Recognized-file values join the
  redaction context after file analysis succeeds.
- **R2-F3, including F3-R1 — refusal diagnostics:** collect declared values before argument
  validation. Ambiguous attached options such as `--e=A=value` and `--en=A=value` are still
  refused, but their values are masked. Space-bearing values and later declarations are covered;
  exact options and command boundaries retain their behavior.
- **R2-F4 — recorded paths:** record the validated `--with-path` entries actually supplied to
  the child instead of resolving them again after execution.
- **R2-F6 — result reporting:** preserve the wrapper's 0/1/2/3 status namespace and record
  the child's outcome separately, including recoverable results when values collide with
  diagnostic words or digits. Wrapper success alone does not mean the child check passed.

The detailed masking boundary and result schema remain in
[emission-boundary.md](skills/vibe-to-engineering/references/emission-boundary.md).

## Independent review evidence

Kimi's final F3-R1 re-review is dated 2026-09-29. Its evidence folder retains the
2026-09-28 name. The following are Kimi's recorded independent results:

- Original leak reproduced before; identical inputs masked after, with exit 2, no launched
  check, no evidence write and no registry change.
- 22 CLI cases and 42 collection-level differential cases; exactly 20 changed cases,
  all within the intended ambiguous-attached routes.
- Fail-before: 7 tests, 51 behavioral failures, no errors or skips.
- Pass-after: 7 of 7 tests passed.
- Full serial suite: **307 tests passed, zero failures, errors or skips**, in 327.5 seconds.
  All four required reader-matrix tests ran and passed within that run.
- Bundle hashes: 150 of 150 matched. The 61-file delivered tree matched the tested and
  live trees. The F3-R1 repair changed only its five expected files; runtime changes were
  confined to `emission.py`'s `collect` function.
- The protected F03 file changes retained their required total of +76/-14. Previously
  accepted mechanisms and pre-existing tests were preserved.

Verification scope: macOS arm64, CLT Python 3.9.6, local Node v20.20.2, the pinned reader
matrix and Chromium headless shell. This does not establish Linux or Windows readiness.
Unknown/non-`--env` options and whitespace/equals-only values retain their documented
diagnostic behavior; the reviewer recorded these as unchanged policy, not new defects.

The complete review and raw logs are retained locally in
the evidence folder `vibe-to-engineering-F3-R1-rereview-2026-09-28/` (`REVIEW.md`, scripts, logs and
integrity records). They are not bundled into the installable skill. The source regression
tests are included in this repository. Existing delivery-time references remain historical;
this document records the current acceptance status.

### Verification before this GitHub update

Codex compared all 61 source files with the reviewed manifest before editing: every file
matched. Only README, CHANGELOG and FIX-FIRST status text was updated, and LASTUPDATE was
added; runtime code and tests remained byte-identical to the reviewed version.

Codex then reran the full suite on a disposable copy with an isolated HOME, the documented
CLT Python, Node and browser, and both `V2E_REQUIRE_NODE=1` and `V2E_REQUIRE_MATRIX=1`:
**307 tests passed, zero failures, errors or skips**, in 327.107 seconds. All four required
reader-matrix tests passed. Local logs and the pre-update backup are retained in
the evidence folder `v2e-github-update-2026-09-29-qzr8_d34/`. This verifies the repository snapshot;
the release workflow exam below is still pending.

## September 29 release queue (historical; October status above)

1. **A3 — scratch retention (next implementation step).** Remove automatic deletion of
   the check's run-owned scratch root. Retain it outside the project with mode 0700, record
   its path in evidence and the ledger, and explain that it may contain sensitive output.
   Listing is allowed; deletion remains the human's act. Prove the scratch files survive
   and foreign sentinel files remain untouched. This addresses the retained R2-F1 obligation.
2. **A4 — platform refusal.** Make this release macOS-only at the execution boundary.
   Unsupported platforms must refuse before any write or check. Keep Linux and Windows
   in the roadmap until their own implementation and native release exams are complete.
3. **C — documentation corrections.** Describe checkpoints as covering their defined
   saved-file set. Explain that fingerprints compare covered file states and do not prove
   absence of reads, remote writes or temporary changes. Remove any suggestion to edit a
   real `.env` to gain admission. Require passing recorded evidence for required checks;
   approved manual alternatives must stay visibly outside the masking guarantee.
4. **B — release regression verification.** After the pending changes, run the complete
   suite with Node and the reader matrix required, verify the F03 seal, and preserve the
   accepted A1/A2 and confidentiality/status regressions. Keep explicit refusal tests and
   the recorded reasons for superseded behavior. Passing today's suite does not replace
   the tests still owed for A3/A4 and the workflow exam.
5. **D — full macOS workflow exam on disposable projects.** Exercise successful JavaScript
   and Python migrations; no-migration/zero-write behavior; the refusal battery;
   interruption and ledger-driven resume; failed verification and separately approved
   restore/retry; approved baseline failures; all required-check refusal outcomes; and
   data-safety detection, including a check that writes to a planted database. Hash originals
   before and after, and scan the defined output locations for synthetic secret canaries.
6. **Fresh-user and final release gates.** The real fresh-user exam remains pending until
   account access is arranged with the owner; do not create or modify accounts as a shortcut.
   Complete the remaining evidence, owner gate and separately authorized final independent
   review before claiming whole-skill readiness, closing NEW-5 or releasing/installing it
   for real-project use.

The queue above comes from the owner-approved v0.1.0 release checklist. It records remaining
work; this repository update does not implement those slices. Continue evaluation with
disposable projects and synthetic secrets.
