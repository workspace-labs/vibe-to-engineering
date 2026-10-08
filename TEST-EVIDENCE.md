# Skill validation evidence — 2026-10-08

Repository: workspace-labs/vibe-to-engineering. Baseline: `014e97909f1976993217bb13877e38c9f678b433`.
Review branch: `fix/platform-boundary-review`.

## Scope and verdict

The skill remains in development with macOS-only execution. Windows and Linux checks
establish safe refusal and selected portable behavior; they do not establish support
for running migrations on those systems. A complete agent workflow exam and owner
release approval remain outstanding.

## Original Windows result

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

## Corrections and focused proof

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

## Reproducible validation

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

## Results and remaining gates

Portable validation of commit `39d07f557d528c4e1bada5ab5951684b76c3a2cf`:

| Host | Python | Tests | Failures / errors / skips | Result |
|---|---|---:|---|---|
| This PC: Windows 11, AMD64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |
| GitHub Windows Server 2025, AMD64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |
| GitHub Linux, x86_64 | 3.12.15 | 84 | 0 / 0 / 0 | PASS |
| GitHub macOS 26.6.2, arm64 | 3.12.10 | 84 | 0 / 0 / 0 | PASS |

[CI run and downloadable portable logs/summaries](https://github.com/workspace-labs/vibe-to-engineering/actions/runs/37767517413).
The macOS native regression is still being verified separately. The first portable macOS
run exposed a simulated-Windows import failure; the test now simulates Linux on macOS,
while Windows/Linux hosts still exercise their actual platform. No test was skipped.

The historical September 29 macOS result of 307 passing tests belongs to the baseline
and is not reused as current evidence.
Workflow migrations, no-migration behavior, interruption/resume, approved restore/retry,
baseline failures, data-safety checks, fresh-user validation and final release review
remain required under the existing release checklist in `LASTUPDATE.md`.
