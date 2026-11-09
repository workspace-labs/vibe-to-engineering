# Architecture and boundaries

Structure is derived from the product, never from a template. The shapes below are concepts, not required folders, and a project's own accepted layout takes precedence.

## Contents

- §5 The repository communicates the architecture
- §6 Separation of concerns
- §7 Prevent God files
- §8 Domain logic must have a home
- §9 Dependency direction
- §10 Feature ownership
- §14 Platform boundaries
- §23 Future change test
- §24 Change coupling check
- §38 Module boundary quality gate
- §49 Configuration ownership
- §50 Naming
- §51 Comments and code clarity

## §5 The repository communicates the architecture

A competent engineer opening the repository should quickly find where each of these lives:

- application composition;
- domain and business rules;
- major features;
- shared UI;
- persistence;
- platform-specific adapters;
- tests;
- tooling;
- documentation;
- generated artifacts;
- evidence and backups, if relevant.

Folder structure reflects actual responsibility. Do not create folders merely because a popular template contains them.

## §6 Separation of concerns

Avoid modules that own unrelated responsibilities. Important boundaries commonly include application composition, domain or business logic, UI rendering, feature-specific interaction, persistence, networking, platform integration, configuration, testing and operational tooling.

A composition root may wire many systems together. It must not become the implementation of every system it wires.

## §7 Prevent God files

Central files such as App, main, index, server, controller or manager must not become the default destination for every new behavior. File size alone is not the deciding rule. The real warning signs are:

- unrelated responsibilities;
- many independent state groups;
- repeated business rules;
- high change coupling;
- many unrelated side effects;
- feature-specific handlers accumulating centrally;
- unrelated features repeatedly requiring edits to the same file;
- important product state existing only as scattered local variables.

When these appear, establish a real boundary before adding more responsibility. Asked to add another major feature to such a file, first inspect its responsibilities and coupling; when a boundary is clearly needed, put the new behavior behind it instead of growing the file, and take any restructuring beyond that feature through the Human Gate.

Do not split a cohesive file merely to satisfy an arbitrary line-count target.

## §8 Domain logic must have a home

Important product concepts exist independently of UI implementation where practical. Domain and business logic should preferably be explicit, testable, deterministic where appropriate, and independent from rendering, storage implementation and platform wrappers.

Domain modules should not casually depend on UI frameworks, DOM or browser APIs, desktop or mobile wrappers, database implementations, or global wall-clock access. Pass external concerns — clock, storage, environment, platform services, network clients — through explicit boundaries where useful.

## §9 Dependency direction

Dependencies generally point toward stable product logic rather than outward infrastructure. A conceptual direction may resemble:

- platform → application → features → domain
- persistence implementation → persistence contract / domain types

The exact structure depends on the product. Avoid accidental directions: domain → UI, domain → platform, domain → database implementation, shared logic → desktop wrapper, shared logic → mobile wrapper. A genuinely appropriate exception must be intentional and understandable.

## §10 Feature ownership

A substantial feature has an obvious architectural home. Feature-specific elements may live together: components, interaction logic, local state, feature-specific hooks, field definitions, feature tests.

Rules used across features are not duplicated for convenience; genuinely shared product rules move to an appropriate shared or domain boundary. Avoid casual cross-feature dependency chains.

## §14 Platform boundaries

Keep shared product logic independent from platform wrappers where practical. A project may conceptually contain a shared product plus desktop, mobile or web wrappers. Platform-specific concerns stay isolated instead of leaking through the entire application. Do not create wrappers the product does not need when the application targets only one platform.

## §23 Future change test

Before accepting an architecture, test it mentally against likely future work:

- If another engineer adds the next planned feature tomorrow, where does it go?
- Can they find the correct module?
- Can they find its tests?
- Can they understand the data model?
- Can they change one feature without understanding the entire application?
- Can a backend or platform implementation change without rewriting unrelated product code?

If the answers are unclear, investigate whether the architecture needs a stronger boundary. Judge against the next realistic roadmap, not hypothetical infinite scale (§58).

## §24 Change coupling check

Watch for changes where one conceptual field or behavior requires edits across many unrelated locations. When it happens, ask whether:

- the product aggregate is missing;
- a contract is duplicated;
- validation is duplicated;
- UI and domain state are fused;
- tests have copied implementation details;
- the persistence shape is leaking.

Do not abstract automatically. First identify the actual source of the coupling.

## §38 Module boundary quality gate

For each major module or subsystem, ask:

- What responsibility does it own?
- What public contract does it expose?
- Which implementation details should remain private?
- Who depends on it?
- What does it depend on?
- Can it be tested independently?
- Can it change without causing unrelated changes?

If ownership cannot be explained clearly, investigate whether the boundary is wrong or missing.

## §49 Configuration ownership

Configuration has an obvious owner. Avoid duplicated configuration, magic values spread across unrelated modules, and environment-specific behavior hidden in product logic. Separate where appropriate: product constants, environment configuration, user preferences, secrets, build configuration.

## §50 Naming

Names communicate responsibility: prefer names based on what a module owns or does. Avoid vague dumping-ground names such as utils, helpers, misc, common or manager when a more specific responsibility exists; they are acceptable only when the contents are genuinely cohesive under that concept. Do not rename stable code merely for cosmetic preference.

## §51 Comments and code clarity

Prefer code whose structure explains itself. Comments explain why, invariants, non-obvious constraints, compatibility requirements and safety decisions. Avoid comments that merely restate the next line of code, and do not keep comments that a behavior change made obsolete.
