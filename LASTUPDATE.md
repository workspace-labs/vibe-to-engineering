# Latest update — 2026-09-30

## Current status

The latest F3-R1 repair passed Kimi's independent re-review and was accepted by the owner
on 2026-09-29. A1 and A2 were already accepted. The confidentiality/status work has no
remaining defect reported by that review: R2-F2, F4 and F6 were verified in the preceding
review, and F3-R1 closes its remaining ambiguous-option leak.

**A3 — scratch retention — is now implemented** (2026-09-29, owner decisions: retain under
`~/.vibe-to-engineering/runs/`, enrollment's root retained too). The tool never deletes:
every run-owned scratch root is confirmed by the R1 identity proof and left standing,
mode 0700, its path recorded in the evidence header and on stderr, and — per the updated
protocol — in the project ledger; deletion stays the human's act. R2-F1 is closed by
construction: a tool that never deletes can never delete data the run did not make.
The first independent A3 review (of 569c8f9) **reopened A3** for three blocking defects
and two minor ones — a check tampering with the scratch base, a state the original tests
never created: a base failure after launch crashed unmasked with exit 1 (F1), the base
chain was followed through a link (F2), the recorded "mode 0700" was never enforced (F3),
plus a umask gap (F4) and a stale wording (F5). The corrective is implemented: retention
creates and changes nothing at the base (lstat-only `verify_base`), the chain is validated
level by level at construction (never a link, a non-directory or another user's; never
inside the project), the 0700 is re-asserted on the verified root, and each finding has a
regression test that fails on 569c8f9 and passes now (`tests/test_a3_corrective.py`).
The re-review of that corrective (9204241) closed F1–F5 on their reproductions but **reopened A3
again** for five defects inside the corrective itself: a swap window between the identity check
and the chmod (N1), a check removing its own $TMPDIR getting exit 3 where 569c8f9 gave 0 (N2),
a letter-case route past the inside-the-project string comparison (N3), an early refusal still
creating the base folders (N4), and the evidence header claiming retention it had not confirmed
(N5). The second corrective is implemented: identity and chmod now happen through one descriptor
(open O_DIRECTORY|O_NOFOLLOW, fstat, fchmod; home/ and tmp/ through it with dir_fd), a missing
home/ or tmp/ is skipped, containment is judged by device and inode, check_base runs inside
construct after every validation, and the header only points at the stderr retention report.
Each finding has a regression that fails on 9204241 and passes now.
The third review (of cc5b862) closed N2–N5 and all F findings, found N1 only half-closed and
four more defects, and the third corrective is implemented: the base levels and the root itself
are created and validated through one descriptor chain (dir_fd throughout — a swapped base level
cannot redirect the root into a stranger, P1), home/ and tmp/ are registered by identity at
creation and only a matching descriptor is fchmodded (a foreign folder moved in is a stranger,
P2), a root the check made unreadable is identity-confirmed and restored instead of misreported
as a stranger (P3), and no fstat failure can escape raw (P4); every injection hook in the tests
asserts it actually fired (P5). Each finding has a regression that fails on cc5b862 and passes now.
The fourth review (of 87709ab) closed P1–P5 and everything before them, and found one defect class
left in the P3 path: the by-path restore could still be raced by a real foreign directory. The
fourth corrective ends the by-path era — the root's descriptor is HELD OPEN from creation to
retention, identity and mode are judged on it alone, "still at its path" is an lstat compared
against it, the root string must name the folder just made or the run is refused, and the held
descriptor is proven closed exactly once on every path. Each finding has a regression that fails
on 87709ab and passes now.

**A3's history:** `569c8f9` (implementation), then `9204241`, `cc5b862`, `87709ab`, and
`46114bc`, which was **reviewer-accepted on 2026-09-29**: the independent re-review found A3
ACCEPTED on the review side — Q1 and Q2 close, every earlier finding (F1–F5, N1–N5, P1–P5)
stays closed, the must-be-unchanged list holds, and the suite is 329 tests, OK, no skips.

**The owner has not pressed Accept.** His decision: the skill must be completely clean first —
fix R1–R3 before A3 closes. R1–R3 were fixed (2026-09-30, `89d8151`); the independent review
reopened R2 for two Low findings (L1, L2), fixed the same day (`aa20333`); the re-review found
L1 and L2 FIXED and one new Low (L3, tests only, pre-existing since 569c8f9), fixed the same
day (`79bd7a2`) and — after round 3 narrowed the same flake to the '-'-ending prefix boundary —
fixed again in final form the same day and delivered for review. Owner acceptance of A3
remains pending.

## L3 (2026-09-30, final form) — flaky secret-canary assertions, tests only

The reviewer's full suite flaked once: `assertNotIn("9137", …)` tripped on the retained root's
random hex name in the stderr retention line — no secret had leaked. Round 2's shared tokens
(`"-9137"`, `"-5561"`) narrowed the flake but did not close it: the prefixes end in '-', so a
suffix STARTING with the digits still spells them (the reviewer reproduced `v2e-run-9137…`;
the recommendation had been the reviewer's own, and the new comments overstated it). Final
form: each subtest asserts its own FULL canary values — `FEED-9137`, `Hor5e-9137x`,
`other-9137`, `c13k-9137-token`, `x{a,b}` (the brace case's guard was vacuous before) in
test_env_literal.py, `/x-5561` and `v-5561` in test_evidence_stage1.py — every canary holds
characters no `v2e-run-` + lowercase-hex name or mktemp suffix ([a-z0-9_]) can spell, so the
guards cannot flake at all; the comments say exactly that and no more. The other four audited
assertions stay left as they are (the re-review confirmed the audit). Proof on disposable
copies: root names forced to START with 9137 fail `79bd7a2` (6 failures) and pass now; names
forced to END with 9137 pass; a mktemp name holding `-5561` fails `79bd7a2` and passes now;
planted real leaks (raw .env in the refusal; raw --env with masking disabled) still fail every
canary assertion. No product code changed; the F03 seal holds. The full suite on a disposable
copy of the final committed tree, isolated HOME, CLT Python 3.9.6, Node v20.20.2, Chromium
headless shell, the verified reader matrix, `V2E_REQUIRE_NODE=1` and `V2E_REQUIRE_MATRIX=1`:
**335 tests, zero failures, errors or skips**. Next: the independent review of L3.

## L1–L2 (2026-09-30) — the review's two Low findings, fixed (re-review: FIXED)

- L1: the open-failure and fstat-failure refusals printed the scratch base PATH before the
  identity check had passed — after a base-level swap (the Q2 attack shape) that string
  resolves into a stranger. Both branches now use the stat/Q2 wording: before the identity
  check only the root's NAME is named, no path at all. The new regression swaps the chain and
  then fails the open: **fails on 89d8151** (the stranger-bound base path was printed) and
  passes after.
- L2: no test reached the true Q2 "resolves away" mismatch branch — the swap test lands on
  the stat-confirmation branch (os.stat finds nothing after the swap). It is renamed
  `test_the_stat_confirmation_refusal_…`; a new test plants a same-named folder in the
  stranger so os.stat succeeds on a different inode, reaching the real mismatch refusal and
  asserting "resolves away", the root named, the stranger's path absent and the stranger
  untouched. The branch was already correct — the gap was coverage, not behavior (the test
  passes on 89d8151 and fails on 46114bc, where the message named nothing).

The full suite ran on a disposable copy of the final committed tree with an isolated HOME,
the documented CLT Python 3.9.6, Node v20.20.2, Chromium headless shell and the verified
reader matrix, with `V2E_REQUIRE_NODE=1` and `V2E_REQUIRE_MATRIX=1`: **335 tests passed (333
plus the two new ones), zero failures, errors or skips**. The F03-sealed files are
byte-identical. The re-review found both FIXED (and raised L3, above).

## R1–R3 (2026-09-30) — fixed, reviewer-accepted for R1 and R3; R2 completed under L1–L2

- R1: `retain` now pops the registry BEFORE `verify_base` and closes the held descriptor on
  that failure path too — a failed base check no longer leaves it open and registered until
  the process exits. The "closed exactly once on every path" companion proof gained the
  "a failed base check" case.
- R2: every `Fail` raised after the root's `mkdir` in `scratch_root` now names what the human
  needs to find the left-behind root — the confirmed root path once the identity check has
  passed, and before it only the root's NAME (the review's L1: not even the base's path,
  which the same swap can point into a stranger; this section first said "name and base").
  Nothing is deleted, still.
- R3: the Q1 test catches `retain`'s `Fail`, so on 87709ab it FAILS on the mode assertion
  that proves the defect instead of ERRORING on it; `test_final_review_r1.py`'s registry pop
  now closes the held descriptor it removes.

Each item has a regression that fails on 46114bc and passes after: the new tests in
`tests/test_a3_r1_r2.py` fail there (each on the defect-proving assertion), the extended
companion proof fails on its new "a failed base check" case, and the repaired Q1 test fails —
never errors — on 87709ab. The full suite ran on a disposable copy with an isolated HOME, the
documented CLT Python 3.9.6, Node v20.20.2, Chromium headless shell and a freshly rebuilt
reader matrix (the previous folder was gone; every artifact fetched from its recorded URL,
each sha256 verified) with `V2E_REQUIRE_NODE=1` and `V2E_REQUIRE_MATRIX=1`: **333 tests
passed (329 plus the four new ones), zero failures, errors or skips**, in 343.2 seconds, and
the reviewer reran it on 89d8151 itself: 333, OK, 287.4 seconds. The F03-sealed files are
byte-identical.

**The whole skill is still in development.** This state is not a v0.1.0 release or approval
for use on real projects. A4, the documentation sweep, the regression re-verification and
the remaining release exam are pending. NEW-5 is not declared closed.

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
- **A3 — scratch retention (implemented 2026-09-29):** `childenv.cleanup` is gone. Nothing the
  tool runs deletes anything: `childenv.retain` confirms each run-owned scratch root by the R1
  identity proof (registered, run-prefixed, directly inside the one base, matched by device and
  inode) and leaves it standing — a moved, swapped or linked-over root is still exit 3, and
  whatever stands at its path is left exactly as found. The scratch base moved from `/tmp`,
  which the OS reaps on its own schedule, to `~/.vibe-to-engineering/runs/` — so deletion
  really is the human's act alone. The chain is made once at construction, each level a real
  directory owned by this user (never a link, never inside the project), every level mode
  0700 whatever the umask; retention only inspects it (lstat) and re-asserts the recorded
  0700 on the verified root — identity matched with fstat on the root's own open descriptor
  (O_DIRECTORY|O_NOFOLLOW), the mode set with fchmod on it, home/ and tmp/ opened through it
  with dir_fd, a missing one skipped — so no swap between check and chmod can touch a stranger.
  The chain itself is built the same way: levels opened through their parent's descriptor, the
  base descriptor held open, the root created with mkdir(dir_fd=) and registered from fstat —
  home/ and tmp/ registered by identity too, so a foreign folder moved in as one is a stranger
  skipped untouched, and a root the check made unreadable is identity-confirmed and restored,
  never misreported.
  The retained path
  is in the evidence header (`scratch … its retention is reported on stderr; may hold
  sensitive output`) and the stderr summary; SKILL.md records it in the
  project ledger with each check's numbers. Enrollment's probe root is retained too. Exit statuses are unchanged; a refusal
  before construction still leaves nothing, a refusal past it retains its check-free root.
  Corrective tests cover retention survival with contents, a foreign sentinel moved inside the
  root untouched, refusal of non-run-owned paths and links, retained roots on refusals past
  construction, and the R1 swap/link/moved-root battery re-pointed at retention.

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

1. **A4 — platform refusal (next implementation step).** Make this release macOS-only at the
   execution boundary. Unsupported platforms must refuse before any write or check. Keep Linux
   and Windows in the roadmap until their own implementation and native release exams are complete.
2. **C — documentation corrections.** Describe checkpoints as covering their defined
   saved-file set. Explain that fingerprints compare covered file states and do not prove
   absence of reads, remote writes or temporary changes. Remove any suggestion to edit a
   real `.env` to gain admission. Require passing recorded evidence for required checks;
   approved manual alternatives must stay visibly outside the masking guarantee. Also fold in
   the 2026-09-29 skill-audit findings: the `sh scripts/test.sh` example wording in SKILL.md
   (a static scanner reads it as a bundled-file reference) and the two `~/Desktop/...` evidence
   paths in `references/env-boundary.md` and `references/stage1-acceptance.md`.
3. **B — release regression verification.** After the pending changes, run the complete
   suite with Node and the reader matrix required, verify the F03 seal, and preserve the
   accepted A1/A2 and confidentiality/status regressions. Keep explicit refusal tests and
   the recorded reasons for superseded behavior. Passing today's suite does not replace the
   tests still owed for A4 and the workflow exam. A3's own verification ran 2026-09-29: the
   complete suite — **309 tests passed (307 plus A3's two new proofs), zero failures, errors
   or skips**, in 298.4 seconds — on a disposable copy of the repository with an isolated
   HOME, the documented CLT Python, Node v20.20.2, the pinned reader matrix and Chromium
   headless shell, with `V2E_REQUIRE_NODE=1` and `V2E_REQUIRE_MATRIX=1`.
4. **D — full macOS workflow exam on disposable projects.** Exercise successful JavaScript
   and Python migrations; no-migration/zero-write behavior; the refusal battery;
   interruption and ledger-driven resume; failed verification and separately approved
   restore/retry; approved baseline failures; all required-check refusal outcomes; and
   data-safety detection, including a check that writes to a planted database. Hash originals
   before and after, and scan the defined output locations for synthetic secret canaries —
   now including the retained scratch roots under `~/.vibe-to-engineering/runs/`.
5. **Fresh-user and final release gates.** The real fresh-user exam remains pending until
   account access is arranged with the owner; do not create or modify accounts as a shortcut.
   Complete the remaining evidence, owner gate and separately authorized final independent
   review before claiming whole-skill readiness, closing NEW-5 or releasing/installing it
   for real-project use.

The queue above comes from the owner-approved v0.1.0 release checklist. It records remaining
work; this repository update does not implement those slices. Continue evaluation with
disposable projects and synthetic secrets.
