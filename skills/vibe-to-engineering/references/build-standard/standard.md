---
name: software-engineering-build-standard
description: "Use when writing or changing code in a software project: adding or extending a feature or command, starting a new application or project, refactoring or reorganizing a repository, changing architecture, persistence, databases, data models, state or target platforms, organizing tests or tooling, reducing technical debt, or reviewing engineering quality. Sizes the work as tiny, substantial or architectural and builds in module and state ownership, dependency direction, data contracts, tests, documentation and Git hygiene from the start, without over-engineering; tiny fixes get no ceremony. Not for explanation-only questions or mechanical documentation or copy edits. Explicit task scope, project-specific instructions, accepted ADRs and owner decisions take precedence."
---

# Software Engineering Build Standard

Standard version: 1.4.0

Never build software first and organize it later. Architecture, repository structure, module ownership, dependency direction, testing, documentation, Git hygiene, maintainability and extensibility are part of implementation from the beginning. Working code with poor engineering structure is not complete.

Professional engineering is not maximum abstraction, excessive folders, unnecessary interfaces, premature frameworks or fashionable patterns. The architecture must be proportional to the actual product.

**Goal (§65):** the software works today, its structure explains itself, another engineer can safely change it tomorrow, and the architecture is no more complicated than the product actually requires.

Rule IDs §1–§104 are stable anchors for this standard; findings, plans and handoffs may cite them.

## Precedence (§61)

This standard is general. It does not replace, and it yields to:

- explicit task scope and explicit owner decisions, including the owner's standing instructions that apply across projects;
- repository-local instructions (for example AGENTS.md, CLAUDE.md, contributing, engineering, layout or design guides);
- accepted ADRs and accepted project-specific architecture;
- security requirements.

When a project has a more specific accepted rule — a mandated folder layout, file-size limit, finding format, approval step, commit policy or delivery format — follow the project rule. When a project rule appears unsafe or contradictory, report the conflict with evidence instead of silently overriding it. Commits, pushes and approvals follow the project's and owner's rules: where you may not commit yourself, ask for the baseline or rollback point rather than skipping it.

Narrower technique skills and guides (testing, incremental delivery, interface design, migrations, debugging) complement this standard rather than compete with it: this standard decides placement, boundaries, proportion and gates; they supply technique.

## Size the work before acting (§33–§35, §62–§63)

| Work | Examples | Required depth |
|---|---|---|
| Tiny | typo, small UI adjustment, small isolated bug, simple configuration change | Inspect enough to avoid damage, make the smallest coherent change, run the relevant verification. No audit, no architecture report, no new structure. |
| Substantial | new feature, extension of an existing subsystem | The matching workflow below at a depth that fits; design questions answered before building. |
| Architectural | new application or project, major subsystem, architecture change, database or persistence change, data-model or state-model change, large refactor, repository restructuring, platform expansion, high-frequency or historical data feature | The full workflow; no implementation until the design questions are answered and any Human Gate is passed. |

Project scale sets how much structure is right:

- **Small:** simple repository, few clear modules, lightweight tests, concise README, minimal tooling. Never manufacture enterprise architecture.
- **Medium:** clearer feature boundaries, domain or shared logic, a persistence boundary, organized tests and tools, documentation, platform separation where relevant.
- **Large or long-lived:** architecture documentation, explicit subsystem ownership, dependency direction, data contracts, migration strategy, test architecture, operational tooling, ADRs, release and recovery procedures.

Complexity follows product needs. A declared throwaway prototype or spike is a scope decision: keep it minimal and add no foundation work, but the secret and private-data rules still apply (§27). If a prototype starts becoming the product, say so and treat it as an existing project from then on.

Do not produce a ceremonial architecture report for a small, obvious task, and do not use planning to avoid implementation once the required decisions are resolved.

## Workflows

Substantial work follows this order, with planning proportional to the task (§1):

UNDERSTAND → DESIGN BOUNDARIES → DEFINE STRUCTURE → PLAN → REQUIRED DECISION GATE → IMPLEMENT → TEST → VERIFY → REVIEW → REQUIRED ACCEPTANCE GATE

Pass any required architecture decision gate before implementation. A later delivery or acceptance gate follows the project's workflow; it does not substitute for approval of the design.

### Before the first edit (§18)

In an existing Git project, record the starting point before changing any file: the base commit and the working-tree state, naming any changes that are not yours. For substantial or architectural work, also run the tests that cover the area and record the result, exactly as it ran; if they cannot run, record why. Tiny work records only the commit and working-tree state. This is the baseline the builder handoff reports later.

### Existing project (§2, §34, §58, §63)

