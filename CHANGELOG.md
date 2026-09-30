# Changelog

## [Unreleased]

- 2026-09-30 — **C owner-ACCEPTED** (`7dd2193` + `28f5e85`). Claude's re-review of `28f5e85`
  ACCEPTED the review round: M1 fixed (the `Manual:` line carries the reported result, the
  label requires every manual check reported PASSED, a FAILED manual check is a failing check
  like any other), D1 applied exactly (word-level diff shows only the four approved
  recovery.md phrases), the extended tests fail on `7dd2193` (failures=4) and pass on
  `28f5e85` (7/7), the full suite is **346 tests, OK, zero failures, errors or skips** (306.5
  s), and the seals hold (gitrun.py, nested.py and test_nested.py byte-identical to `b3ad397`;
  recovery.md changed only at the four approved spots). Next: B (release regression
  verification), then D (the macOS workflow exam). The skill is still in development — this
  is not a release.

- 2026-09-30 — C review round: M1 (a FAILED manual check had no defined outcome) and D1
  (recovery.md narrow unseal, owner-approved 2026-09-30), delivered for independent review;
  base `7dd2193`. M1: the `Manual:` line now carries the reported result —
  `Manual: <check> — passed (reported by the human, <date>) — ran outside the secret-masking
  guarantee (its output was not masked by the tool)`; `COMPLETE WITH APPROVED MANUAL CHECKS`
  requires every manual check reported PASSED; a manual check reported FAILED is a failing
  check like any other — in a phase the phase fails (section 8), in the final review it blocks
  completion unless it was already failing at the baseline and approved, in which case it
  appears as a `Still failing` line under `COMPLETE WITH APPROVED BASELINE FAILURES`; the
  ledger records the reported result with the approval; mirrored in migration-plan.md. D1
  (recovery.md, exactly four spots, nothing else): line 51 macOS-only this release with other
  platforms as roadmap entries; line 81 "supported in 0.1.0 (all tests pass; release exam
  pending)"; line 83 "keeps its saved-file set"; G10 gains the §3.7 limit sentence (the
  comparison covers local file states and does not prove the absence of reads, remote writes
  or temporary changes — a file changed and changed back looks unchanged). gitrun.py,
  nested.py and test_nested.py stay byte-identical to `b3ad397`. `tests/test_c_wording.py`'s
  extended assertions guard both — the four touched methods fail on `7dd2193` (failures=4)
  and pass after; the suite stays 346 tests. The skill is still in development — this is not
  a release.

- 2026-09-30 — C: documentation correctness (the frozen §3.7 wording rules and the owner
  decision of 2026-09-30 on required checks), delivered for independent review; base `99c8ebf`.
  Checkpoints are described as covering their defined saved-file set — every file git would not
  ignore; ignored files watched, not saved; nested repositories not saved — replacing the
  "whole project" claims in README.md and plan-template.html, with SKILL.md's checkpoint table
  saying the same. Wherever a fingerprint or checkpoint comparison stands as data-safety
  evidence, the text now states it compares covered local file states and does not prove the
  absence of reads, remote writes or temporary changes (a file changed and changed back between
  two checkpoints looks unchanged). The `.env` boundary states the file is never edited,
  rewritten or converted so the tool accepts the project — the acceptable remedies are keeping
  it outside the project for the migration or `--env` throwaway data; the audit found no editing
  suggestion to remove. Required checks: passing recorded evidence (a matching wrapper 0 and
  child exit 0) is the written gate for ALL GREEN; a refused or unrunnable required check has
  exactly three outcomes — plan revision, owner-approved manual alternative (approved plan
  revision, ledger record with the human's words, visibly marked
  `MANUAL — OUTSIDE THE MASKING GUARANTEE`), or blocking finding — never silently skipped and
  never ALL GREEN; a migration completed with a manual alternative ends in the new
  `VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED MANUAL CHECKS` outcome with one `Manual:` line
  per such check (ran outside the secret-masking guarantee), added everywhere outcomes are
  listed (both flows, the resume rule, the status-lines list, the section-9 blocks;
  migration-plan.md's verification section gains the three-outcomes rule). Skill-audit
  leftovers: the `sh scripts/test.sh` example is now `sh <project-script> …` (SKILL.md and
  supported-checks.md); the two personal `~/Desktop` evidence paths in env-boundary.md and
  stage1-acceptance.md are neutral descriptions. The four A4 review notes: checkpoint.py's
  docstring is macOS-only (Linux/Windows roadmap); the "(Windows: py -3 …)" usage lines are
  removed from evidence.py's and render_pdf.py's docstrings; README's macOS row reads
  "supported; all tests pass; release exam pending"; stage1-acceptance.md's Linux/Windows notes
  read as roadmap/design history. Also corrected on audit: evidence.py's docstring said the
  scratch folder is "removed when the run ends" — A3 retains it; now retained, never deleted.
  New `tests/test_c_wording.py` (7 wording tests) guards all of it — each fails on `99c8ebf`
  (failures=7) and passes after. No behavior changes; recovery.md, gitrun.py, nested.py and
  test_nested.py stay byte-identical to `b3ad397`; the audit-flagged sealed lines inside
  recovery.md come back as an owner decision per the seal rule. The skill is still in
  development — this is not a release.

- 2026-09-30 — **A4 owner-ACCEPTED** (`b3ad397`). Claude's independent review of `b3ad397`
  ACCEPTED the macOS-only platform refusal with no findings: the new tests fail on `ef21f2b`
  (failures=9) and pass on `b3ad397` (4/4); the full suite is 339 tests, OK, zero failures,
  errors or skips (298.1 s); a harsher reviewer probe (Unix-only `os` functions removed,
  Unix-only modules blocked, `ctypes` broken, `os.name` 'nt') gave 24/24 clean refusals — no
  traceback, nothing written, nothing ran. The F03 seal is intact and the recovery.md narrow
  unseal is exactly 3 lines. The review handed four wording notes to C (the checkpoint.py
  docstring's platform claim, the "(Windows: py -3 …)" docstring usage lines, README's
  "Supported and validated" while exam D is pending, and the Linux/Windows notes in
  stage1-acceptance.md and supported-checks.md). Next: C (documentation corrections), then B
  (regression re-verification), then D (the macOS workflow exam). The skill is still in
  development — this is not a release.

- 2026-09-30 — A4: macOS-only platform refusal at the execution boundary (the frozen staged
  release decision: macOS → Linux → Windows; no platform release-validated until its own
  release exam passes), delivered for independent review. Every entry point — `evidence.py`,
  `checkpoint.py`, `render_pdf.py` — refuses on any platform other than macOS
  (`sys.platform != "darwin"`, any other value included), before any write, check, launch,
  enrollment, registry access, scratch root or platform-risky import: a plain-language message
  naming the platform it saw, never a traceback, and no bypass flag, environment variable or
  config. Exit codes follow each script's own refusal convention (evidence.py 2, with the usual
  wrapper status record — `wrapper` 2, `launched` false, `saved` false; checkpoint.py 1;
  render_pdf.py 1), through one new small stdlib-only shared guard,
  `scripts/platform_gate.py`, importable on every platform. The historical Windows/Linux code
  branches stay in place, now unreachable; macOS behavior is unchanged. New
  `tests/test_a4_platform.py` proves, for each entry point on linux, win32 and freebsd14: the
  refusal exit code and message (platform named, macOS-only, roadmap), no traceback, nothing
  written (disposable project byte-identical; isolated HOME without `~/.vibe-to-engineering/`;
  no evidence file, checkpoint store or PDF) and nothing ran (sentinel check never ran, no
  browser launched) — each failing on `ef21f2b` and passing after — plus unchanged darwin
  behavior. Documentation: README's Platforms section now names macOS the only supported
  platform with Linux and Windows as roadmap entries, and a new Roadmap section lists the
  frozen items (Linux: pin semantics without SIP, dash-vs-bash-3.2, locale detection; Windows:
  PE gate, symlink/G1 settlement, native verification hardware); SKILL.md states macOS-only
  near its top and drops the "on Windows use `py -3`" convention; recovery.md's platform
  wording moved to macOS-only + roadmap under the owner-approved narrow unseal, its Windows
  technical notes kept as roadmap facts — the other three sealed files stay byte-identical.
  Honest limit: a simulated `sys.platform` is not a native Linux/Windows run — the tests prove
  the refusal boundary, not those platforms' behavior.

