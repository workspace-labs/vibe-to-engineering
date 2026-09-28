# Supported checks — the NEW-5 stage-1 registry (D6)

This document is the registry of record for the supported-check set. A check launched through
`scripts/evidence.py` runs only when its runner is in the supported set below **and enrolled for this user**
(A2, R2-F5): the executable the command resolves to — under the launch's own working directory, so a
relative path is judged where it will actually run — must exist, be executable, match a supported final name
after links resolve, and then match the user's enrollment registry
(`~/.vibe-to-engineering/runners.json`): the resolved path must be the enrolled path and the bytes there must
hash to the enrolled SHA-256. Routine validation never executes the candidate — the pre-A2 per-run profile
probe was itself the R2-F5 defect: it gave untrusted candidates execution privileges, and the launch that
followed was not pinned to the probed bytes. `evidence.py`'s gate implements this list exactly, and
`tests/test_check_registry.py` proves the gate and this list agree. A check under any other runner, under a
runner named on the quarantine list, under an unenrolled runner, or under a runner whose identity moved or
changed since enrollment is **refused before execution** (exit 2): it was never revalidated under the
constructed environment, and an unvalidated check is unsupported. A quarantined runner re-enters the
supported set only by passing the same four-part revalidation again, with its evidence added here.

## Runner enrollment (A2)

Enrollment is the only way a runner enters the registry, and it is a deliberate human act — there is no
automatic enrollment and no automatic re-enrollment:

