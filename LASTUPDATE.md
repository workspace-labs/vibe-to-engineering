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

**A3 is owner-ACCEPTED (2026-09-30).** His decision was that the skill must be completely
clean first — fix R1–R3 before A3 closes. R1–R3 were fixed (2026-09-30, `89d8151`); the
independent review reopened R2 for two Low findings (L1, L2), fixed the same day (`aa20333`);
the re-review found L1 and L2 FIXED and one new Low (L3, tests only, pre-existing since
569c8f9), fixed the same day (`79bd7a2`) and — after round 3 narrowed the same flake to the
'-'-ending prefix boundary — fixed again in final form the same day (`ec7ed3b`). With the
skill completely clean, the owner accepted A3 on 2026-09-30.

**A4 — macOS-only platform refusal at the execution boundary — is implemented and
owner-ACCEPTED (2026-09-30).** Every entry point — `evidence.py`,
`checkpoint.py` and `render_pdf.py` — refuses on any platform other than macOS
(`sys.platform != "darwin"`, any other value included) before any write, check, launch,
enrollment, registry access, scratch root or platform-risky import: a plain-language message
naming the platform it saw, never a traceback, and no bypass flag, environment variable or
config. Exit codes follow each script's own refusal convention (evidence.py 2 — with the usual
wrapper status record, `wrapper` 2, `launched` false, `saved` false — checkpoint.py 1,
render_pdf.py 1), through one small stdlib-only shared guard (`scripts/platform_gate.py`),
importable on every platform. The historical Windows/Linux code branches stay in place, now
unreachable. `tests/test_a4_platform.py` proves, for each entry point on linux, win32 and
freebsd14: the refusal exit code and message (platform named, macOS-only, roadmap), no
traceback, nothing written (the disposable project's tree byte-identical, the isolated HOME
without `~/.vibe-to-engineering/`, no evidence file, checkpoint store or PDF), nothing ran (a
sentinel check never ran, no browser launched) — each failing on `ef21f2b` and passing after —
and that darwin still runs normally. Linux and Windows are roadmap entries only: README's
Platforms section says macOS is the only supported platform in this release and carries a
Roadmap section with the frozen items (Linux: pin semantics without SIP, dash-vs-bash-3.2,
locale detection; Windows: PE gate, symlink/G1 settlement, native verification hardware);
SKILL.md states macOS-only near its top and drops the "on Windows use `py -3`" convention;
recovery.md's platform wording moved to macOS-only + roadmap under the owner-approved narrow
unseal (the other three sealed files stay byte-identical). The honest limit: a simulated
`sys.platform` is not a native Linux/Windows run — the tests prove the refusal boundary, not
those platforms' behavior.

**A4 is owner-ACCEPTED (2026-09-30, `b3ad397`).** Claude's independent review of `b3ad397`
ACCEPTED it with no findings: the new tests fail on `ef21f2b` (failures=9) and pass on `b3ad397`
(4/4); the full suite is **339 tests, OK, zero failures, errors or skips** (298.1 s); a harsher
reviewer probe — Unix-only `os` functions removed, Unix-only modules blocked, `ctypes` broken,
`os.name` set to 'nt' — gave 24/24 clean refusals: no traceback, nothing written, nothing ran.
The F03 seal is intact and the recovery.md unseal is exactly 3 lines. The review handed four
wording notes to C (item 2 below). **Next is C — the documentation corrections — then B (the
regression re-verification) and D (the macOS workflow exam).**

