# NEW-5 stage 1 — acceptance evidence (2026-09-27, updated after final-review corrective R1)

This record assembles the evidence the final independent review is asked to confirm. It says what stage 1
built, what each acceptance test proves, how the launch path is shaped, and what is and is not verified on
each platform. The governing documents are the stage-1 design contract and its seven owner decisions D1–D7
(`~/Desktop/vibe-to-engineering-stage1-design-contract-2026-09-26.md`, decisions log in its §13) and the
supported-check registry (`references/supported-checks.md`). NEW-5 is **not closed**: closure requires this
evidence to pass the independent review, per the closure standard (D7).

The first final review (R1) found eight blocking findings; the corrective for each is implemented, regression
-tested (`tests/test_final_review_r1.py`, every test failing against the reviewed candidate and passing
after), and folded into this record below. The R2 review's runner-identity finding (R2-F5) was repaired and
accepted as A2. The R2 confidentiality/status slice (R2-F2, R2-F3, R2-F4, R2-F6) is implemented,
regression-tested (`tests/test_final_review_r2.py`'s Emission, RecordedPaths and WrapperStatus classes plus
`tests/test_r2_confidentiality.py` and `tests/test_r2_status.py` — every new test failing against the
pre-slice candidate and the provenance-verified historical R2 snapshot, and passing after) and **delivered
for independent review**; it is folded into this record below. That review verified F4 and demonstrated
remaining F2/F3/F6 defects. Their corrective regressions now cover complete-message boundaries,
file-derived contexts, parser abbreviations, and recoverable child outcomes under redaction; see
`references/emission-boundary.md` and `tests/test_*emission*.py`. The correction is delivered for
independent re-review, not owner acceptance. R2's remaining findings (A3 scratch
retention, A4 platform refusal) and the wider release checklist stay separate work.

## The launch path, structurally

`scripts/evidence.py`'s main path is, in order:

1. **Two-phase admission (R2-F3).** The maskable values of *every* `--env` setting are collected from the
   raw arguments before any parsing or validation (`emission.collect`, using the parser's option table,
   including unique abbreviations and missing-operand errors), and the argument parser itself
   reports through that redaction context — so no usage line, parser error or admission refusal can show a
   declared value, not even one supplied in a later argument, and not even when it sits inside another
   argument's name (a duplicate name can spell an earlier value out). Only then are the settings validated
   (names only, never values), so from admission onward every diagnostic is redacted against the declared
   values — a refusal never shows one, even when it appears inside another argument such as a
   `--with-path` folder or the `--out` path (R1, F3).
2. `childenv.construct(args.with_path, args.env)` builds **one** environment mapping — the synthesized
   profile (plus the macOS pin), the validated `--with-path` folders (absolute, existing, real directories,
   never holding the PATH separator, so one folder enters PATH as exactly one entry — R1, F4), the admitted
   `--env` settings (a value of only whitespace and `=` is refused: it could not be masked — R1, F2) — and
   the run-owned scratch root, registered by identity (device and inode), not by path alone (R1, F1). The
   validated `--with-path` entries are **retained** with the mapping: validate once, then construct,
   analyze, launch and record from that same result — never re-resolve a mutable original argument after
   the run (R2-F4).
3. The supported-runner gate resolves the command's executable **under the launch's own working directory**
   (the check runs with `cwd=project`, so a relative path is judged where it will actually run), requires an
   existing executable file in the supported set, and validates it against this user's **enrollment
   registry** (`~/.vibe-to-engineering/runners.json` — A2, R2-F5): the resolved path must be the enrolled one
   and its bytes must hash to the enrolled SHA-256 — validation never executes the candidate. Enrollment is
   the only way a runner enters the registry: `--enroll-runner` discloses the resolved path, size and
   SHA-256, waits for the typed approval word, then runs the one profile probe — a real executable **binary**
   of the platform only (Mach-O on macOS, ELF on Linux), so a script under a runner's name is never even
   probed, and Node is held to the registry's version bounds (v20.7–v26.10). The launch uses the enrolled
   bytes: pin path only after proving the complete root-owned path chain (including ancestors and ACLs)
   again after approval and on every run, pin copy launched
   from a private copy of the hashed bytes — a replaced binary or retargeted link cannot substitute another
   program between validation and launch. A probe copy's own hash must equal the approved hash before it
   executes. Malformed registry encoding and non-integer schema versions also refuse cleanly. An unenrolled,
   moved, malformed or changed identity refuses
   **before execution** (exit 2), naming manual (re-)enrollment — never automatic. (R1's per-run probe was
   itself R2-F5: it executed untrusted candidates, and the launch was not pinned to the probed bytes. The
   probe now runs only at enrollment, disclosed and approved.)
