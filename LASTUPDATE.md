# Latest update — 2026-09-29

## Current status

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
`~/Desktop/vibe-to-engineering-F3-R1-rereview-2026-09-28/` (`REVIEW.md`, scripts, logs and
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
`~/Desktop/v2e-github-update-2026-09-29-qzr8_d34/`. This verifies the repository snapshot;
the release workflow exam below is still pending.

## What to fix and verify next

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