**C — documentation correctness — is implemented (2026-09-30, base `99c8ebf`) and delivered for
independent review.** The skill's words now promise exactly what the tool does. Checkpoints are
described as their defined saved-file set — every file git would not ignore; ignored files
watched, not saved; nested repositories not saved — replacing the "whole project" claims in
README.md and plan-template.html, with SKILL.md's checkpoint table saying the same. Wherever a
fingerprint or checkpoint comparison stands as data-safety evidence, the text states it compares
covered local file states and **does not prove the absence of reads, remote writes or temporary
changes** (a file changed and changed back between two checkpoints looks unchanged): SKILL.md's
checkpoint-tool section and phase gate, README, the plan template. The `.env` boundary states the
file is never edited, rewritten or converted so the tool accepts the project — the acceptable
remedies are keeping it outside the project for the migration or `--env` throwaway data; the
audit found no editing suggestion anywhere to remove. Required checks: passing recorded evidence
(a matching wrapper 0 and child exit 0) is the written gate for ALL GREEN; a refused or
unrunnable required check has exactly three outcomes — (a) a plan revision, (b) an owner-approved
manual alternative (approved plan revision, ledger record with the human's words, visibly marked
`MANUAL — OUTSIDE THE MASKING GUARANTEE`), (c) a blocking finding, never silently skipped and
never ALL GREEN — and a migration completed with (b) ends in the new
`VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED MANUAL CHECKS` outcome with one `Manual:` line per
such check stating it ran outside the secret-masking guarantee; a run with both kinds shows both
blocks. The outcome is added everywhere outcomes are listed: the SKILL.md and README flows, the
resume rule, the status-lines list and the section-9 blocks (the plan template and
migration-plan.md list no outcomes; migration-plan.md's verification section gains the
three-outcomes rule). Skill-audit leftovers folded in: the `sh scripts/test.sh` example is now
`sh <project-script> …` in SKILL.md and supported-checks.md, and the two personal `~/Desktop`
evidence paths in env-boundary.md and stage1-acceptance.md are neutral descriptions (the evidence
is recorded outside the repository). The four A4 review notes: checkpoint.py's docstring is
macOS-only with Linux/Windows on the roadmap; the "(Windows: py -3 …)" usage lines are removed
from evidence.py's and render_pdf.py's docstrings; README's macOS row reads "supported; all tests
pass; release exam pending"; and the Linux/Windows notes in stage1-acceptance.md read as
roadmap/design history (supported-checks.md's platform-scope note already did). One audit find
beyond the list: evidence.py's docstring still said the scratch folder is "removed when the run
ends" — A3 retains it — now corrected to retained, never deleted. `tests/test_c_wording.py`
(7 tests) guards every correction — each fails on `99c8ebf` (failures=7) and passes after. No
behavior changes; recovery.md, gitrun.py, nested.py and test_nested.py stay byte-identical to
`b3ad397`. Per the seal rule, the audit's flagged lines inside the sealed recovery.md come back
as an owner decision instead of edits: line 51 "so the same files run on every platform" (stale
since A4; its checkpoint.py twin is fixed) and line 81 "macOS — validated in 0.1.0" (reads
release-validated while exam D is pending; its README twin is fixed), plus two borderline
readings recorded for judgment (G10's "report one whose contents changed" without the
changed-and-changed-back limit, and the Windows roadmap note's "the saved pre-restore checkpoint
keeps everything").

## C review round (2026-09-30) — M1 and D1, owner-ACCEPTED

Claude's review of `7dd2193` verified items 1–7 (7/7 new tests fail on `99c8ebf` and pass
after; the full suite 346 OK; the seals hold; no over-claims left outside recovery.md) and
REOPENED narrowly for one finding: a manual check the human reports FAILED had no defined
outcome and could end in `COMPLETE WITH APPROVED MANUAL CHECKS` (M1). Fixed with the review's
prescription: the `Manual:` line carries the reported result —
`Manual: <check> — passed (reported by the human, <date>) — ran outside the secret-masking
guarantee (its output was not masked by the tool)`; the label requires every manual check
reported PASSED; a manual check reported FAILED is a failing check like any other — in a phase
the phase fails (section 8), in the final review it blocks completion unless it was already
failing at the baseline and approved, in which case it appears as a `Still failing` line under
`COMPLETE WITH APPROVED BASELINE FAILURES`; the ledger records the reported result with the
approval. Mirrored in migration-plan.md. The owner then decided the recovery.md question the
audit brought back (D1, narrow unseal 2026-09-30, exactly four spots, nothing else): line 51
is macOS-only with other platforms as roadmap entries; line 81 reads "supported in 0.1.0 (all
tests pass; release exam pending)"; line 83's "keeps everything" is "keeps its saved-file
set"; G10 gains the §3.7 limit sentence. gitrun.py, nested.py and test_nested.py stay
byte-identical to `b3ad397`; recovery.md differs from it by exactly those four spots.
`tests/test_c_wording.py`'s extended assertions guard both fixes — the four touched methods
fail on `7dd2193` (failures=4) and pass after; the suite stays 346 tests.