4. The analysis reads that same mapping: `secret_values(project, env)` sees the constructed environment, the
   admitted `--env` names included (D4 rule 5). Declared values are sensitive from admission (D4 rule 4) and
   win attribution over a file value equal to them, so a check pointed at throwaway data prints the masked
   declared value. A recognized `.env` file is admitted only inside the v0.1 literal boundary (A1,
   `references/env-boundary.md` — superseding the stage-3 reader modeling and the R1-F7 computed readings):
   outside the grammar the run refuses before launch; inside it, every value is the single decode the claimed
   readers agree on, and nothing in the reading depends on the environment.
5. `subprocess.run(command, env=env, …)` launches the child with that same mapping — the D4 invariant: the
   final constructed environment is the single source of truth for both preflight analysis and launch, and no
   admitted entry is transformed between them.
6. The run's output is masked and emitted through the one governed path: every mask label is value-free
   when the name itself holds a masked value (a declared value inside another declared name falls back to a
   safe marker — R2-F2), and the final generated text — header, labels, the stderr summary — passes the
   redaction context once more before it is printed or saved. That context includes declared values and
   the recognized-file values already classified, with the existing short/numeric whole-word policy.
   Reconstructed values across mask edges are removed by a bounded, safe-symbol repair, and final
   newlines/prefixes are inside the checked text. The child's own result is retained immediately and recorded as data
   (`the check exited N`, or `terminated by signal N (NAME)` — never collapsed into an ordinary exit), and
   the wrapper's exit status is its own namespace (owner decision 5.3, R2-F6): **0** the check ran and the
   required evidence was produced — never "the check passed", a failed or signaled check's recorded outcome
   decides that; **1** a wrapper operational failure (the validated launch would not start, or the evidence
   could not be written); **2** a pre-launch refusal — nothing ran and no check evidence exists; **3** a
   post-launch integrity failure — the check ran. The final stderr line also records wrapper, launch,
   evidence-save and child facts in a recoverable form when literal outcome words/digits need masking;
   its format and caller checks are specified in `references/emission-boundary.md`. A missing or invalid
   record is unverified, never a passed check.
7. `childenv.retain(scratch)` runs in a `finally`, confirming the run's own scratch root still stands where
   the run made it and leaving it there — nothing is ever deleted (A3, the retained R2-F1 obligation): the
   object at the path must be the very folder the run made, matched by device and inode — a check can move
   its root away or put a foreign folder, link or file in its place, and retention will never touch it.
   The base chain is made once, at construction — each level a real directory owned by this user, never
   a link, mode 0700 whatever the umask, never inside the project — and retention only inspects it
   (lstat): a base that is missing, unreadable, a link, a non-directory or another user's is the same
   governed exit 3, never a traceback (A3 corrective, F1/F2). The recorded mode 0700 is re-asserted on
   the verified root and its home/ and tmp/ — the root is opened by descriptor
   (O_DIRECTORY|O_NOFOLLOW), identity matched with fstat and the mode set with fchmod, home/ and tmp/
   opened through it with dir_fd and matched against their registered identities (a foreign folder
   moved in is a stranger, skipped untouched — P2), a missing or non-directory one simply skipped, so
   no swap between
   check and chmod can touch a stranger and only a failure on the root itself is exit 3 (re-review
   N1/N2). The chain and the root are created the same way — levels through their parent's
   descriptor, the base descriptor held open, the root made with mkdir(dir_fd=) (P1) — and a root
   the check made unreadable is identity-confirmed by lstat, restored never through a link, and
   re-verified (P3). A
   retention that cannot confirm the root is an **integrity failure after the run: exit 3** (R1, F6) — the
   check ran and its outcome stands; exit 2 is reserved for refusals where nothing ran and no evidence
   exists. A confirmed root's path goes to the evidence header and the stderr summary: it may hold sensitive
   output, listing it is allowed, and deleting it is the human's own act.