1. `python3 scripts/evidence.py --enroll-runner <runner> [--with-path /abs/dir]…` resolves the candidate the
   same way the gate does (an absolute path, or a name on the system folders plus the given `--with-path`
   folders, links resolved, kind judged by the resolved final name), and refuses anything that is not a real
   executable **binary** of the platform (Mach-O on macOS, ELF on Linux — a script under a runner's name is
   refused without ever being run, so a lookalike's payload cannot act even during vetting — final-review R1).
2. The tool discloses the resolved path, size and SHA-256, the pin mode, and the one probe it will run.
3. Only the typed approval word runs the disclosed probe — the profile answer each runner below, checked but
   never shown, Node held to the version bounds — and records the identity. The bytes are hashed again after
   approval, and a probe copy's own reading must also match the approved size and hash before it can execute.
4. Each entry records a pin mode. **pin: path** requires the file and **every ancestor**, checked from `/`
   downward with no-follow opens, to be root-owned, without group/other write bits, without an extended ACL,
   and unwritable by the current user. The chain is checked again after approval and on every routine run;
   an old path entry whose protection cannot be proved refuses and requires manual re-enrollment. A sandbox
   denying `os.access` is not sufficient proof. This conservative rule admits the measured `/bin/sh` and
   Command Line Tools Python under `/Library`; it rejects the admin-writable `/Applications` ancestor of
   this Mac's Xcode Python. The macOS ACL check uses the standard library's `ctypes` to read native metadata,
   never executes the candidate, and refuses path pinning on an ACL, a read error or an unverified platform.
   **pin: copy** for any other location: the launch is a private copy written from the very bytes just hashed,
   inside the run's scratch root. A candidate with neither pin mode is refused: SIP platform binaries cannot
   be copy-executed, and a framework executable can depend on its original location. No installation's name
   alone grants path pinning, and nothing automatically changes an existing registry entry's pin mode.

A moved runner (the command resolves elsewhere than the enrolled path), a changed runner (the bytes no longer
hash to the enrolled SHA-256) and a malformed registry all refuse before the check runs; the remedy named is
manual re-enrollment, never an automatic one. Enrollment is **not** protection against an attacker who
controls the user's account — such an attacker can rewrite the registry itself; the guarantee inside that
boundary is that the bytes launched are the bytes enrolled, exercised by `tests/test_final_review_r2.py`
and `tests/test_a2_corrective.py`: an
unenrolled candidate is never executed by routine validation, approval binds to the disclosed bytes, a
successful check launches bytes whose hash equals the enrollment record, and replaced binaries, retargeted
symlinks and swaps between validation and launch cannot substitute another program.

The registry is UTF-8 JSON with integer `version: 1` (booleans and floating-point values are not schema
versions) and a `runners` object. Bad encoding, JSON or required entry types refuse with exit 2, a manual
remedy, no check/evidence and no registry rewrite. Native ACL semantics are documented in Apple's
[ACL implementation](https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_file.c):
`acl_get_fd` reads an open object; absence is reported through `filesec_get_property`, not a pathname lookup.

The supported set (the gate's table, one kind per runner; the profile each must answer at enrollment):

- **python** — resolved final name `python3` or `python3.<minor>` (any CPython 3 the check's constructed PATH
  resolves; measured: 3.9.6, the macOS system Python). Probe: `-I -c "import sys; print(sys.version_info[0])"`
  must answer `3`.
- **sh** — resolved final name `sh` (measured: `/bin/sh` = bash 3.2.57 — the version the literal `.env`
  boundary's shell evidence is measured against, `references/env-boundary.md`). Probe: `echo ${BASH_VERSION:-none}`
  must answer a bash **3.2** version — any other shell (dash, later bash) is a different profile than the
  boundary was revalidated against and refuses loudly.
- **node** — resolved final name `node` (measured: v20.20.2; the `.env` reader profiles are version-bounded by
  the boundary's claimed reader set: Node v20.7–v26.10 and npm dotenv v0.4.0–v18.0.4). Probe: `--version` must
  answer a version within those bounds.

Quarantine list: **empty** (no runner failed revalidation).

A plan's check names its runner explicitly (`python3 -m pytest …`, `sh scripts/test.sh …`, `node …`), never a
bare project command (`npm test`, `./run.sh`, `make`): those resolve to runners outside the set and are
refused. A project check that cannot run under a supported runner is not run until it passes revalidation —
the human decides, per the plan rules.

## Revalidation evidence (2026-09-27, under the constructed environment of stage 1)

Each runner below completed the four-part revalidation (D6): (1) environment-dependency enumeration,
(2) absence behavior, (3) throwaway-data routing with masking, (4) boundary-invariant regression checks.
Evidence for parts 2–4 is the named tests in the suite (`python3 -m unittest discover -s tests` — 179 tests,
OK, run 2026-09-27 with the gate and the R1 corrective in place), each of which runs real checks through
`evidence.py` under the constructed environment. The 2026-09-28 A2 corrective (R2-F5) changed the gate's
mechanism — enrollment identity plus hash-only validation, the profile probe moved to enrollment, the launch
pinned to the enrolled bytes — without changing the supported set or any profile; its regressions are
`tests/test_final_review_r2.py`, and every test below now runs with the suite's runners enrolled into an
isolated test HOME (`tests/enrolled.py`), never the real per-user registry.

### python

1. **Enumeration.** A CPython check can consult: the `PYTHON*` startup and steering variables (`PYTHONPATH`,
   `PYTHONHOME`, `PYTHONSTARTUP`, `PYTHONDONTWRITEBYTECODE`, `PYTHONWARNINGS`, …) — all D3-prohibited
   (`PYTHON*` is never inherited and never admitted via `--env`); `HOME`, `PATH`, `LC_ALL`, `LANG`, `TZ` — all
   synthesized by the profile; on macOS the runtime-added `__CF_USER_TEXT_ENCODING` — pinned into the mapping
   (Gate-2 clarification); `__PYVENV_LAUNCHER__` is set by a framework build's own `main()` after launch,
   child-side, outside the boundary. Bytecode caches are governed by the check's own `-B` flag
   (`PYTHONDONTWRITEBYTECODE` can never be declared — D3).
2. **Absence.** With every inherited name absent, CPython starts cleanly — `test_a_check_inherits_nothing_but_
   the_constructed_environment` runs a check under a deliberately hostile parent environment (function
   definitions, proxies, wrong `HOME`/`TMPDIR`) and the child sees exactly the constructed mapping.
3. **Throwaway routing.** `test_a_check_is_pointed_at_throwaway_data` and
   `test_a_name_the_env_flag_gives_the_check_never_stops_the_run` (tests/test_evidence.py): the check reads
   only the declared throwaway values, and every declared value is masked in the evidence.
4. **Boundary invariants.** The whole suite, including the Round-9 controls and the B4 / skipped DEL/SOH byte
   outcomes (tests/test_evidence_readings.py), green under the new boundary.

### sh

1. **Enumeration.** A shell check can consult: `ENV`, `BASH_ENV`, `SHELLOPTS`, `BASHOPTS`, `BASH_FUNC_*` — all
   D3-prohibited, so absent: no startup file is read, no function is inherited (B1 is eliminated by
   construction); `HOME` — synthesized, so `~` resolves to the run's scratch home; `PATH` — synthesized plus
   governed `--with-path` folders only; `LC_ALL`/`LANG` — fixed (locale-decided values stay refused by the
   reader model); `IFS`, `CDPATH` and the shell's own variables (`RANDOM`, `SECONDS`, …) — absent, and the
   reader model refuses a file value that would depend on them.
2. **Absence.** The suite's shell checks source `.env` files under `/bin/sh` with nothing inherited
   (tests/test_evidence_readings.py, tests/test_env_literal.py); a `.env` file is admitted only inside the
   literal boundary (`references/env-boundary.md` — literal assignments, no references or expansion), and
   anything outside it refuses before launch, loud failure, never silent. (The stage-1 reader-model wording
   here predates the boundary; the model is superseded, the refusals retained and widened.)
3. **Throwaway routing.** Declared `--env` values reach the check and are masked wherever printed
   (tests/test_evidence_stage1.py, `test_a_declared_value_that_wins_a_reading_is_masked_as_the_winner`).
4. **Boundary invariants.** The literal boundary's own proofs — the grammar tests, the brace regression and
   combination tests (tests/test_env_literal.py), and the differential matrix over every claimed reader
   (tests/test_literal_matrix.py) — plus the retained refusal regressions (bad-substitution, unclosed-quote,
   DEL/SOH kept-byte, BOM), all green. (The inheritance-era STALE rule is gone with R1: no inherited function
   can stand in for a command under the constructed environment.)

### node

1. **Enumeration.** A Node check can consult: `NODE_OPTIONS` — D3-prohibited; `DOTENV_CONFIG_*`, `DOTENV_KEY`
   — D3-prohibited (`DOTENV_*`), so `.env.vault` can never be decrypted and a recognized `.env.vault` is
   always refused; `NPM_CONFIG_*` — D3-prohibited (case-insensitive); the proxies — D3-prohibited; `NODE_ENV`
   — absent unless declared (old npm dotenv's `.env.$NODE_ENV` second file is a recognized secret file under
   `.env.*`, masked regardless); `HOME`, `PATH`, locale, `TZ` — synthesized.
2. **Absence.** With nothing inherited, Node's loaders take the file's own values — and a `.env` file is
   admitted only inside the literal boundary, so every admitted value is the one decode the claimed readers
   agree on. A file whose keys only some loader would read (quoted, tabbed or space-bearing names, colon
   separators, bare lines) refuses before launch — NODE-PRECEDENCE is superseded by the boundary
   (tests/test_evidence_node.py, the supersession record in `references/env-boundary.md`).
3. **Throwaway routing.** A declared name a Node loader would keep over the file's is masked as the winner
   (tests/test_evidence_stage1.py).
4. **Boundary invariants.** The claimed Node reader set — v20.7.0, v20.20.2, v22.0.0, v22.16.0, v24.21.0,
   v26.10.0, and npm dotenv 0.4.0–18.0.4 — is exercised live over the admitted corpus in
   `tests/test_literal_matrix.py`, every decode proven inside the masked set.

## Rules this registry lives by

- The set changes only by owner decision, and an entry changes only with its four-part revalidation evidence
  re-executed and recorded here.
- Failure of one runner's revalidation quarantines that runner (move its entry to the quarantine list with the
  reason); it never weakens the boundary and never blocks stage-1 acceptance by itself. Failure of a boundary
  invariant blocks stage-1 acceptance.
- The run's exit status is the wrapper's own namespace, never the check's (owner decision 5.3, R2-F6): 0 the
  check ran and its evidence was produced — never "the check passed"; 1 a wrapper operational failure; 2 a
  pre-launch refusal (nothing ran, no new evidence) — the refusals this registry defines are all of that
  kind; 3 a post-launch integrity failure (the check ran). The check's own exit code or signal is recorded
  with the run as data, and a caller judges a required check by that recorded outcome. The final stderr
  line retains wrapper/launch/evidence/child facts even when literal outcome text collides with a protected
  value; decode with `emission.read_result` and require agreement with the process status. Missing or
  invalid results are unverified. See `references/emission-boundary.md` for the format and caller contract.
- Platform scope: this registry is revalidated on macOS only. No other platform is claimed (the Windows
  requirements recorded in the stage-1 design contract §13 stand; the Windows name-handling corrective in
  `childenv.py` is structural, verified by unit tests only — never natively — and does not change that scope).
