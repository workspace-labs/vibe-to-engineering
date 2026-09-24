# RA-02 — leave a record of the structural decisions inside the project

## What is missing

The skill reads a project's ADRs and architecture notes (they outrank its standard, `SKILL.md:89`), but it never writes one. Every reason behind the new structure lives only in `.vibe-to-engineering/`: the plan's "Key decisions" table (each decision, why, and the simpler alternative rejected) and the ledger. That folder ignores itself in git, and at the end the owner is told that keeping or deleting it is their decision (`SKILL.md:240`).

Once it's deleted, or on any other clone, the project has no record of *why* it is shaped the way it is. The next developer or AI agent can put the duplicates straight back, and the final review has nothing in the project to check against.

The migration plan's phase order already ends with "updating documentation that describes the structure" (`references/migration-plan.md:33`). But that only *updates* documentation that already exists. A project with none, which is typical for vibe-coded projects, ends the migration with none.

## How it showed up

Project `spendly`: it has no `docs/`, ADR, CONTRIBUTING, AGENTS.md, CLAUDE.md or architecture notes, only a README with run instructions. Plan v1 decided:

- `db.py` is the only module that talks to SQLite (finding F1);
- `config.py` holds the only budget table (F2);
- the layout stays flat, and a `src/` + `web/` + `domain/` + `data/` split was rejected as overengineering for about 540 lines (C16).

Nothing in the plan puts any of this into the project. After the migration and deleting `.vibe-to-engineering/`, the only trace would be the diff.

## Where

- `SKILL.md:89` → `- the project's own rules and decisions (README, CONTRIBUTING, architecture notes, ADRs, AGENTS.md, CLAUDE.md). They outrank this skill's standard.`
- `SKILL.md:222` → the final review checks `documentation that describes the structure matches it`, but only if such documentation exists.
- `SKILL.md:240` → `… keeping or deleting it is their decision.`
- `references/migration-plan.md:33` → `- **Typical order:** … → updating documentation that describes the structure.`
- `assets/plan-template.html`: the phases section has no documentation phase.

## Added means

1. Every migration plan ends with a **documentation phase**: the last phase, before the final review, and approved like any other. It writes a short record into the project, in the form the project already uses:
   - if the project has ADRs, one new ADR in its folder, in its format;
   - if it has architecture notes or a CONTRIBUTING file, a section there;
   - if it has neither, a **"Project layout"** section in the README (one line per top-level folder or file: its job), plus a few bullet lines for the key decisions, each with the alternative rejected. It creates `docs/adr/` only if the owner asks for ADRs. For a small project a README section is the proportionate form (C16).
2. The record holds no migration history (phases, checkpoints, dates of runs). It describes the structure as it now is and why. This matches the existing rule against "migration notes left in code".
3. The plan shows the exact text of the record, so the owner approves the words, not just "a doc will be added".
4. The final review checks the record against the final tree: every folder it names exists and holds what it says. A mismatch is a finding.
5. The owner can decline the phase at the plan gate ("no docs"). The ledger records that, and the final report says there is no record in the project.
6. Tests in `test_protocol.py` check:
   - that `SKILL.md`, `migration-plan.md` and the template require the documentation phase;
   - that it can be declined;
   - that the final review covers it.

## Ideas (not tried)

- The plan's "Key decisions" table already has the right columns (decision · why · simpler alternative rejected). The record can be generated from it, which keeps one source of truth.
- A one-line pointer at the top of the record ("structure decided on <date>; see the decisions below") helps a later run of the skill: INSPECT will find it as a documented decision, which the standard says is never a finding by itself.