The evidence header records the command line and the declared `--env` **names only** — never a declared
value (D4 rule 4) — plus the `--with-path` folders, the validated entries the child actually received
(R2-F4). A declared value is masked **wherever** the check prints
it — short, numeric, single-character, embedded in a longer word (R1, F2) — and no mask label, summary
field or diagnostic carries one (R2-F2, R2-F3).

## What the acceptance suite proves (`tests/test_stage1_acceptance.py`)

- **Paired adversarial runs** (`test_paired_runs_identical_child_environment_under_varied_hostile_parents`):
  the same check runs under four parent environments — a normal one, an empty one, one stuffed with
  proxy/`GIT_*`/`NODE_OPTIONS`-style variables, and a randomized hostile one carrying every prohibited
  channel and secret-shaped values — and the child's received environment is byte-identical across the runs:
  exactly the synthesized names (plus the macOS pin) and nothing the parent held. The hostile parent
  deliberately omits `DYLD_INSERT_LIBRARIES`, which would act on the *wrapper* before its own code runs —
  that is the D5 boundary made visible, not a gap in D4.
- **Prohibited-name admission** (`test_every_admission_attempt_is_refused_before_anything_runs`): 21
  attempts — each D3 group, case variants, malformed names, duplicates, synthesized-name overrides — all
  refused before any child runs.
- **Refusal means no launch** (`test_every_refusal_means_no_launch_and_no_evidence`): seven refusal kinds
  (an unreadable secret file, a `.env.vault`, an unsupported runner, a prohibited `--env` name, a duplicate,
  a synthesized-name override, a malformed name) each produce exit 2, no child process, and no evidence
  file. Post-launch integrity failures are exit 3 instead (R1, F6 — proven in `test_final_review_r1.py`).
- **Real readers** (`test_a_real_shell_reads_only_what_the_model_reads`,
  `test_a_real_node_keeps_the_constructed_value_and_the_declared_winner_is_masked`): a real `/bin/sh`
  (asserted bash 3.2) sources a `.env` inside the literal boundary and reads exactly the boundary's decode —
  the arithmetic/`${#NAME}`/`~` cases this test used to exercise are refused by the boundary now, asserted in
  the same test (A1 supersession) — and a real Node (asserted within the version-bounded loader profiles)
  reads a declared winner — the child's printed values match the model's readings, and the declared value
  appears only masked. The Node test is skipped as NOT
  VERIFIED without a local Node unless `V2E_REQUIRE_NODE=1` makes that a failure.
- **Seeded property runs** (seed 20260927, twelve draws each):
  `test_property_the_child_environment_never_depends_on_the_parent` (the child environment is invariant
  under randomized parents), `test_property_a_declared_value_never_appears_raw` (declared-value
  confidentiality — drawn from adversarial shapes, not one distribution: 1–3-character values, all-digit
  values, values with `=` or spaces inside, ordinary values, printed embedded in surrounding text — R1, F2),
  `test_property_no_simple_secret_file_value_ever_reaches_the_evidence` (random `.env` values are always
  masked).

The Slice-1–4, Windows-corrective and R1 test files carry the rest of the proof: `tests/test_childenv.py`
(construction, retention scoping, prohibited names, Windows case-folding and `SystemRoot`, structurally),
`tests/test_evidence_stage1.py` (the rewired launch path, the header, masked-declared-winner),
`tests/test_evidence_node.py` (the Node reader obligations — superseded by the boundary: refusals),
`tests/test_check_registry.py` (registry and gate agree), `tests/test_evidence_readings.py` (the retained
refusal regressions; the reader-model expectations are superseded by the boundary — the mapping is in
`references/env-boundary.md`), `tests/test_final_review_r1.py` (one regression test per R1
finding, each failing against the reviewed candidate: 20 failures + 1 error there, all passing after).

## Platform status

- **macOS** — verified. The full suite (179 tests) runs green on the development Mac (system Python 3.9.6,
  bash 3.2.57 as `/bin/sh`, Node v20.20.2). `__CF_USER_TEXT_ENCODING` is pinned in the constructed
  environment so the OS cannot inject it into the child after the analysis (owner decision at Gate 2).
