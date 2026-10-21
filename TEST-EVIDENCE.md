# Skill validation evidence

## Local repair validation — 2026-10-21

The `0.1.1-dev` repair candidate passed **378 native macOS tests** and **90 portable
checks**, with zero failures, errors or skips. The original snapshot passed 359
native tests; 19 regression methods were added. See [test-evedince.md](test-evedince.md)
for exact runs, counts, fixes, evidence paths and remaining release limits.
The portable methods are included in the full suite and must not be double-counted.

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

On a prepared macOS arm64 host with the exact reader versions and a Chrome-family browser:

```text
/Library/Developer/CommandLineTools/usr/bin/python3 -B tests/reader_matrix_prepare.py /path/to/readers
V2E_READER_MATRIX_DIR=/path/to/readers /Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos --output validation-results
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
