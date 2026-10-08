# vibe-to-engineering

An Agent Skill that inspects an existing software project, decides from evidence whether its structure shows signs of ad-hoc ("vibe-coded") development, and — only if restructuring is justified — moves it to an architecture designed for that project, through a migration the human approves one phase at a time.

```
INSPECT → DIAGNOSE → DESIGN TARGET ARCHITECTURE → CREATE MIGRATION PLAN → GENERATE PDF
→ HUMAN APPROVAL → CREATE + VERIFY BACKUP → PHASE 1 → TEST + VERIFY → CHECKPOINT
→ HUMAN APPROVAL → NEXT PHASE → … → FINAL REVIEW → ALL GREEN
```

## What it does

- **Reads before it judges.** Inspection and diagnosis are read-only: no builds, tests or scripts run, and nothing in the project is written.
- **Can say no.** Every finding cites evidence someone else can re-check. A project whose structure already fits gets `NO MIGRATION REQUIRED`, and nothing is written. It never imposes one folder tree on every project, and it treats more folders or more abstraction as a cost, not as engineering.
- **Plans before it touches anything.** A justified migration gets a current tree, a target tree designed for that project, every file of the project listed before → after (the ones it never touches included), phased steps and an `Engineering-Migration-Plan.pdf` that shows CURRENT → MIGRATION → TARGET on one page. Then it stops at `AWAITING HUMAN APPROVAL`.
- **Backs up by itself.** After approval, and before Phase 1, it saves the recovery contract's covered files, including uncommitted work in that set, and proves those files restore byte for byte. Ignored files and nested repositories are outside that saved set; checkpoints do not comprehensively back up local data or secrets. It refuses when it cannot account for the covered files or a nested repository has uncommitted work.
- **One phase per approval.** After each phase: checks compared with the baseline, the change compared with the plan, a new verified checkpoint, a report, and a stop.
- **Investigates failures instead of guessing.** A break stops the work, saves the broken state, compares it with the last known-good checkpoint and reports the root cause and the options. Stopping never rolls anything back; a restore needs the human's own approval and refuses, changing nothing, when it cannot be done safely.
- **Finishes with an independent review.** The approved target tree is compared with the actual final tree, and `VIBE-TO-ENGINEERING — ALL GREEN` is reported only when nothing blocking remains and every final check passes. Checks that were already failing when the human approved going ahead anyway are named in a separate completion status instead.

It never adds features, fixes bugs or changes dependencies, commits nothing unless asked, never pushes, and never touches files git ignores, secrets, data or nested repositories.

## Development status

A1 (the literal `.env` boundary) and A2 (per-user runner enrollment and protected launch) are accepted.
The R2 confidentiality/status slice (R2-F2/F3/F4/F6: no declared value in any emitted byte, confidentiality
before admission finishes, the recorded `--with-path` entries pinned to what the child received, and the
wrapper's own 0/1/2/3 status namespace with the check's outcome recorded as data) is implemented.
Independent review verified F2, F4 and F6; Kimi's final re-review verified the remaining F3-R1
ambiguous-attached-option correction, and the owner accepted F3-R1 on 2026-09-29.
Kimi reproduced all 307 tests passing, including the four required reader-matrix tests, on macOS arm64
with CLT Python 3.9.6. The current output and
caller result contract is in [emission-boundary.md](skills/vibe-to-engineering/references/emission-boundary.md).
This is not a released or generally approved skill. The current development changes implement A3
scratch retention and A4 macOS-only execution refusal; their native macOS regression, workflow and
release verification remain pending. The historical 307-test result above predates these changes.
Keep evaluation on disposable projects with synthetic secrets until the release gates are satisfied.
See `skills/vibe-to-engineering/references/env-boundary.md`.

**Latest update:** [LASTUPDATE.md](LASTUPDATE.md) records what is fixed, the review evidence,
and the remaining work in order. Historical delivery notes describe their status at the time;
use LASTUPDATE.md for current release status and the verification still required.

## Install