**C is owner-ACCEPTED (2026-09-30, `7dd2193` + `28f5e85`).** Claude's re-review of `28f5e85`
ACCEPTED the round: M1 fixed (the `Manual:` line carries the reported result, the label
requires every manual check reported PASSED, a failed manual check is a failing check like
any other), D1 applied exactly (word-level diff shows only the four approved recovery.md
phrases), the extended tests fail on `7dd2193` (4) and pass on `28f5e85` (7/7), the full
suite is **346 tests, OK, zero failures, errors or skips** (306.5 s on the review side; the
delivery-side run was 308.2 s), and the seals hold. **Next is B — the release regression
verification — then D (the macOS workflow exam).** The skill is still in development — this
is not a release.

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
**335 tests, zero failures, errors or skips**. The independent review of this final form
closed L3, and the owner accepted A3 on 2026-09-30.

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
for use on real projects. The documentation sweep (C), the regression re-verification (B) and
the remaining release exams (D, then the fresh-user gate) are pending. NEW-5 is not declared
closed.

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
- **A4 — macOS-only platform refusal (implemented and owner-accepted 2026-09-30):** every
  entry point (`evidence.py`, `checkpoint.py`, `render_pdf.py`) refuses on any platform other
  than macOS, before any write, check, launch or platform-risky import — a clean message naming
  the platform it saw, never a traceback, no bypass. Each script keeps its own refusal exit
  code (2/1/1), evidence.py's refusal carries the usual wrapper status record, and one small
  stdlib-only guard (`scripts/platform_gate.py`) holds the message. Linux and Windows are
  roadmap entries only (README Roadmap; SKILL.md; recovery.md's platform wording under the
  narrow unseal). Regressions in `tests/test_a4_platform.py` fail on `ef21f2b` and pass after.

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

1. **A4 — platform refusal (implemented and owner-accepted 2026-09-30, `b3ad397`).** This
   release is macOS-only at the execution boundary: unsupported platforms refuse before any
   write or check, and Linux and Windows live in the roadmap until their own implementation and
   native release exams are complete. Claude's independent review accepted it with no findings.
2. **C — documentation corrections (owner-ACCEPTED 2026-09-30, `7dd2193` + `28f5e85`).**
   Checkpoints are described as covering their defined saved-file set;
   fingerprints and checkpoint comparisons state they compare covered local file states and do
   not prove absence of reads, remote writes or temporary changes; the `.env` boundary states
   the file is never edited, rewritten or converted to gain admission and names the acceptable
   remedies (outside the project for the migration, or `--env` throwaway data) — the audit found
   no editing suggestion to remove. Required checks pass only with passing recorded evidence; a
   refused or unrunnable one has exactly three outcomes (plan revision / owner-approved manual
   alternative, ledger-recorded and marked `MANUAL — OUTSIDE THE MASKING GUARANTEE` / blocking
   finding), and an approved manual alternative ends the migration in the new
   `VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED MANUAL CHECKS` outcome — never ALL GREEN. The
   2026-09-29 skill-audit findings (`sh <project-script> …`; neutral evidence paths) and the
   four A4 wording notes are folded in. Guarded by `tests/test_c_wording.py` (7 tests, each
   failing on `99c8ebf` and passing after); no behavior changes. Claude's review verified all
   of it and reopened narrowly for M1 (a FAILED manual check had no defined outcome) — fixed
   with the review's prescription; the owner decided the recovery.md lines the audit brought
   back (D1: all four spots changed under a narrow unseal; gitrun.py, nested.py and
   test_nested.py stay byte-identical to `b3ad397`). Claude's re-review of `28f5e85` ACCEPTED
   the round, and the owner accepted C on 2026-09-30 (`7dd2193` + `28f5e85`).
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