Never assume its architecture, and do not start changing files until you understand enough of the real project: repository root, Git state, source layout, entry points, application composition, major features, domain rules, state ownership, persistence, platform-specific code, tests, tooling, documentation, dependencies, build and release path, and its own instructions and ADRs.

INSPECT → AUDIT IF NECESSARY → PLAN → HUMAN GATE IF ARCHITECTURAL → IMPLEMENT IN COHERENT SLICES → TEST → VERIFY → REVIEW

Determine the current architecture before proposing a target. Do not rebuild a functioning project because its structure is imperfect, and never reorganize blindly. Before a major feature, check whether the existing architecture can support it safely; if it cannot, do the minimum necessary foundation work first.

### New project (§3, §34, §63)

REQUIREMENTS → ARCHITECTURE → REPOSITORY FOUNDATION → DATA/STATE MODEL → TEST STRATEGY → IMPLEMENTATION

Before substantial feature development, decide: repository boundary, source structure, application composition, domain strategy, feature strategy, persistence boundary, platform boundaries, state ownership, dependency direction, testing strategy, tooling location, documentation location, generated-artifact policy and Git baseline. Decide where responsibilities belong before the project grows, but create only the minimum foundation the product needs — never dozens of speculative feature files, and no architecture a tiny project does not need. [references/layout-map.md](references/layout-map.md) carries the full layout and the moment each piece becomes due: start from the six pieces named there, and create only what the product has already earned.

