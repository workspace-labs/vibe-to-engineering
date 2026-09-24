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
- **Plans before it touches anything.** A justified migration gets a current tree, a target tree designed for that project, phased steps and an `Engineering-Migration-Plan.pdf` that shows CURRENT → MIGRATION → TARGET on one page. Then it stops at `AWAITING HUMAN APPROVAL`.
- **Backs up by itself.** After approval, and before Phase 1, it saves the whole project — uncommitted work included — as a recovery baseline and proves the baseline restores byte for byte. It refuses to start when it cannot save everything, for example a folder it cannot read or a nested repository with uncommitted work.
- **One phase per approval.** After each phase: checks compared with the baseline, the change compared with the plan, a new verified checkpoint, a report, and a stop.
- **Investigates failures instead of guessing.** A break stops the work, saves the broken state, compares it with the last known-good checkpoint and reports the root cause and the options. Stopping never rolls anything back; a restore needs the human's own approval and refuses, changing nothing, when it cannot be done safely.
- **Finishes with an independent review.** The approved target tree is compared with the actual final tree, and `VIBE-TO-ENGINEERING — ALL GREEN` is reported only when nothing blocking remains and every final check passes. Checks that were already failing when the human approved going ahead anyway are named in a separate completion status instead.

It never adds features, fixes bugs or changes dependencies, commits nothing unless asked, never pushes, and never touches files git ignores, secrets, data or nested repositories.

## Install

The skill is the folder `skills/vibe-to-engineering`. Copy it into your agent's skills folder.

Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R skills/vibe-to-engineering ~/.claude/skills/
```

Codex:

```bash
mkdir -p ~/.codex/skills
cp -R skills/vibe-to-engineering ~/.codex/skills/
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
├── evidence/                          raw check output, trees and diffs
└── checkpoints.git/                   the recovery store; the project's own repository is only read
```

When the migration is finished, keeping or deleting this folder is the human's decision. It can hold raw command output, so it is kept out of git on purpose.

## Requirements

- **Python 3.8 or newer**, standard library only, for the two bundled scripts.
- **git** — checkpoints are git objects in their own store, for projects with or without git.
- **A Chrome-family browser** (Chrome, Chromium, Edge, Brave, or one downloaded by Playwright) to print the plan as a PDF. Without one, the plan stays readable as HTML.

Nothing is installed and nothing uses the network.

## Platforms

The recovery protocol is platform-independent: a written contract (`references/recovery.md`) and a store format any implementation can share. The bundled implementation is one Python file that calls git without a shell, with its few operating-system differences kept in one section.

| Platform | Status in 0.1.0 |
|---|---|
| macOS | Validated: all tests pass (Python 3.9, git 2.54, Chromium headless shell). |
| Linux | Expected to work unchanged; not yet validated. |
| Windows | Designed for (`py -3`, Git for Windows); not yet validated. Known differences are listed in `references/recovery.md`. |

To validate a platform, run the tests on it.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_checkpoint.py` checks every guarantee of the recovery contract on throwaway projects, under deliberately hostile git settings. Point `V2E_CHECKPOINT` at another implementation to test it against the same contract. `tests/test_render_pdf.py` checks the template and the PDF renderer; its render test is skipped when no browser is installed. `tests/test_protocol.py` guards the wording of the protocol's gate transitions and completion outcomes in `SKILL.md`.

## Repository layout

```
skills/vibe-to-engineering/
├── SKILL.md                         the protocol, its gates and status lines
├── agents/openai.yaml               display name and default prompt for Codex
├── references/
│   ├── engineering-standard.md      how a project's structure is judged
│   ├── migration-plan.md            target design, phases, verification, the plan document
│   └── recovery.md                  the recovery contract, store format and platforms
├── scripts/
│   ├── checkpoint.py                the recovery tool
│   └── render_pdf.py                HTML plan → PDF
└── assets/plan-template.html        the plan's layout
tests/                               conformance, renderer and protocol tests
```

## Why a new skill

Before building, the open skills ecosystem was searched (2026-09-23, five queries, about 25 results). The closest skills each cover part of this job — phased refactoring, restructuring plans, cleanup of AI-generated code, audits — but none combines an evidence-based verdict that can say "no migration", a verified recovery baseline, one approved phase at a time with checkpoints, failure investigation against the last good checkpoint, and a final target-versus-actual review.

## License

MIT — see [LICENSE](LICENSE).
