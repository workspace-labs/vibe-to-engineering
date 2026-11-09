# Shared engineering standard

Use this reference in DIAGNOSE, DESIGN TARGET ARCHITECTURE and FINAL REVIEW.
The engineering standard defines appropriate placement and boundaries. Vibe supplies the
evidence, migration plan, human approvals, recovery checkpoints and behavior-preservation checks.

## Pinned source, available offline

This package carries engineering standard **1.4.0**, from
`workspace-labs/agent-engineering-standard` commit
`a27317b9f7885b18dc6b5eedc24b5dd29d27fdb9`.

- [Standard entrypoint](build-standard/standard.md) — the upstream instructions, preserved byte for byte
  under a different filename so this resource cannot be discovered as a second skill.
- [Layout map](build-standard/references/layout-map.md) — responsibility homes and the moment each is due.
- [Project-tree chooser](build-standard/references/trees/README.md) — eleven staged project families.
- [Source manifest](build-standard/source.json) — source paths and SHA-256 for every bundled document.
- [Upstream licence](build-standard/LICENSE).

Read the entrypoint, layout map and chooser. Then read the matching family tree(s), plus only the
conditional guides earned by the project's existing responsibilities. A desktop app, CLI,
website, webapp, API, mobile app, game, library, AI service, data pipeline and monorepo have
different shapes; do not manufacture a second deployable or turn examples into empty scaffolding.
An Agent Skill keeps its instruction-package layout, as the coverage guide explains.

The bundle is self-contained. Do not fetch a newer standard, install a sibling skill or choose
whichever installed copy happens to be newer. If the pinned resources are missing, inconsistent
with the manifest or unreadable, report the missing evidence and stop before designing a target.
Do not guess from memory or silently fall back to the old criteria alone.

## Apply the standard within migration scope

1. **Inspect first.** Identify the actual project type, framework, size, features and runtimes.
   Reuse its approved scope, architecture and decisions. Owner instructions and project-specific
   rules take precedence, followed by framework conventions; explain conflicts to the owner.
2. **Diagnose with evidence.** Use [C1–C16](engineering-standard.md) to establish structural
   harm and migration benefit. Cite the applicable upstream rule IDs (§) where relevant.
   The shared standard is the placement policy; C1–C16 decide whether migration is warranted.
3. **Map existing responsibilities.** For each proposed move or split, record the finding ID,
   target home, applicable due-at trigger and any accepted override. Preserve a healthy existing
   home. A tree mismatch alone is never a Material finding.
4. **Keep broader work separate.** Rules about security, reliability, services, accessibility,
   privacy, release or testing may expose real unmet duties. Report those plainly. They do not
   authorize new features, new services, changed dependencies, changed data, bug fixes or altered
   product behavior inside a structural migration. Keep structural corrections and the approved
   characterization safety net in the plan; let the owner decide other work separately.
5. **Use the same basis throughout.** The plan and ledger name version 1.4.0, the source commit,
   selected tree guides and project overrides. The final reviewer uses that approved basis,
   checks every changed responsibility against it and verifies the actual target tree.

Read the platform-services guide when existing jobs, realtime, storage, notifications, payments,
webhooks, search or other services need a structural home. Their existence earns the relevant
rules; an example folder is never a reason to add the capability. The data, frontend, backend,
lifecycle and coverage guides apply by the same due-at rule, within the migration boundary above.
This skill's stricter read-only planning, data protection and approval rules still govern execution.

## The plan is the owner's decision

The plan states what the agent will do: exact files and boundaries, intended target, phase order,
checks and pass criteria, protected files and recovery limits, risks and the documentation left
behind. Show the current tree and target tree in the PDF and explain the practical benefit.

After presenting the plan, end with `AWAITING HUMAN APPROVAL` and wait. Only explicit approval
of that presented version authorizes creating/verifying the recovery baseline and Phase 1.
Approving an inspection, asking for a plan, or saying "go" before the plan exists is not that
approval. A requested revision gets a new plan version and fingerprint and comes back for approval.
Each later phase and final review keeps its existing approval gate. Record approval in the ledger;
do not start checks or change code while merely waiting for the answer.

## Maintaining this bundle

Update the snapshot only as an explicit skill-maintenance change, never during a project migration.
Take the upstream standard entrypoint and its complete reference tree from one reviewed commit,
keep their bytes and relative links intact, include its licence, and regenerate `source.json`.
Update this router, package version, changelog and plan guidance together. Run the package and
portable checks and independent agent exercises; record what was actually observed.

A migration already approved under an older bundle keeps its recorded basis. If that bundle is
no longer available, stop and propose a revised plan for the new one. Never silently change the
criteria in the middle of an approved migration, and never describe tests of this instruction
update as approval or release of the whole migration runtime.