- 2026-09-30 — A3 L3, final form (the re-review of 79bd7a2 narrowed the same flake: the round-2
  shared tokens `"-9137"`/`"-5561"` can still be spelled at the prefix boundary — `v2e-run-`
  ends in '-', so a root name whose hex STARTS with 9137 prints `v2e-run-9137…`; the token had
  been the reviewer's own recommendation, and the new comments overstated it), delivered for
  independent review. Both assertions now assert each subtest's own FULL canary values:
  `FEED-9137`, `Hor5e-9137x`, `other-9137`, `c13k-9137-token` and `x{a,b}` in
  `tests/test_env_literal.py` (the brace case's guard was vacuous before — it now has a real
  one), `/x-5561` and `v-5561` in `tests/test_evidence_stage1.py`. Every canary holds
  characters no `v2e-run-` + lowercase-hex name or mktemp suffix ([a-z0-9_]) can spell, so the
  guards cannot flake at all; the comments state exactly that and no more. Proof on disposable
  copies: root names forced to START with 9137 fail 79bd7a2 (6 failures, `v2e-run-9137e03…`)
  and pass now; names forced to END with 9137 pass; a mktemp name holding `-5561` fails
  79bd7a2 and passes now; planted real leaks (raw .env in the refusal; the raw --env setting
  with masking disabled) still fail every canary assertion. Tests only — no product code; the
  F03 seal holds.

- 2026-09-30 — A3 L3 (the re-review of aa20333 found L1 and L2 FIXED and one new Low, tests
  only, pre-existing since A3's 569c8f9), delivered for independent review. The reviewer's
  full suite flaked once: `assertNotIn("9137", …)` tripped on the retained root's random hex
  name (`v2e-run-ba82f9ad9c9137509e`) printed on stderr — the secret had not leaked. The two
  canary assertions whose checked text can carry the root path now assert tokens with a
  non-hex character: `"-9137"` in `tests/test_env_literal.py` (every canary in the loop
  carries it) and `"-5561"` in `tests/test_evidence_stage1.py` (the one canary that lacked
  the dash, `NOT A NAME=5561`, became `NOT A NAME=v-5561`; that report's only collision
  channel is the mktemp suffix in a `--with-path` path, which never spells `-`). (The shared
  tokens were superseded the same day by the entry above: they can still be spelled at the
  '-'-ending prefix boundary.) Audited and
  LEFT, with evidence: `tests/test_final_review_r2.py:575` — its canary is a DECLARED value,
  masked wherever it appears, so a forced root name ending in `1234` arrives as
  `v2e-run-…<masked>` and the old assertion cannot flake; `tests/test_evidence_readings.py:167`
  and `tests/test_stage1_acceptance.py:178` — the checked text is the tool's stdout, empty on
  a refusal (the retention report is stderr-only), so the root path never reaches it;
  `tests/test_r2_confidentiality.py:199` — pure computed label strings, no run output.
  Proof, all on disposable copies: with `os.urandom` rigged so every root name ends in the
  canary digits, the old assertions fail and the new ones pass; with the real secret planted
  in the output (raw .env content in the refusal; the raw --env setting with masking
  disabled), the new assertions still fail. No product code changed; the F03 seal holds.

- 2026-09-30 — A3 L1–L2 (the independent review of 89d8151 REOPENED R2 for two Low findings;
  R1 and R3 stayed closed), delivered for independent re-review. (L1) The open-failure and
  fstat-failure refusals printed the scratch base PATH before the identity check had passed —
  after the very base-level swap Q2 guards against, that string resolves into a stranger: both
  branches now use the stat/Q2 wording ("directly inside the scratch base directory this run
  created it in" — no path; before the identity check only the root's NAME is named). The new
  regression swaps the chain and then fails the open: it fails on 89d8151 (the stranger-bound
  base path was printed) and passes after. (L2) No test reached the true Q2 "resolves away"
  mismatch branch — the existing swap test lands on the stat-confirmation branch (os.stat
  finds nothing after the swap): it is renamed `test_the_stat_confirmation_refusal_…`, and a
  new test plants a same-named folder in the stranger so os.stat succeeds on a different
  inode, reaching the real mismatch refusal — asserting "resolves away", the root named, the
  stranger's path absent and the stranger untouched. The branch was already correct on
  89d8151 (the test passes there and fails on 46114bc, where the message named nothing); the
  gap was coverage, not behavior. The no-deletion rule, the held-descriptor design, R1, R3,
  every F/N/P/Q regression and the F03-sealed files are unchanged.

- 2026-09-30 — A3 R1–R3 (the owner's three Low leftovers after the reviewer acceptance of
  46114bc), delivered for independent review. (R1) `retain` called `verify_base()` BEFORE
  `_ROOTS.pop`, so a failed base check left the root's held descriptor open and registered
  until the process exited: the pop now comes first, and the descriptor is closed exactly
  once on that path too — the "closed exactly once on every path" companion proof gained the
  "a failed base check" case. (R2) Any `Fail` raised after the root's `mkdir` in
  `scratch_root` left a real root in the base that was neither registered nor reported — and
  the tool never deletes. The refusal now names what the human needs to find it: the
  confirmed root path once the identity check has passed, and before it only the root's
  NAME — not even the base's path, which the same swap can point into a stranger (corrected
  by L1 above; this entry first claimed "name and base"). (R3, tests) The Q1 test caught
  nothing, so on 87709ab it ERRORED on `retain`'s `Fail` instead of reaching the mode
  assertion that proves the defect: it now catches the `Fail` and FAILs on that assertion
  there. `test_final_review_r1.py`'s registry pop now closes the held descriptor it removes
  instead of leaking it. The new regressions in `tests/test_a3_r1_r2.py` fail on 46114bc and
  pass after; the swap test among them covers the stat-confirmation branch — the true Q2
  "resolves away" mismatch branch gains its own test under L2 above (this entry first implied
  it was already covered). The no-deletion rule, the held-descriptor design, the one
  descriptor chain, the 0/1/2/3 statuses, every F/N/P/Q regression and the F03-sealed files
  are unchanged.

- 2026-09-29 — A3 fourth corrective (fourth review Q1–Q2), delivered for independent re-review:
  the fourth review of 87709ab closed P1–P5 and everything before them but found one defect
  class left in the P3 path. (Q1) `reopen_unreadable` checked identity by path, then chmodded
  by path — `follow_symlinks=False` stops a link but not a real foreign directory swapped in
  between: the root's descriptor is now HELD OPEN from creation to retention, identity is fstat
  and the mode restore is fchmod on it (a stripped read bit changes nothing), "still at its
  path" is an lstat compared against it, `reopen_unreadable` is deleted, and the held
  descriptor is closed exactly once on every path — success, refusal, integrity failure,
  injected error (proven by counting closes in the tests). (Q2) The root string was resolved
  after creation, so a base level swapped in between pointed it into the stranger even though
  the root was correctly made in the pinned base: the string must now name the very folder just
  made (os.stat against the creation fstat) or the run is refused. The no-deletion rule, the
  device+inode identity proof, the 0/1/2/3 statuses, both refusal rules, the ledger
  instruction, header masking and all accepted F/N/P behavior are unchanged. The three new
  tests fail on 87709ab (5 failures, 1 error) and pass after.

- 2026-09-29 — A3 third corrective (third review P1–P5), delivered for independent re-review:
  the third review of cc5b862 closed N2–N5 and all F findings but found N1 only half-closed and
  four more defects. (P1) The base levels were opened by full path, so a swap of
  `.vibe-to-engineering` after it was judged redirected the root into a stranger and chmodded it:
  the levels are now chained by descriptor (each opened through its parent's descriptor with
  dir_fd, created with mkdir(dir_fd=) when missing), the base descriptor stays open, and the
  scratch root itself is created with mkdir(dir_fd=base), opened with O_NOFOLLOW and registered
  from fstat. (P2) A foreign real folder moved in as home/ or tmp/ was chmodded without any
  race: home/ and tmp/ are now registered by device and inode at creation, and only an inner
  descriptor whose fstat matches is fchmodded — anything else is a stranger, skipped untouched.
  (P3) A check stripping its own root's read permission was misreported as "did not make" with
  exit 3 (9204241 restored it and exited 0): identity is now confirmed by lstat, the owner's
  permission restored never through a link (follow_symlinks=False), and the root re-opened and
  re-verified. (P4) Two fstat calls sat outside the OSError handling: both are wrapped into
  Fail, so no raw error can escape into main's finally. (P5) The N1 swap test passed vacuously
  on the descriptor-pinned retain — its lstat hook could never fire: it now hooks the chmod
  itself and every injection hook asserts it fired. The no-deletion rule, the device+inode
  identity proof, the 0/1/2/3 statuses, both refusal rules, the ledger instruction, header
  masking, all accepted F/N behavior and zero-descriptor-leak error paths are unchanged. The
  four new regressions fail on cc5b862 (3 failures, 1 error) and pass after.

- 2026-09-29 — A3 second corrective (re-review N1–N5), delivered for independent re-review:
  the re-review of 9204241 closed F1–F5 on their reproductions but found five more defects
  inside the corrective itself. (N1) The identity check and the chmod were two path operations
  with a swap window between them — an injected swap chmodded a stranger through a link:
  everything is now done through one descriptor (open with O_DIRECTORY|O_NOFOLLOW, fstat for
  the device+inode match, fchmod), home/ and tmp/ opened through it with dir_fd, and
  scratch_base's levels likewise. (N2) A check removing its own $TMPDIR got exit 3 — a
  regression from 569c8f9's exit 0: a missing or non-directory home/ or tmp/ is skipped; only
  a failure on the verified root itself is the integrity failure. (N3) The inside-the-project
  check compared strings and a different letter case walked past it on a case-insensitive
  filesystem: containment is now judged by device and inode, walking the base's ancestors
  against the project's stat. (N4) check_base ran before --env/--with-path validation, so an
  early refusal still created the base folders: it now runs inside construct, after every
  validation, just before the root. (N5) The evidence header still claimed "kept after the
  run … mode 0700" when the root was gone: it now reads "its retention is reported on
  stderr", claiming nothing itself. The no-deletion rule, the device+inode identity proof,
  the 0/1/2/3 statuses, the refusal contracts, the ledger instruction, header masking and all
  accepted F1–F5 behavior are unchanged. Each finding has a regression in
  `tests/test_a3_corrective.py` that fails on 9204241 (6 failures there, including the header
  wording the N5 fix supersedes) and passes after.

- 2026-09-29 — A3 corrective, delivered for independent re-review: the first A3 review
  (569c8f9) reproduced three blocking defects and two minor ones, all in states the original
  tests never created — a check tampering with the scratch BASE, not only its own root.
  (F1) A base failure after the launch crashed with a traceback, exit 1 and an unmasked
  emission: retention no longer creates or changes anything at the base (`verify_base`,
  lstat only; the chain is made once, at construction), and every OSError there is a governed
  Fail — exit 3 with the recoverable record still emitted. (F2) `scratch_base` followed a
  link at `runs`: the chain is now validated level by level — a link, a non-directory or
  another user's folder is refused before any root is made, chmod never passes through a
  link, and `check_base` refuses a base that would stand inside the project. (F3) The
  recorded "mode 0700" was never checked: retention re-asserts it on the VERIFIED root and
  its home/ and tmp/ (lstat first, never through a link), and the evidence header no longer
  words retention as already confirmed. (F4) Under umask 000 the intermediate level could be
  left 0777: each level is created and re-asserted 0700. (F5) FIX-FIRST's "strictly scoped
  cleanup" wording updated. The no-deletion rule, the device+inode identity proof, the
  0/1/2/3 statuses, the refusal contracts, the ledger instruction and header masking are
  unchanged. Each finding has a regression in `tests/test_a3_corrective.py` that fails (or
  errors) on 569c8f9 and passes after — 6 failures and 1 error there, all passing now.

- 2026-09-29 — A3, scratch retention (the retained R2-F1 obligation, owner decisions of 2026-09-29):
  the tool no longer deletes anything. The check's run-owned scratch root — and the enrollment probe's —
  is retained when the run ends instead of removed: `childenv.cleanup` is gone, replaced by
  `childenv.retain`, which keeps the R1 identity proof (registered, run-prefixed, directly inside the one
  scratch base, matched by device and inode) and leaves the root standing; a moved, replaced or linked-over
  root is still reported as a post-launch integrity failure (exit 3), and whatever stands there is left
  exactly as found. A tool that never deletes can never delete data the run did not make, closing R2-F1 by
  construction rather than by a race-proofed deletion. The scratch base moves from `/tmp` — which the
  operating system reaps on its own schedule, so deletion would not be the human's act — to
  `~/.vibe-to-engineering/runs/`, created and re-asserted mode 0700 beside the runner registry. The
  retained root's path is recorded in the evidence header and on the stderr summary, with the warning that
  it may hold sensitive output; listing is allowed, deletion stays the human's own act, and the protocol
  (SKILL.md) records the path in the project ledger with each check's numbers. Exit statuses are unchanged:
  2 still means nothing ran and no evidence; a refusal past construction now retains its (check-free) root
  like any other run. Corrective tests: retention survival with contents, a foreign sentinel moved inside
  the root untouched, refusal of every non-run-owned path and of links, retained roots on pre-launch
  refusals past construction, the R1 swap/link/moved-root integrity battery re-pointed at retention, and
  the evidence-level proof that both a successful and a refused run keep their roots with the header and
  stderr records. Previously accepted A1/A2/R2 mechanisms and tests preserved. Not a release; NEW-5 and the
  remaining release gates (A4, documentation sweep, regression re-verification, workflow exam, fresh-user
  exam) stand.

- 2026-09-29 — Record the owner's acceptance of F3-R1 after Kimi's independent re-review:
  both original refusal leaks and independent variants are protected; all 307 tests passed in
  that review, including all four required reader-matrix tests, with no skips or errors.
  Add `LASTUPDATE.md` with accepted work, evidence, remaining release gates and A3 as the next
  implementation step; update README and FIX-FIRST to point to the current status. This is a
  repository update, not a versioned release, installation, whole-skill approval or NEW-5 closure.

- 2026-09-28 — F3-R1 follow-up for independent re-review: retain ambiguous option candidates for
  redaction so attached `--env` values are protected even when `--e` / `--en` is refused, including
  values with spaces and declarations supplied later. Exact options and command boundaries retain
  their meaning. New real-CLI regressions reproduce the refusal leaks before and verify privacy, no
  launch/evidence/registry change and accurate refusal results after. F2/F6 and accepted work preserved.

- 2026-09-28 — R2-F2/F3/F6 corrective, delivered for independent re-review: protect complete output
  against marker-edge reconstruction, recognized-file values, fixed prefixes and help; use the parser's
  option table for early collection, including abbreviations and missing operands; retain known child
  results through post-launch failures and emit a recoverable stderr result even when words/digits
  collide with protected values. The result schema and callers' pass criteria are documented in
  `references/emission-boundary.md`. New corrective/transport regressions accompany the stronger existing
  confidentiality battery (no body-only scan or missing-outcome exemption). Accepted A1/A2 and the
  verified R2-F4 path mapping are preserved. No release, registry migration, installation or new slice.

- 2026-09-28 — R2 confidentiality/status slice (R2-F2, R2-F3, R2-F4, R2-F6; root-cause classes II and III,
  owner decision 5.3), delivered for independent review: no declared `--env` value appears in any byte the
  wrapper emits — mask labels fall back to a value-free marker when a name holds a masked value, and the
  final generated text (header, labels, summary) passes the redaction context through the one governed
  emission path (`scripts/emission.py`); two-phase admission collects the maskable values from the raw
  arguments before parsing or validation, so usage, parser errors and early refusals never expose a value
  supplied in a later argument; the evidence header records the validated `--with-path` entries the child
  actually received, retained from construction instead of re-resolved after the run; and the wrapper's
  exit status is its own namespace — 0 the check ran and its evidence was produced (never "the check
  passed"), 1 a wrapper operational failure, 2 a pre-launch refusal, 3 a post-launch integrity failure —
  with the check's own exit code or signal recorded as data. Regressions: `tests/test_final_review_r2.py`'s
  new Emission/RecordedPaths/WrapperStatus classes, the generated battery in
  `tests/test_r2_confidentiality.py` and the full status matrix in `tests/test_r2_status.py`, each failing
  against the pre-slice candidate (and the four findings' regressions against the historical R2 snapshot)
  and passing after; one pre-existing assertion was mechanically remapped to the approved status contract
  (the baseline masking test now asserts wrapper 0 plus the recorded child outcome instead of the child's
  exit code passing through). Accepted A1 and A2, the F03-sealed files and the other slices remain
  unchanged; A3, A4 and release remain separate work. No release, installation or readiness claim.

- 2026-09-28 — A2 corrective delivery for independent re-review (A2-F01/F02/F03): compare the probe
  copy's own size and SHA-256 with the approved identity before executing it; require a root-owned,
  non-writable, ACL-free chain through every ancestor for path pinning, rechecked after approval and on
  every run; refuse malformed registry encodings and non-integer schema versions with exit 2. Existing
  unsafe path entries require manual re-enrollment. `tests/test_a2_corrective.py` reproduces the original
  failures with real compiled invocation markers and keeps neighboring swap, refusal and safe-run controls.
  This supersedes the immediate-folder/Xcode path-pinning claim in the original A2 delivery below; accepted
  A1, the supported runner profiles, F03-sealed files and other slices remain unchanged.

- 2026-09-28 — A2 runner identity (R2-F5; owner decision 5.2 and release decision 3.3), delivered for
  independent review: per-user runner enrollment at `~/.vibe-to-engineering/runners.json` replaces the
  per-run profile probe that itself executed untrusted candidates, and the launch is pinned to the enrolled
  bytes instead of re-resolving the command name. Enrollment (`evidence.py --enroll-runner <runner>`)
  discloses the resolved path, size and SHA-256 and runs the one profile probe only after the typed approval
  word, never reusing an approval for different bytes; routine validation is hash-only and never executes
  the candidate. The original path-pinning assumption (file plus immediate folder unwritable, including
  Xcode) was found insufficient in independent review and is superseded by the corrective entry above.
  Pin copy launches from a private copy written from the same reading that was hashed — so a
  replaced binary, a retargeted symlink or a swap between validation and launch cannot substitute another
  program. Unenrolled, malformed, unsupported or changed identities refuse before the check runs (exit 2,
  no evidence), naming manual re-enrollment; nothing is enrolled or re-enrolled automatically, and the
  documented boundary stands: enrollment is not protection against an attacker controlling the user's
  account. The evidence header now attests the enrolled identity launched. Regressions:
  `tests/test_final_review_r2.py` (10 tests, 23 failing subtests against the pre-A2 candidate, all passing
  after); R1's F5 tests keep their invariants at the enrollment gate; every evidence-running test now works
  against an isolated enrolled test HOME (`tests/enrolled.py`). A3/A4, the other R2 findings and release
  remain separate work; no release, installation or readiness claim.

- 2026-09-28 — A1 corrective round, delivered for independent re-review: refuse consecutive
  single-quoted backslashes that python-dotenv decodes differently, Unicode controls other than TAB,
  and Unicode/U+FEFF quoted-edge whitespace. Preserve normal quoted Unicode, interior TAB and
  single literal backslashes. Matrix execution/output failures no longer become passing empty results;
  archive provenance now verifies extracted imports, entry mappings and the actual harness. Added
  fail-before/pass-after regressions and live-reader counterexamples. Protected F03 files and
  out-of-slice A2–A4/B/C/D remain unchanged; no release, installation or readiness claim.

- NEW-5, the v0.1 literal `.env` boundary (A1, owner-approved 2026-09-27): instead of modeling each `.env` reader's readings — the ported bash 3.2 parser, Node's and npm dotenv's loaders, python-dotenv, and old npm dotenv's `$NAME` interpolation — a recognized `.env` file is now admitted only when it fits a positive literal grammar (`envliteral.py`; `references/env-boundary.md`): blank lines, `#` comments and literal `[export ]NAME=VALUE` assignments, with the unquoted character set, the quoting rules and the duplicate/CRLF/BOM refusals exactly as approved. Anything else — a `$` or backtick anywhere in a value (single quotes included), an unquoted byte outside the probed set (braces included, after the independently reproduced `export A=x{a,b}` → `xb` bash case showed the combination, never the isolated character, is the operator), whitespace inside an unquoted value or at a quoted value's edge, a duplicate name, a carriage return, a bare line — refuses before launch: exit 2, nothing runs, no evidence. The masked set for an admitted line is the line's single unanimous decode across the claimed readers, plus npm dotenv 15.0.0's quoted-empty forms. The claimed npm dotenv range is reduced to 0.4.0–18.0.4 (0.1.1–0.2.0 truncate at a second `=`, 0.1.1–0.3.0 strip quotes anywhere), with 0.5.0's recorded limitation (its `load()` applies nothing when `.env.<NODE_ENV>` is absent; it decodes normally in its two-file setup). The evidence: the 2026-09-27 reader-compatibility experiment (107 readers × 83 fixtures + 5 two-file cases, 8,891 recorded observations, provenance and hashes on file) and the new in-suite differential matrix (`tests/test_literal_matrix.py`), which runs the implemented grammar and masking logic against every claimed reader live — bash 3.2, Node v20.7.0/v20.20.2/v22.0.0/v22.16.0/v24.21.0/v26.10.0, all 87 dotenv releases in range, python-dotenv 1.2.3, artifacts re-verified against recorded hashes — proving every admitted form's decode stays inside the masked set and every divergent form refuses. Regression expectations the boundary contradicts are superseded by explicit refusal tests, each proving the check never launched, with the mapping and reasons recorded in `references/env-boundary.md` and at each changed test; the reader models remain in the tree as provenance, no longer wired, their removal a separate decision.

- F02: store commands could still change a file outside the store. The store check now stops at any store folder it cannot read, and refuses any store file that is also another file's name (a hard link), apart from the three files the tool replaces whole; git runs on the store with `core.logAllRefUpdates=false`, so it creates no missing reference log — a log that already exists still receives appends, and the hard-link refusal keeps them inside the store. Tests cover both routes, with hard links in reference logs, deep references, `packed-refs` and objects, and an existing reference log with one name and with two.
- F03: the check that a nested repository holds no unsaved work ran `git status` inside it, and `git status` runs any filter program the git settings name whenever it re-reads a file — so a program could run during a checkpoint. The check now never asks git to read a file: it takes git's lists (staged changes, untracked files, index entries with the stat data git recorded) and compares each file itself — by that stat data, or by hashing its bytes where the stat data does not settle it — plus links, the executable bit and submodule commits. A file git converts on checkout (line endings, a filter) counts as changed once its stat data changes; `git status` run by the human refreshes git's record. The refusal now says what it found.
- F06: a nested repository the project's git ignores was recorded as an ignored folder and never checked, so a checkpoint could be created while its uncommitted work was held nowhere. Ignored nested repositories — also inside an ignored folder, and repositories nested inside a nested one — are now named and checked like the others. Each stays recorded where the store format has always kept it — once, with a trailing `/`, on the `ignored-by-git:` line — so an older tool reads a new checkpoint the same way; a disappeared one is reported `gone`. A nested repository that an ignore rule starts or stops matching is no longer reported `gone` (NEW-4): it only moved from one of the two lists to the other.
- NEW-1: a repository git refused to open (another user's folder: "detected dubious ownership") was treated as a plain folder, so tracked files matching an ignore rule were left out of every checkpoint. Now only git's own "not a git repository" (read untranslated) means a plain folder; any other failure stops the command with git's message.
- F08: markup that Python's HTML parser and the browser read differently (a comment closed with `--!>`, a `<style/>`) could still run an event handler or load a local file into the PDF. The renderer now prints a temporary copy that starts with a content security policy (`default-src 'none'`, inline styles, `data:` images and fonts only), so the browser itself runs no script and loads no file or address, whatever markup gets past the checks. A `<meta>` refresh, which no content policy stops, is refused: the raw text may hold only the template's two `<meta>` lines.
- NEW-2, found by trying the tool on a copy of a real project (FIX-FIRST item 6): `create` failed with "Argument list too long" on any project with many ignored files, so no backup could be made and no migration could start. The F07 correction lists every ignored file in the checkpoint's message, and the message was one command-line argument: a real Electron app's 32,651 ignored names came to 2.9 MB, where macOS allows 1 MB of arguments and Linux 128 KB for one argument (about 1,500 names). The message now reaches git on standard input.
- F03, round 2: a nested repository set up as a partial clone made git fetch a missing object the moment the check read it — through a remote helper, before the refusal, and git wrote `partialclonefilter` into that repository's config. Every git call now runs with `GIT_NO_LAZY_FETCH=1`, so a missing object is a plain error and the check refuses with nothing run and nothing written; on a git older than 2.46, which has no such switch, a nested repository or a store configured as a partial clone is refused outright.
- F06, round 2: a committed symbolic link replaced by a plain file holding the link's target was called clean. It is now a change (what git shows as ` T`), unless the repository's `core.symlinks` is off — the one case where git itself keeps links as plain files.
- F08, round 2: a non-breaking space, a vertical tab or an em space before `<!DOCTYPE html>` is body text to the browser, so the policy inserted after the doctype landed in the body and the browser ignored it. The renderer now refuses a plan with anything but a byte order mark and ordinary spaces before the doctype, before the browser starts — and treats any content-security-policy line the browser logs (the policy ignored, or something in the plan running into it) as the browser's own verdict: the print is refused and the PDF deleted. A plan that an event handler or a local image got into no longer prints with holes; it is refused with the browser's sentence.
- NEW-1, round 2: a `.git` file whose pointer is broken made git say `not a git repository: (null)`, and the message test read that as a plain folder. A folder is plain only when no `.git` entry exists in it or in any folder above it and git says `(or any of the parent directories)`; `GIT_CEILING_DIRECTORIES` is dropped from the environment like the other variables that change what git opens.
- NEW-5: `evidence.py` leaked values from files it recognized as secret: an inline comment made the exact value miss, a JSON `"password"` key was not read, a `.env` that is a link was skipped, a folder that cannot be listed was skipped without a word, and a value under four characters was left alone. It now reads every `NAME=VALUE`, `name: value` and `"name": "value"` form anywhere on a line, quoted or not, with and without the comment; follows a link to a plain file; stops the run when a folder cannot be listed or is a link; masks a short value as a whole word; and always masks a value under a name that says secret (key, token, password, pin…) — while a number or a yes/no word under any other name (`PORT=8000`) stays readable and is named in the summary, so nothing is certified silently.
- NEW-6: a file that holds secrets was fingerprinted by its modification time, so a replacement of the same size with the time preserved was called unchanged. Such files now get a keyed fingerprint — HMAC-SHA256 with a random key made on first use in `.vibe-to-engineering/fingerprint.key` (owner-readable, guarded like the store, never in a checkpoint) — so a changed byte is reported while the checkpoint's message gives away nothing about the file, unlike a plain hash of a short secret. A checkpoint from before the key still compares by modification time.
- ENG-01: `checkpoint.py` (1,290 lines) and `tests/test_checkpoint.py` (1,330) were split by responsibility, with every moved definition and test method byte for byte the same: `gitrun.py` runs git safely and holds the platform helpers, `nested.py` checks nested repositories, `watched.py` watches ignored files, `treeview.py` prints the tree; `tests/support.py` holds the shared fixtures, `tests/test_nested.py`, `tests/test_watched.py` and `tests/test_tree.py` the tests of those parts. The command line, the store format and the test seams are unchanged.
- NEW-5, round 3: values from recognized secret files still reached the evidence in forms the line-by-line reader did not see: a JSON value written with escapes (`9`…), a YAML block value (`password: |-` and the indented lines after it), a `.env` value quoted over several lines, one line of a private key's body, a key file holding one bare value, and a UTF-16 file read as UTF-8. `evidence.py` now reads a quoted value across lines and in its decoded form, a YAML block value whole and line by line, a JSON file as one document (a list's members included), and every line that gives no name a value as a value in itself; it decodes a file by its byte order mark; and a secret file that is not text it can read — binary, or an encoding without a mark — stops the run before the check, naming the file, instead of being read as nothing.
- F03, round 3: on a git older than 2.46, a partial clone recorded as a gitlink inside a nested repository had its commit read — through a remote helper — before its own check refused it. The partial-clone refusal now comes before that read as well.
- NEW-6, round 3: a checkpoint from before keyed fingerprints recorded a secret file's modification time, and `diff` and `restore` compared that with the file's time now — so a replacement of the same size with the time preserved was called unchanged; a checkpoint that recorded no contents at all made every watched file look unchanged. Such a record is compared with nothing now: `diff` and `restore` list the file as `unknown`, saying which side recorded only a time or nothing, and a diff against such a checkpoint never ends in "no changes". Old checkpoints stay readable; nothing is rewritten.
- NEW-5, round 4: recognized secret files still leaked in forms the line-by-line reader did not understand — a YAML flow list, a YAML block value whose header carries a comment, a TOML `"""…"""` value and one written with `\uXXXX` escapes, a YAML `''` apostrophe (a secret suffix left after the mask), and a private key's body read as a setting's name (the payload shown in the mask's own label). `evidence.py` now reads each secret file whole with one reader per format (`secretformats.py`: `.env`, JSON, YAML, TOML, INI, Java `.properties` and key files; any other file line by line, as written) and collects every value in every form a program may print it in (`secretforms.py`: as written, as python-dotenv, Node, a shell, PyYAML, tomllib, configparser and Java decode it, and each part a program may print alone: a word, a list's member, a URL's password or query value, a `NAME=VALUE` inside it). A file its reader does not understand stops the run before the check. The net for a value given to a name that says secret, and the token shapes, now look at the output as printed as well as with the values found blanked out — masking values one after another had let a masked piece of a setting's name hide `NAME=value` — while a value masked already still counts as the edge of a word, as its mask did; and a mask is never labelled with secret text. A number inside a value with a plain name stays a readable setting, as the owner's rule reads it; a list's member or a line with no name never is.
- F03, round 4: a repository whose git keeps a sparse index (`git sparse-checkout set --sparse-index`) was changed by the check that is meant only to read it: listing its index made git expand it, writing a tree object and freshening two object timestamps in a nested repository — and, on an older git (emulated), fetching through the remote helper first — all before the refusal. The same happened in the project's own repository, through `git check-ignore`, and `create` then succeeded. `gitrun.py` now reads git's index file itself (versions 2 to 4, SHA-1 and SHA-256 ids, a split index's shared file) and refuses a sparse index, nested or the project's own, before git runs anything that reads it; the older-git partial-clone refusal now also comes before the listing. A sparse checkout without a sparse index is inspected as before.
- NEW-5, round 5: values from recognized secret files still reached the evidence, whole or in part, through readings the collector did not make — a YAML value tagged binary through a `%TAG` handle (`!e!binary`, or `!binary` for the primary handle), which PyYAML decodes; and a `.env` value a shell sourcing it reads with arithmetic inside `"…"`, hexadecimal arithmetic (the reading was dropped without a word) or `${#NAME}` (a `12` was left between two masks). The YAML reader now resolves every tag through the document's `%TAG` handles — verbatim `!<…>` tags and `%`-escaped letters too — and stops the run at a tag PyYAML decodes to bytes or a Python object (`binary`, `python/…`), or one written flush against what follows it, never re-reading such a file as a template's text. The shell's reading of a `.env` value now works out arithmetic inside `"…"` and in bash's `$[ … ]`, octal and hexadecimal numbers and `${#NAME}`, reads a `${…}` holding a space whole, and reads each further assignment a shell makes on the same line — an unquoted URL's `…&password=…` included — as a value found inside that line's own, named after it; a reading only the shell can make — a command's output (`$( … )`, backquotes), arithmetic it does not work out, any other `${…}` form, `$$`, `$!`, `$-`, `$0` and `$_` — stops the run before the check, naming the line, where it used to be dropped. Nothing inside `'…'` is expanded, so a single-quoted `pa$$word` still reads. Tests also cover three protections the round-4 mutation run found untested: a padded bare token whose would-be name holds a secret word, a URL fragment's `;`-separated parameters, and a `.env` file that is one JSON document.
- NEW-5, round 6: four more readings still reached the evidence, whole or in part. (1) A valid YAML file the reader stopped on was read as a template's text whenever that line held `{{` or `{%` anywhere — in a comment or a quoted value — so a binary tag PyYAML decodes, on that line or further on, was never refused. The text reading is now taken only for a marker in the line's data (not in a quoted value or a comment), and never for a file holding a tag PyYAML decodes. (2) `${#NAME}` measured another reader's value of NAME, not the shell's: the `.env` reader now keeps the shell's own variables — each value exactly as the shell makes it (arithmetic, quotes, escapes, continued lines, `$'…'`), assignments in order on one line, `+=`, a background job and a one-command assignment changing nothing, `export`/`readonly` expanding all their words before assigning — and refuses what it cannot follow: `&&`, `||`, `|`, `( )`, a here-document, a command that sets variables its own way (`eval`, `.`, `read`, `declare`…), a reference in a command's words, a reference to an array, and an assignment inside another `${…}`, which a shell makes only when that branch is used. (3) `export -n`, `declare -x` and other builtin options lost the value they assign: an option other than `--` now stops the run, and `export --` / `readonly --` values, and a `readonly` line of its own, are read. (4) Arithmetic past the shell's signed 64 bits, which the shell wraps around without a word, now stops the run instead of being worked out differently.
- NEW-5, round 7: a `.env` value a shell builds from something the file does not set reached the evidence unmasked: `DB_PASSWORD=${SECRET:-safe-fallback}` was read with `SECRET` unset, but a shell sourcing the file inherits `SECRET` from wherever it runs, so the check printed the inherited secret and the evidence kept it. The shell's reading now stops the run before the check whenever a value depends on what the file itself does not decide — a variable the file does not set before that line (whether the environment holds it or not), `$1`, `$#`, `$?`, `$@`, `$*`, one of the shell's own variables (`RANDOM`, `SECONDS`, `LINENO`…), `~` without a `HOME` the file sets (and `~+`, `~-`), `NAME+=value` on a name the file has not set, an assignment to a name the file made read-only, and — after a command a function inherited from the environment could stand in for — any variable set before it. A reference in a part the shell skips (`${A:-$SECRET}` when the file sets `A`) is not read, as the shell does not read it. Found alongside, each shown leaking on the round-6 candidate and closed the same way: a length or a trimming pattern the locale decides (a value outside ASCII, a `[a-z]` range, an extended pattern), a `$'…'` escape shells decode differently (`\u`, `\U`, `\c?`, a byte that is 0 or outside ASCII), `$"…"`, and `${NAME:?word}` on an empty value, where the shell stops and prints the word. And read as the shell reads them now: `~name`, from the user database; a value holding a literal `$`, never read again for references; a line python-dotenv reads as the rest of a quoted value (after `'x\'`), which was never read for the shell at all; a Windows line break's carriage return, which the shell keeps in the value. A refusal message no longer shows the command word it stopped on.
- NEW-5, round 8: the round-7 re-review found six more ways a `.env` reading and the real reader parted, four of them leaking an inherited value into the evidence, and each is closed as its reproduction asked. A function inherited from the environment (`BASH_FUNC_frob%%`) can stand in for any command a `.env` file runs and change a value the file set before it: such a value now stops the run unless the file sets it again after the command — a `NAME=value` on that command's own line too, which bash keeps after a function (so an unquoted value with a space, `APP_NAME=My App`, stops the run unless set again). A `.env` file that starts with a byte order mark stops the run: a shell reads the mark as part of its first word, and the reader used to decode it away. A `.env` file whose text is also one JSON document is never read as JSON instead when its shell reading refuses it. A part of a `${…}` the shell never evaluates is never refused for what it holds — `${A:-$(printf x)}`, `${A:-${B:=x}}`, backquotes, `$$`, arithmetic, `${!A}` or an array's element there — and is refused as before where the shell does evaluate it; a part whose end the reader cannot find as bash finds it (a quote, a backslash, a `{` or `}`, or a `#` inside) still stops the run. `~name` stops the run: the user database decides it, never the file. python-dotenv (checked against 1.2.3) fills `${NAME}` into every value — quoted or escaped — from the environment when no earlier line sets `NAME`, and its `load_dotenv()` keeps a value the environment already holds: a `${NAME}` python-dotenv fills for a shell-style name the file has not set earlier now stops the run whatever the environment holds, and so does any name python-dotenv reads that the environment the check inherits holds (a key the file names, a name it fills in) — the names only, never their values; a name `--env` gives is the check's own and never stops it. Decided by the owner (2026-09-25): refuse for python-dotenv, never model the environment; a skipped part is never refused for what it holds; `~name` is refused.
- NEW-5, round 9: the round-8 re-review found a part of a `${ … }` the shell skips still refused for a quote, a backslash, or a quoted or escaped command's output inside it (B4), and Node's own `.env` loader keeping an inherited value under a key python-dotenv does not read — `'DB_PASSWORD'=from-file` gives Node the key `'DB_PASSWORD'`, quotes and all (NODE-PRECEDENCE). Where a `${ … }` ends is now found as bash 3.2 finds it, ported from its own source (the word as `parse.y` reads it, the expansion as `subst.c` ends it): valid syntax in a part the shell skips is masked as the shell prints it, and where the shell reads that part — or ends the `${ … }` elsewhere, or never — the run still stops. A key a Node loader that keeps an inherited value reads — Node's own parser in each of its forms since v20.7 (every release from v20.6.0 to v26.10.0 compared, its own code compiled and run), and npm dotenv in every release that keeps an inherited value (v0.1.1 to v18.0.4, its opt-in fast parser too), each ported from its source (`nodekeys.py`) and checked against Node 20.20.2, its JavaScript engine, and each npm dotenv release's own code run in it — stops the run when the check's environment already holds it (names only, never values). Found on the way, and corrected by the owner's decisions (2026-09-26): a `${ … }` with anything but an operator after its name (`${A${B}}`, `${A$(cmd)}`), which bash rejects as a bad substitution and so assigns nothing, was read as `${A}` and an inherited value reached the evidence (BAD-SUBSTITUTION; round 8's marks added four of its forms); and a quote the shell never finds closed, where it stops reading the file, was accepted when no other reader saw it (UNCLOSED-QUOTE). Both now stop the run. Found as well, and corrected the same way while the owner's ruling on it is asked for in the round-9 handoff: bash keeps a byte of its own (\x01) in a value where a backslash stands before a raw DEL byte in `"…"`, or a raw DEL or \x01 byte in `$'…'`, which the reader's value did not have, so the value reached the evidence unmasked (round 8 too; B4 let more words reach it) — such a word now stops the run; and inside `"${ … }"`, a `$'…'` decoding to a backslash, before another `$'…'`, now stops it too (bash reads that backslash with what the next one decodes to). The cost: a `.env` file a shell cannot read to its end — an apostrophe in an unquoted value — stops the run; the few valid shapes still refused are listed in the round-9 handoff.
- F03, round 5: inspecting a repository whose git keeps a split index (`git update-index --split-index`) rewrote the modification time of its shared index file — git refreshes that file every time it reads the index, and `ls-files` in a nested repository and `check-ignore` in the project's own read it before anything else. `gitrun.py` already read the index file to find a sparse index; it now also refuses a split index (a `link` extension naming a shared index), nested, ignored or the project's own, before git runs anything that reads it, so nothing in that repository changes. Turning the split index off there stays the human's decision. A repository with an ordinary index is inspected as before.
- NEW-5, stage 1, final-review corrective R1 (2026-09-27): the first final independent review of the stage-1 candidate found eight blocking findings (five High, three Medium); each is corrected at its underlying invariant, with a regression test that fails against the reviewed candidate and passes after (tests/test_final_review_r1.py — 20 failures and one error there, all passing now), nearby variants covered, and no existing boundary weakened. (1) Cleanup could delete whatever stood at a registered scratch-root path: a check owns its scratch root and can move it away or put a foreign folder, link or file in its place, and the reviewed candidate removed it — data loss. The object at the path is now matched by identity (device and inode) against the root the run itself made before anything is deleted. (2) An admitted --env value that was short, all digits, or embedded in a longer word reached the evidence raw (only whitespace-and-'=' values were never masked at all): every declared value is now masked wherever it appears, and a value of only whitespace and '=' is refused at admission because it could not be masked. (3) A refusal naming a --with-path folder echoed the folder even when it held a declared value: every diagnostic from admission onward is redacted against the declared values. (4) A --with-path folder whose name holds the PATH separator entered PATH as several entries, the rest never validated: refused, as is a link resolving to one. (5) The supported-runner gate trusted a resolved file's name, judged against the wrapper's own folder: the executable is now resolved under the launch's working directory, must be an existing executable file, must be a real executable binary of the platform (a script under a runner's name is refused without ever being run, so a lookalike's payload cannot act even during vetting), and must answer its supported profile when probed — one fixed benign invocation under the constructed environment from inside the run's scratch root — with Node held to the registry's version bounds; a lookalike named node is refused before anything runs. (6) A cleanup failure after the check had run and evidence was written was reported as exit 2, the refusal code: post-launch integrity failures are now exit 3, with the check's outcome reported; exit 2 is reserved for refusals where nothing ran and no evidence exists. (7) A .env shell reading the file does not decide was still refused under the inheritance-era rule although the constructed environment decides it (D4 rule 5): such readings are now computed from the one mapping — the value it holds, empty where it holds no such name — and refusal stands only for what stays indeterminate ($1 $# $? $@ $*, the shell's own variables, the ones it sets itself at startup — measured on bash 3.2: PWD, SHLVL, HOSTNAME, HOSTTYPE, MACHTYPE, OSTYPE, IFS — ~name, ~+ ~-, the locale's lengths and patterns); the inheritance-era STALE rule is gone with it, since no inherited function can stand in for a command under the constructed environment (D3). (8) Two supported reader profiles had no live real-reader evidence: npm dotenv v0.4–1.2's interpolation now has each release's own lib/main.js (0.4.0, 0.5.0, 0.5.1, 1.0.0, 1.1.0, 1.2.0) run in Node over the model's cases — all matched — and python-dotenv 1.2.3's own wheel ran against the model's per-value, interpolation and load_dotenv precedence readings, all matched (owner-authorized one-off throwaway fetches; nothing vendored; method and outputs in references/stage1-acceptance.md).
- NEW-5, stage 1 (the architecture change the rounds converged on; the design contract and its seven owner decisions are on file): a check used to inherit the environment of wherever the tool ran, filtered by a list of names known to be dangerous — and every channel not yet on that list (a proxy variable, `NODE_OPTIONS`, a `GIT_*` setting, a loader's own `DOTENV_*` key) reached the check, so the list could only grow one finding at a time. The check's environment is now constructed instead of inherited (`childenv.py`): a synthesized profile of six portable names (`PATH`, `HOME`, `TMPDIR`, `LC_ALL`, `LANG`, `TZ`) — on macOS with `__CF_USER_TEXT_ENCODING` pinned, which the OS would otherwise add to the child after the analysis — a scratch root the run owns (`/tmp/v2e-run-*`, removed by that run alone, and only what the run itself created), extra tool paths only through `--with-path` (an existing real directory, resolved), and `--env` settings admitted under a governed contract: a name must match `[A-Za-z_][A-Za-z0-9_]*`, a duplicate or an override of a synthesized name is refused, and a prohibited name never enters (`BASH_ENV`, `ENV`, `SHELLOPTS`, `BASHOPTS`, `NODE_OPTIONS`, `BASH_FUNC_*`, `PYTHON*`, `DYLD_*`, `DOTENV_*`, `NPM_CONFIG_*` case-insensitive, `YARN_*`, `PNPM_*`, `PIP_*`, `GIT_*`, the proxy names in either case, `LD_PRELOAD`, `LD_LIBRARY_PATH`). Every declared value is sensitive from admission: the evidence header records declared names only, never a value. Where a supported reading is deterministically won by a declared value, the evidence masks the declared winner instead of refusing; the run refuses only when the effective reading cannot be derived from the approved inputs — and the one constructed mapping is what the analysis reads and what the child is launched with, superseding round 9's `--env` exclusion while keeping its throwaway-data-redirection intent. A `.env.vault` file stops the run: its values are encrypted and the key that would read them lives outside the project. npm dotenv v0.4–1.2's `$NAME` interpolation is worked out from the approved inputs or the run stops. A supported-check registry (`references/supported-checks.md`) names the revalidated runners — python, sh and node, identified by the resolved executable — and an unrecognized runner refuses before execution; a check re-enters the supported set only through the four-part revalidation gate, and a failing check is quarantined, never the boundary weakened. On Windows the name rules fold case (so `Path` cannot bypass a collision or a prohibition) and `SystemRoot` is derived from the OS rather than inherited wholesale — proven structurally only: native Windows verification is pending and Windows is not claimed supported; macOS is verified and Linux needed no pin (the stage-1 cross-platform investigation). The guarantee's boundary (the owner's D5): it begins at the constructed environment of the launched child — wrapper startup before launch and the check's own behavior after it are outside it, and no sandbox is claimed. The acceptance evidence is assembled in `references/stage1-acceptance.md` for the final independent review.
- NEW-6, round 4: two genuine checkpoints from before content records, compared with each other, said "no changes" in both directions although a secret file had changed between them: neither had a content record, so there were no names to go through. A checkpoint without an `ignored-contents:` line is now read through its `ignored-by-git:` line — every watched file it names, and every file inside a folder it lists as one entry, is listed as `unknown`, whichever side it is on — and `watched_names()` is the one filter that reading and the fingerprints share. Nothing in the store is rewritten.
- FIX-FIRST item 9: four safety checks had no test that fails when they are removed — the snapshot compared with the disk, the re-check just before a restore changes files, the "nothing lost" check after a restore, and the renderer's element list. Each now has one: a file changed while it is saved, a file written after the restore was verified, an ignored file lost while the restore writes, and a bare `<a>`.
- RA-01: `tree` listed only the files a checkpoint saves, and left out without a word every file git ignores, every nested repository and the skill's own folder — so "left alone on purpose" looked the same as "never seen". It now shows every file where it sits: ignored files, nested repositories and `.vibe-to-engineering/` are marked, a folder holding only ignored files (dependencies, build output) is one line with its count, and the last line counts each kind. `tree <label>` shows the lists that checkpoint recorded. `--saved-only` prints exactly the old output. SKILL.md shows the human the full tree, the plan keeps the marked lines, and the final review compares them too.
- RA-03: checkpoints recorded ignored files by name only, so an overwritten, emptied or corrupted ignored database passed every check — and it is the one thing no checkpoint can bring back. Each checkpoint now also records every ignored file's size and fingerprint (SHA-256 of its bytes), outside dependency, build-output and cache folders; a file that holds secrets (`.env`, keys, credentials) is never read — its modification time stands in. `diff` and `restore` report a changed one; the phase architecture check and the final review treat it as a break like a `gone` one, apart from files the checks rewrite (recorded at the baseline). A watched ignored file that cannot be read stops the command. Older checkpoints, which recorded no contents, still read as before.
- RA-08: the plan listed only the files each phase changes, so nothing let the owner confirm that the whole project was accounted for. A new plan section, "Every file: before → after", has one row per file — ignored files and nested repositories included — with what happens to it and what it holds today and afterwards, under the totals from `tree`; then "Who owns each job", before and after. The final report repeats both as they came out. The overview page's trees keep `tree`'s marks with shorter labels (`[ignored]`, `[nested repository]`), and a tree line that is too long now spills visibly instead of pushing the TARGET column off the page.
- RA-02: every reason behind the new structure lived only in `.vibe-to-engineering/`, which git ignores and the owner may delete, so a project with no docs ended the migration with none. Every plan now ends with a documentation phase that leaves a short record inside the project, in the form it already uses — a new ADR, a section in its architecture notes or CONTRIBUTING, or else a "Project layout" section in the README with the key decisions and the alternatives rejected. It describes the structure, never the migration's history; the plan shows its exact text; the owner can decline it ("no docs"), which the ledger and the final report record; and the final review checks the record against the final tree.
- RA-04: nothing said that running a check must leave the owner's data alone, and a smoke run with the app's defaults writes into the real database. Checks now use throwaway data: INSPECT records where the app reads and writes data and what chooses it, the plan names for each check the data it uses and how it is redirected (a new "Data it uses" column), a check that would touch the owner's data is refused at the plan stage, one that cannot be redirected is not run, and checks write no caches into the project where the stack allows it.
- RA-05: a server smoke run could be answered by another program on the same port, or by a stale copy from an earlier check, and pass. A check that starts a server now takes a free port, waits for the app's own start-up signal, confirms before and after the calls that its own process is the one answering, starts only when no earlier process is left, stops and confirms its process is gone, and records the port, process id and start-up log.
- RA-06: nothing said how to handle a secret once found, so values could reach the transcript, the plan, the ledger and the evidence. Secret files are now read for their key names only; a committed secret is reported by file, line and key name (at most its first 4 characters). A new `scripts/evidence.py` runs every check: it prints and saves the output inside `.vibe-to-engineering/evidence/` with secret values masked — the exact values from the project's secret files, which it reads and never shows, and anything shaped like a private key, access token or password — and exits with the check's own code. Its `--env` settings point a check at throwaway data.

## [0.1.0] - 2026-09-23

- First version. The vibe-to-engineering protocol — inspect, diagnose, design the target, plan with a PDF, human approval, verified backup, one approved phase at a time with checkpoints, failure investigation, final review — with its engineering standard, the migration plan template and PDF renderer, and the checkpoint tool with its platform-independent recovery contract and conformance tests. Validated on macOS only.