- **Linux** — no pin required. The stage-1 cross-platform investigation found no channel by which a Linux
  child receives a variable absent from the constructed mapping. Structurally covered by the portable path;
  a native Linux suite run remains open as part of FIX-FIRST item 7. Note: the sh profile (checked at
  enrollment since A2) requires the runner to answer as bash 3.2 — the version the shell evidence is measured
  against — so a Linux box whose `/bin/sh` is dash refuses loudly rather than running under an unverified
  profile.
- **Windows** — **not claimed supported**. The corrective (case-folded name rules, OS-derived `SystemRoot`)
  is proven structurally only; `system_root()` has never executed on native Windows. The owner will run
  native verification separately, and any failure returns through a corrective gate. Recorded future
  requirements: case-insensitive collision/prohibition handling (done, structural), SystemRoot resolution
  (done, structural), and a native platform verification before any support claim.

## Real-reader evidence for every supported profile (R1, F8 — closed)

**Status note (2026-09-28):** the v0.1 literal `.env` boundary (A1, `references/env-boundary.md`) supersedes
the reader-model approach this section evidences — interpolation and environment-dependent readings are
refused outright now, and the live cross-reader proof for the claimed set is the in-suite differential matrix
(`tests/test_literal_matrix.py`). The entries below remain the record of R1-F8 for the reviewed candidate.

- **sh (bash 3.2 as `/bin/sh`)** — live: the reader-model tests source real `.env` files with `/bin/sh`
  under the constructed environment and compare against the model (`test_evidence_readings.py`,
  `test_stage1_acceptance.py`).
- **Node's own `.env` loader and npm dotenv v0.1.1–v18.0.4 keys** — live: the local Node v20.20.2
  (`test_evidence_readings.py`, round 9), within the version-bounded profiles.
- **npm dotenv v0.4–1.2 `$NAME` interpolation** — live (2026-09-27, throwaway: `/tmp/v2e-f8-oldnpm`): each
  release's own `lib/main.js` (0.4.0, 0.5.0, 0.5.1, 1.0.0, 1.1.0, 1.2.0, fetched from unpkg) run in Node
  v20.20.2 over eight interpolation cases (file-key resolution, environment fallback, chained keys, quoted
  values, empty-falls-through, unknown-is-empty, `\$` escape, whole-rest-is-the-name). 1.0.0–1.2.0
  interpolate inside `parse()`; 0.4.0–0.5.1 in `_processForPotentialEnvVariable` on the `load()` path —
  both driven exactly as the release's own code does. All six matched the model (`old_npm_interpolated`) on
  every case. Nothing vendored; the model and its tests carry the repeatable proof.
- **python-dotenv 1.2.3** — live (2026-09-27, throwaway: `/tmp/v2e-f8-pydotenv`, owner-authorized one-off
  fetch): the official 1.2.3 wheel run with the system Python over 21 checks — the per-value reading (quote
  forms, escape sets, `\x`/`\u`/octal-looking left as written, inline comments, right-stripping),
  interpolation from earlier lines then the environment (including inside single quotes, defaults,
  unknown-is-empty, the file winning over the environment for its own key), and `load_dotenv()` keeping the
  environment's value. All matched the model. Note: the wheel's metadata declares `requires-python >=3.10`;
  the pure-Python code imported and ran correctly on this Mac's 3.9.6 — the verification is recorded
  honestly, not generalized into a support claim about other machines.

## Known limitations

- The Windows behaviors above are structural, pending native verification.
- The runner gate trusts what the human enrolled: enrollment is **not** protection against an attacker who
  controls the user's account — such an attacker can rewrite the registry itself. Within that boundary the
  launched bytes always equal the enrolled bytes: pin path requires a fresh proof that the file and every
  ancestor are root-owned, have no group/other write bits or ACLs and are unwritable by the current user;
  otherwise pin copy is required at enrollment, or the runner refuses. The measured `/bin/sh` and Command
  Line Tools Python qualify; this Mac's admin-writable `/Applications` prevents Xcode Python path pinning.
  Native ACL metadata is verified on macOS only; other platforms require a working copy or refuse. Pin copy launches
  a private copy of the hashed bytes, so no replaced binary or retargeted link can reach the launch. An
  operator-approved binary that mimics a profile answer is an operator-chosen tool, outside the gate's
  boundary — the gate exists so that *unvalidated* runners never launch, not to authenticate
  operator-granted tools.
- Wrapper startup before child launch, and the check's own behavior after launch, are outside the NEW-5
  guarantee by design (D5); no sandbox is claimed.
