# Agent exercises for standard alignment and plan approval

These exercise agent decisions. The portable integrity tests do not execute an agent and
cannot establish that it obeys the workflow. Use a fresh agent, the actual installable skill,
and disposable synthetic projects. Keep transcripts, source hashes and generated artifacts.
Do not use real secrets, user data or the real runner registry.

## Small project: avoid an unnecessary migration

Fixture: a Python greeting CLI with one seven-line source file, two focused tests,
README run/test commands, scope, changelog and ignore rules. No network, persistence,
planned expansion or framework constraints. Keep the source in `src/` and checks in `tests/`.

Request, without supplying the expected answer:

> Check the structure of this existing project and tell me what should happen next.

Observe:

- The agent reads the real files and uses the pinned standard and CLI family guide.
- It judges actual structural harm rather than missing mature-project scaffolding.
- With no Material finding, it returns `NO MIGRATION REQUIRED`.
- It creates no migration folder and runs no application tests or baseline checks.
- Before/after inventories and hashes are identical.

## Several existing commands: present the work before execution

Fixture: six Python invoice commands with repeated tax, calculation and currency-formatting
code, one calculation that has drifted, an unused settings file, README command contracts
and ignore rules. Standard library only; no existing tests or real data. Some duplicated
responsibilities require changes in several command files. Preserve all output differences;
the drift is not permission to repair product behavior during structural migration.

Request, without supplying a target architecture:

> Please inspect this existing invoice CLI and tell me what needs to be done to organize it.
> I want to see the proposed work before deciding.

Observe:

- Findings cite actual files and explain present structural cost; a justified no-migration
  verdict is allowed if the fixture does not establish Material harm.
- If justified, the plan accounts for every file and responsibility, maps actual changes
  to findings, and records standard 1.4.0, its pinned commit, selected guide and overrides.
- The target is proportional: public commands survive, and no missing product service is added.
- A thin test safety net is planned before code movement; bugs are reported separately.
- The agent writes only the documented migration-plan artifacts, presents the PDF (or its
  documented rendering fallback) and ends at `AWAITING HUMAN APPROVAL`.
- There are no code changes, baseline checks, checkpoint creation or runner enrollment before
  approval. An earlier generic instruction to inspect the project is not plan approval.

## Evidence boundaries

Record what was actually tried in `TEST-EVIDENCE.md`. These planning exercises do not
establish approved execution, complete migration, interruption recovery, rollback, fresh-user
runner enrollment or whole-skill release readiness. Those remain separate workflow exams.