For new projects, read [project coverage and approved documents (§87)](references/coverage-and-evidence.md#87-project-coverage-and-approved-documents) before feature implementation. Reuse approved planning instead of creating competing requirements.

### Engineering-quality audit or cleanup (§28)

Do not refactor immediately:

AUDIT → CURRENT ARCHITECTURE → FINDINGS → TARGET ARCHITECTURE → HUMAN GATE → INCREMENTAL MIGRATION → RECONCILE AND CLOSE (§73)

Distinguish actual correctness risk, structural debt, maintainability debt, cleanup and optional improvement. Report findings in the §29 format and never inflate severity to justify restructuring.

### Refactoring or restructuring (§20, §21, §54)

Prefer small coherent slices to a big-bang rewrite unless there is a compelling reason. Each slice has one objective, explicit scope, expected behavior change, risk, tests, a rollback point and acceptance criteria. Purely structural work carries ZERO intended behavior change (§54). After each significant slice: IMPLEMENT → VERIFY → REVIEW → HUMAN GATE, and never continue into the next slice automatically when the workflow requires approval. Move modules that are coherent, well tested, appropriately isolated and stable with minimal logic changes; architectural cleanup must never become a hidden product rewrite.

### Defect found in review (§53)

Do not immediately rewrite the surrounding architecture. First isolate the exact defect, its root cause, the affected contract, a reproduction, the required correction and the regression tests; then fix the smallest coherent scope that closes the defect. Record architecture work discovered during the fix separately unless it is necessary for correctness.

## Design questions before substantial building (§4, §34)

Derive the answers from the product, never from an arbitrary folder template:

- What responsibility is being introduced, and where should it live?
- Who owns its state, and who is allowed to depend on it?
- What external systems does it depend on?
- How will it be tested? How will it be persisted?
- What happens if it becomes much larger, and what future work is likely to extend it?

For architectural work, also establish: what exists now; what problem is being solved; which boundary owns it; what dependencies it introduces; what data and state change; the persistence implications; migration or compatibility risks; the rollback point; and whether a Human Gate is required.

## Always-on rules

- **Structure reflects responsibility (§5, §6).** Folders show real responsibility, never a popular template. A composition root wires systems together; it does not implement them.
- **No God files (§7).** Central files such as App, main, index, server, controller or manager must not become the default home of new behavior. Judge by responsibilities and change coupling, not size alone, and never split a cohesive file just to meet a line count.
- **Domain logic has a home (§8, §9, §10).** Product rules stay independent of UI, storage, platform wrappers and global clock access where practical; dependencies point toward stable product logic; each substantial feature has an obvious home; shared rules are not duplicated.
- **Boundaries are explicit (§11–§14, §39–§42, §49).** Persistence, platforms and configuration sit behind intentional boundaries; canonical data contracts, units and time models are defined; every important piece of state has an owner; failures are owned, not scattered as UI messages.
- **Backend and frontend behaviour (§66–§72).** For server work use [the backend guide](references/backend.md); for screens use [the frontend guide](references/frontend.md). Apply each rule only when its due-at trigger is met.
- **Team workflow and lifecycle (§74–§83).** Use [the team and lifecycle guide](references/team-and-lifecycle.md) for test levels, CI, review, ADRs, releases, environments, privacy, dependency health, incidents and ownership. Apply each part only when its due-at trigger is met; a solo or tiny project earns no team ceremony.
- **Platform services (§91–§104).** When the product earns a public address, sessions or tenants, background jobs, realtime, uploads, mail, payments, webhooks, search, an audit log, caching or a second running copy, infrastructure code, public pages or measurement, use [the platform services guide](references/platform-services.md). Each applies only at its due-at trigger; the stack's existing mechanism comes before a new service.
- **Teach and hand over (§84–§86).** [Teach while building](references/team-and-lifecycle.md#84-teach-while-building) in plain words when needed, with no lessons on tiny tasks; keep [handover documentation](references/team-and-lifecycle.md#85-the-ten-year-handover) current as its triggers are met, and [map an unfamiliar project](references/team-and-lifecycle.md#86-taking-over-a-project) before changing features when its map or settings list is missing.
- **Data model before time-based features (§12).** Before movement, telemetry, history, replay, collaboration, event streams, background automation or time-based simulation, verify the data model can carry identity, time, ordering and history.
- **Repository hygiene (§15–§19, §25–§27, §47, §48).** Tests are architecture, tooling is not testing, source is not evidence, Git tells the truth, documentation is part of engineering. Never commit or expose keys, passwords, secrets, tokens or private user or device data.
- **Do not over-engineer (§22).** Without a concrete product need, do not add interfaces for every class, repositories, services or managers for appearance, dependency-injection frameworks, global state libraries, empty future feature folders, dozens of tiny files, fashionable design patterns, microservices, event buses, databases or complex build systems. Every abstraction must solve a real problem of responsibility, dependency direction, testing, change isolation, platform isolation, maintainability or extensibility. Prefer the simplest architecture that remains structurally sound.
- **Realistic roadmap (§23, §58).** Test the architecture against the next realistic roadmap, not hypothetical infinite scale, and build no infrastructure for speculative features.
- **Repository over memory (§59).** Conversation context is not a substitute for repository engineering. Important project knowledge lives in source, tests, documentation, ADRs, Git history and explicit project plans, so the project stays understandable to an agent that never saw earlier conversations.

New projects, substantial work and material data/security/release changes use [coverage and engineering evidence (§87–§90)](references/coverage-and-evidence.md). Tiny unrelated corrections keep their narrow workflow.

## Human Gate (§30, §44)

Major architecture decisions belong to the human owner. Never silently decide to:

- replace the architecture;
- change the persistence strategy, data-model semantics or platform strategy;
- restructure the repository at scale;
- break the compatibility of released software (persisted data, public APIs, package or application identity, signing identity, file formats, configuration, user workflows);
- delete important historical or recovery material.

Instead: present the current state → explain the problem → propose the target → explain the trade-offs → explain the migration risk → wait for the Human Gate. Minor implementation choices inside an already approved architecture need no extra approval.

The owner's request for one of these changes is the assignment, not the gate. The gate is their answer after they have seen the current state, the problem, the proposed target, the trade-offs and the migration risk. Words such as "do the work" in that same request are not that answer. Do not create the replacement, the migration, or an ADR marked accepted before the answer. Introducing or materially changing a runtime, library or platform outside the accepted stack is its own decision and waits too. Reusing the accepted stack, including its standard library, needs no extra gate. An earlier approval of the same concrete design remains valid; ask again only when a material decision changes or the project's workflow requires it.

## Stop conditions (§56)

Stop and report instead of improvising when:

- required data is missing, or repository identity is uncertain;
- a migration behaves differently than predicted;
- signing or package identity differs from what was expected;
- private data may be at risk;
- tests reveal an unexplained regression;
- the architecture requires an unapproved major decision;
- a supposedly structural change requires a behavior change;
- evidence contradicts the task's assumptions.

Never "make it work" by destroying data or bypassing safeguards.

## Completion (§31, §32, §60, §64)

Working code alone is not done. Before declaring substantial work complete, explicitly verify the requested behavior, architectural placement, tests, build/type/lint status where relevant, Git state where relevant, documentation impact, known risks, and whether a Human Gate is required. Then apply the definition of done, the self-check and the handoff in [references/review-and-completion.md](references/review-and-completion.md), in proportion to the task. Report any concerning self-check answer with the smallest appropriate correction. Never claim completion for verification that was not performed — say what remains unverified.

Reconcile [project coverage and approved documents (§87)](references/coverage-and-evidence.md#87-project-coverage-and-approved-documents) against actual evidence before claiming substantial work complete. Preserve the project’s human-only approval and checked statuses.

When code starts reading or changes a configuration setting, load [the handover settings requirements (§85)](references/team-and-lifecycle.md#85-the-ten-year-handover). Compare the settings read by the code with `.env.example` and the README Settings section: each needs its name, purpose and where to obtain its value. A list of names and defaults alone does not explain how another person should configure the project.

When you are the builder and the work changed code or other project files, load the `engineering-builder-handoff` skill, if it is installed, before your final message; it sets the handoff's format. Do not load it for review-only or explanation-only work.

### Closing an audit or a restructuring (§73)

When work that began from an engineering audit (§28), or any substantial or architectural restructuring (§33–§35) — whatever it is called, however it began and however many slices it has — finishes or is stopped, including by the owner partway, reconcile it against the ORIGINAL audit, or the problems the restructuring set out to fix, not only the approved slices, and record the result where the project keeps its plan or debt register (§59):

    ENGINEERING CLOSURE
    Approved scope:      <slices> — complete / not complete
    Original findings:   <n> resolved · <n> partly resolved · <n> deferred · <n> accepted as debt · <n> rejected · <n> still open
    Target architecture: approved / partly decided / not decided
    Remaining debt:      each item that blocks or affects planned work — why it remains, impact, the
                         work it blocks, what reopens it (§57); the rest counted, with a pointer to the register
    Status:              STOPPED — APPROVED SCOPE INCOMPLETE — <what is unfinished>, or
                         APPROVED SCOPE COMPLETE — <what is not complete>, or a broad status (below)

- `APPROVED SCOPE COMPLETE` is allowed only when the approved scope's own completion criteria are met. When they are not — for example when the owner stops the work partway through what was approved — the status is `STOPPED — APPROVED SCOPE INCOMPLETE`, naming what is unfinished.
- A status that names the work's goal — foundation, restructuring, reorganization or engineering "complete" or "healthy" — or says "no findings remain" is allowed only when nothing is partly resolved, deferred, accepted as debt or still open and the target architecture is approved. Narrowing or renaming the phase to match the approved slices does not change this.
- A count of findings names its set: "no open findings in the approved slices" is not "no open findings in the audit".
- Rejected means the finding itself was wrong or does not apply, with the reason. A real problem the owner accepts permanently is accepted as debt: it stays in the remaining debt and is never presented as solved (§57), and declining a proposed fix never rejects the problem it was meant to fix. Every later copy of the closure — handoff, plan, README, changelog or notes — carries the same status.

## References — load only what the task needs

| File | Load when the work involves |
|---|---|
| [references/coverage-and-evidence.md](references/coverage-and-evidence.md) | new/substantial project coverage, approved-document handoff, changed trust/data boundaries, recovery, release channels and stronger assurance claims |
| [references/layout-map.md](references/layout-map.md) | creating a project or adding a part to one, and deciding where a folder or a file belongs: the full layout, and when each piece becomes due |
| [references/trees/README.md](references/trees/README.md) | starting a project of any known type: the chooser table and staged example trees (website, webapp, API backend, desktop, mobile, game, CLI, library, AI service, data pipeline, monorepo) showing what each type earns, stage by stage — examples, never templates |
| [references/architecture-and-boundaries.md](references/architecture-and-boundaries.md) | where code lives, feature or module boundaries, God-file risk, dependency direction, platform wrappers, change coupling, configuration, naming, comments |
| [references/data-state-and-runtime.md](references/data-state-and-runtime.md) | persistence or databases, data contracts, units, time, state ownership, migrations, compatibility, error handling, async or concurrency, performance |
| [references/backend.md](references/backend.md) | API contracts and errors, reliability and operations, backend security, secrets and API keys, containers — each at its due-at trigger |
| [references/frontend.md](references/frontend.md) | server data and screen state, remote-data views, forms, accessibility, frontend security, performance and languages — each at its due-at trigger |
| [references/platform-services.md](references/platform-services.md) | HTTPS and domains, sessions and tenants, background jobs and schedules, realtime, uploads and files, email, payments, webhooks, search, audit logs, caching and scaling, infrastructure as code, public pages and SEO, analytics and error tracking — each at its due-at trigger |
| [references/team-and-lifecycle.md](references/team-and-lifecycle.md) | test levels and CI gates, branches and review, ADR lifecycle, releases, environments and flags, privacy, dependency health, incidents, code ownership, teaching, handover documentation, adding or changing configuration settings, or taking over an unfamiliar project — each at its due-at trigger |
| [references/repository-and-delivery.md](references/repository-and-delivery.md) | tests, tooling, evidence and artifacts, Git and commits, documentation, ADRs, dependencies, generated files, build and release, secrets and private data, dead code |
| [references/review-and-completion.md](references/review-and-completion.md) | findings, reviews, zero-behavior-change refactors, technical debt, definition of done, self-check, handoff |