For development evaluation on disposable macOS projects only, the installable package is
`skills/vibe-to-engineering`, including its bundled license. Copy that folder into your agent's skills folder. Installation does not approve this development version for real-project use.

Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R skills/vibe-to-engineering ~/.claude/skills/
```

Codex:

```bash
mkdir -p ~/.agents/skills
cp -R skills/vibe-to-engineering ~/.agents/skills/
```

Other agents that read Agent Skills: copy the same folder into that agent's skills folder. To update, replace the whole folder.

## Use

Open your agent in the project you want checked and say:

```
/vibe-to-engineering
```

or `Use the vibe-to-engineering skill.` (in Codex, `$vibe-to-engineering`). The skill knows the whole protocol; invoke it again at any point and it picks up where the migration stands.

## What it writes in a project

Nothing during inspection and diagnosis, and nothing at all when no migration is needed. Otherwise, one folder that git never sees:

```
<project>/.vibe-to-engineering/
├── .gitignore                         the single line: *
├── Engineering-Migration-Plan.html    the plan
├── Engineering-Migration-Plan.pdf     what the human approves
├── ledger.md                          approvals, baseline, phases, failures, restores
├── evidence/                          check output (secret values masked), trees and diffs
└── checkpoints.git/                   the recovery store; the project's own repository is only read
```

Keeping or deleting this folder is the human's decision. Check execution also retains its private
run-owned scratch folder outside the project and records its location in the evidence and ledger.
Scratch may contain sensitive output; keeping or deleting it is the human's decision too.

## Requirements

- **Python 3.8 or newer**, standard library only, for the bundled runtime scripts. The validation suite and reader-matrix tooling require **Python 3.9 or newer**.
- **git** — checkpoints are git objects in their own store, for projects with or without git.
- **A Chrome-family browser** (Chrome, Chromium, Edge, Brave, or one downloaded by Playwright) to print the plan as a PDF. Without one, the plan stays readable as HTML.

The runtime installs nothing and does not fetch dependencies. Reader-matrix preparation is a
separate development step that may fetch its pinned artifacts; tests never download them.

## Platforms

Execution is restricted to **macOS** in this development version. Unsupported platforms refuse at
the command boundary before project access, tool writes or check execution. Python's own startup
precedes that boundary. This restriction is not a release-readiness claim.

| Platform | Current scope |
|---|---|
| macOS | Development execution target. The accepted September 29 regression evidence covers the earlier macOS arm64 snapshot; the current changes still need native regression and workflow exams. |
| Linux | Unsupported execution target. Portable package/unit and refusal checks do not establish Linux support. |
| Windows | Unsupported execution target. Portable package/unit and refusal checks do not establish Windows support. |

Linux and Windows support require their own implementations and native release exams. The pinned
reader matrix additionally requires **macOS arm64**, Bash 3.2 at `/bin/sh`, and local Node v20.20.2.
Preparation checks these prerequisites before writing or fetching anything.

## Tests

Portable validation on Windows, Linux or macOS (Python 3.9+):

```bash
python -B tests/run_validation.py --scope portable
```

This explicitly selected scope checks package metadata, pure logic and unsupported-platform refusal.
It does not enroll a real runner or run the full migration workflow. Run the native macOS regression
scope from a disposable checkout with the pinned readers and browser prepared:

```bash
V2E_REQUIRE_NODE=1 V2E_REQUIRE_MATRIX=1 /Library/Developer/CommandLineTools/usr/bin/python3 -B tests/run_validation.py --scope macos
```

The native scope must report its prerequisites and actual tests, failures and skips. Missing required
readers are failures. A partial or skipped run cannot replace the macOS release exam. The original
`python3 -B -m unittest discover -s tests -v` remains the complete suite command on a suitable macOS host;
its supported-platform execution expectations are intentionally not converted into Windows/Linux passes.

The evidence tests enroll the interpreter running the suite into an isolated HOME, so it must have a safe
pin mode. The reviewed macOS host used `/Library/Developer/CommandLineTools/usr/bin/python3 -B -m unittest discover -s tests -v`:
its resolved path has a protected ancestor chain. Xcode's Python under admin-writable `/Applications` does
not, and its framework executable cannot run as a relocated copy. That combination must refuse; do not
loosen the runner gate to make a test interpreter enroll.

`tests/test_a2_corrective.py` guards A2's independently found approval/copy race, replacement through a
higher ancestor or intermediate symlink, stale path-pin assumptions, and malformed registry encodings and
schema versions. It uses real compiled invocation markers, isolated registries and safe-run controls.

`tests/test_checkpoint.py`, `tests/test_nested.py`, `tests/test_watched.py` and `tests/test_tree.py` check every guarantee of the recovery contract on throwaway projects, under deliberately hostile git settings (`tests/support.py` holds the fixtures they share; to run one file, `python3 -m unittest discover -s tests -p test_nested.py -v` — discovery is what puts the shared fixtures on the path). Point `V2E_CHECKPOINT` at another implementation to test it against the same contract. `tests/test_render_pdf.py` checks the template and the PDF renderer; its render test is skipped when no browser is installed. `tests/test_evidence.py` checks that a check's output is kept with every secret value masked, and only inside the evidence folder; `tests/test_evidence_readings.py` checks that a value is masked whole as each program reading its format reads it — or that the run stops before the check when only that program can make the reading out (its `.env` reader-model expectations are superseded by the literal boundary below); `tests/test_env_literal.py` checks the v0.1 literal `.env` boundary itself — the grammar, the end-to-end admission/refusal contract, the brace regression and the combination tests against the real local readers; `tests/test_literal_matrix.py` re-proves the boundary differentially against every claimed reader (bash 3.2, six Node versions, npm dotenv 0.4.0–18.0.4, python-dotenv 1.2.3) from hash-verified artifacts prepared by `tests/reader_matrix_prepare.py`, and is skipped as NOT VERIFIED when they are not prepared — set `V2E_REQUIRE_MATRIX=1` to make that a failure instead. One readings test runs the local Node's own `.env` loader, and without Node it is skipped as NOT VERIFIED — set `V2E_REQUIRE_NODE=1` to make that a failure instead. `tests/test_childenv.py` checks the constructed check environment itself — the synthesized profile, retained run-owned scratch roots and tamper detection, `--with-path` validation, the prohibited names, and the Windows case-folding and `SystemRoot` rules (structurally; native Windows verification is pending). `tests/test_evidence_stage1.py` and `tests/test_evidence_node.py` check the launch path against that construction: declared names only in the header, never values; a declared winner masked rather than refused; `.env.vault` refused; an unsupported runner refused before it runs. `tests/test_check_registry.py` guards the supported-check registry and its revalidation gate. `tests/test_stage1_acceptance.py` is the stage-1 acceptance suite: paired adversarial runs under hostile parent environments, prohibited-name admission attempts, refusal-means-no-launch proofs, real `sh` and Node exercises, and seeded property runs (environment invariance, declared-value confidentiality, masking). `tests/test_final_review_r1.py` holds one regression test per finding of the stage-1 final review's R1 corrective, each failing against the reviewed candidate. `tests/test_final_review_r2.py` holds the R2 corrective's regressions — A2 runner identity (enrollment disclosure and approval, hash-only routine validation, the launched bytes pinned to the enrolled ones, swap and registry-tampering refusals) and the confidentiality/status slice (safe mask labels and the governed emission path, two-phase admission with redacted parser and refusal diagnostics, the recorded `--with-path` entries pinned to the child's, and the wrapper's 0/1/2/3 status namespace with the child's exit code or signal recorded as data); `tests/test_r2_confidentiality.py` adds the deterministic adversarial battery over generated `--env` name/value sets and orderings, plus the emission module's unit contract, and `tests/test_r2_status.py` the full status matrix (child exits and real signals, pre-launch refusals, spawn and evidence-write failures, post-launch failures never reported as refusals); the shared evidence fixture in `tests/enrolled.py` isolates both POSIX and Windows home variables and checks the registry path before enrolling the suite's runners; native regression runs also require an isolated process environment. `tests/test_protocol.py` guards the wording the protocol depends on in `SKILL.md`, its references and the plan template: gate transitions, completion outcomes, the full trees, the every-file table, the documentation phase, throwaway data and secrets.

`tests/test_emission_corrective.py`, `tests/test_r2_emission_corrective.py` and
`tests/test_emission_result.py` cover the F2/F3/F6 review counterexamples, full output boundaries,
parser grammar and recoverable results. The original confidentiality battery now checks complete output
and child outcomes without the former single-character/outcome exemptions.
`tests/test_f3_ambiguous.py` covers the remaining refusal leak (`--e=A=value` / `--en=A=value`),
its related input forms and preserved option/command-boundary controls.

`tests/test_reader_platform.py` checks the reader-matrix prerequisites without downloading artifacts.
`tests/test_platform_render.py` checks renderer refusal before plan access, browser lookup or writes;
`tests/test_enrolled_isolation.py` checks both home resolvers and the fixture's registry containment,
with enrollment mocked. These checks do not establish native macOS execution behavior.

## Repository layout

```
skills/vibe-to-engineering/
├── LICENSE                          MIT license included in the copied package
├── SKILL.md                         the protocol, its gates and status lines
├── agents/openai.yaml               display name and default prompt for Codex
├── references/
│   ├── engineering-standard.md      how a project's structure is judged
│   ├── migration-plan.md            target design, phases, verification, the plan document
│   ├── recovery.md                  the recovery contract, store format and platforms
│   ├── stage1-acceptance.md         the NEW-5 stage-1 acceptance evidence, for the independent review
│   ├── supported-checks.md          the checks revalidated to run, and the revalidation gate
│   ├── env-boundary.md              the literal .env boundary: admitted, refused, claimed readers, proof
│   └── emission-boundary.md         complete-output protection and recoverable wrapper/child results
├── scripts/
│   ├── platformgate.py              macOS execution boundary, before file access or writes
│   ├── checkpoint.py                the recovery tool (the command)
│   ├── gitrun.py                    runs git safely; the platform helpers
│   ├── nested.py                    nested repositories
│   ├── watched.py                   ignored files: watched, not saved
│   ├── treeview.py                  the tree view
│   ├── evidence.py                  runs a check and keeps its output, secrets masked
│   ├── emission.py                  protects assembled output and retains recoverable result facts
│   ├── childenv.py                  constructs the check's environment; the prohibited names
│   ├── envliteral.py                the literal .env boundary (which .env files reach a check at all)
│   ├── secretformats.py             reads each kind of secret file for evidence.py
│   ├── secretforms.py               every form a secret value may be printed in
│   ├── nodekeys.py                  the keys Node's .env loaders read (provenance record; not wired)
│   └── render_pdf.py                HTML plan → PDF
└── assets/plan-template.html        the plan's layout
tests/                               conformance, renderer and protocol tests
```

## Why a new skill

Before building, the open skills ecosystem was searched (2026-09-23, five queries, about 25 results). The closest skills each cover part of this job — phased refactoring, restructuring plans, cleanup of AI-generated code, audits — but none combines an evidence-based verdict that can say "no migration", a verified recovery baseline, one approved phase at a time with checkpoints, failure investigation against the last good checkpoint, and a final target-versus-actual review.

## License

MIT — see [LICENSE](LICENSE).

### Reproduce A1 verification

Prepare reader artifacts separately (recorded hashes; no dependency installation):

```bash
python3 -B tests/reader_matrix_prepare.py /tmp/v2e-readers-new
V2E_READER_MATRIX_DIR=/tmp/v2e-readers-new V2E_REQUIRE_MATRIX=1 python3 -B -m unittest discover -s tests -v
```

Choose a fresh preparation directory on macOS arm64. Preparation requires Bash 3.2 at `/bin/sh`,
local Node v20.20.2 on PATH, and the documented reader artifacts. Preparation may fetch a missing artifact; tests never fetch.
Existing extractions must match their archives exactly. Altered imports, redirected entries, changed
harnesses, crashes, malformed output and missing observations cannot count as successful coverage.
Boundary and matrix-integrity regressions also run without the downloaded matrix:
`python3 -B -m unittest discover -s tests -p 'test_a1_*regressions.py' -v`.
