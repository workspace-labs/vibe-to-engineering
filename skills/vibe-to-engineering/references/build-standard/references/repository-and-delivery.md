# Repository and delivery

A project's own rules on layout, evidence locations, ADR format and commit permissions take precedence over these defaults.

## Contents

- §15 Test architecture
- §16 Tooling is not testing
- §17 Source is not evidence
- §18 Git must tell the truth
- §19 Documentation is part of engineering
- §25 Dead code and dependency hygiene
- §26 Build and release reproducibility
- §27 Security and private data
- §36 Architecture Decision Records
- §37 Repository structure quality gate
- §47 External dependencies
- §48 Generated code and artifacts
- §55 Commit hygiene

## §15 Test architecture

Tests are part of the software architecture. They should be discoverable, organized, deterministic where practical, attributable to the subsystem they verify, and easy for another engineer to extend. Prefer test organization that mirrors real product responsibilities.

- Do not let one enormous regression script become a second implementation of the application.
- Do not copy test harnesses repeatedly; use shared helpers where the repetition is structural.
- Duplicating a production algorithm inside tests can provide useful independence, but an accidental second implementation creates maintenance risk. Choose deliberately.

## §16 Tooling is not testing

When the project is large enough for the distinction to matter, keep operational tooling separate from product tests. Tooling includes build, packaging, signing, capture, migration diagnostics, device inspection, deployment and release verification.

Critical recovery and operational tools must be discoverable. Never hide important operational tools permanently inside temporary evidence folders.

## §17 Source is not evidence

Keep the source repository focused on the product. Do not casually mix source with bulk archived builds, screenshots, videos, logs, private device snapshots, temporary backups, proof artifacts or test profiles.

Evidence may be stored separately and indexed by repository documentation. Small durable evidence directly useful to engineering may remain when justified. Private user or device data is never treated as ordinary source.

## §18 Git must tell the truth

Version control represents the real product source, and Git state is intentional.

Before risky restructuring:

- establish a trustworthy baseline;
- verify current behavior;
- make sure that baseline is committed (where committing needs the owner's approval, ask for it rather than skipping the step);
- create rollback points.

Do not perform major restructuring while significant product source exists only as untracked local files.

Never commit private keys, passwords, secrets, private user or device data, or unnecessary generated build bulk.

## §19 Documentation is part of engineering

A mature repository explains enough of itself that another engineer does not need old conversations to understand it. Depending on project complexity, documentation may include a README, architecture overview, module map, data model, persistence or storage contract, testing guide, platform runbooks, ADRs, known risks and debt, evidence policy and release procedure.

- The README is an entry point, not a development diary.
- The CHANGELOG holds release history.
- ADRs hold important architectural decisions.

Do not create large documentation sets for projects too small to need them.

## §25 Dead code and dependency hygiene

Do not let abandoned prototypes, template components, unused dependencies or obsolete scripts accumulate indefinitely — and do not delete them casually either. First establish:

- whether they are used;
- whether tests depend on them;
- whether they have historical or recovery value;
- whether removal changes output.

Remove dead material in a dedicated, reviewable change when appropriate.

## §26 Build and release reproducibility

A mature project is reconstructable from version-controlled source plus intentionally external secrets and dependencies. Build and release procedures must not depend on undocumented files that exist only on one machine. For each required external item, document what it is, why it is external, and how the build obtains it safely. Never put secrets into source merely to make a build self-contained.

## §27 Security and private data

Treat secrets and private data as architectural concerns. Never expose signing keys, passwords, tokens, API secrets, private user records or device snapshots through source control, logs, documentation or test fixtures. Use synthetic fixtures where possible. If real evidence must be retained, separate and classify it appropriately.

## §36 Architecture Decision Records

Use ADRs for important decisions that future engineers might otherwise question, such as persistence strategy, state architecture, platform architecture, major repository structure, signing or release identity, compatibility constraints, important algorithm choices, and intentional architectural limitations. Do not create ADRs for trivial implementation details.

An ADR explains the context, the decision, the alternatives considered where useful, the consequences, and its status.

Never silently rewrite an accepted ADR merely because a new implementation preference appears; a changed decision becomes a new ADR that supersedes the old one, through the Human Gate. Where the project defines its own ADR location, format or timing, follow it.

## §37 Repository structure quality gate

Before declaring a substantial project foundation healthy, verify that:

- the repository root is understandable;
- real product source is tracked;
- generated output is separated;
- private data is excluded;
- major subsystem locations are obvious;
- tests are discoverable;
- tools are discoverable;
- documentation points to the right locations;
- build inputs are represented;
- platform projects are represented;
- important external dependencies and secrets are documented safely.

Another competent engineer must be able to use the repository without relying on the original builder's memory.

## §47 External dependencies

Before adding a dependency, ask:

- What problem does it solve?
- Can the existing stack solve it adequately?
- Is it maintained?
- What architectural coupling does it introduce?
- What is its bundle or runtime cost?
- Does it affect security or licensing?
- How difficult is removal later?

Do not add libraries merely to avoid writing a small amount of straightforward code. Do not reimplement complex, security-sensitive or standardized functionality merely to avoid a justified dependency.

## §48 Generated code and artifacts

Clearly distinguish source from generated output. Generated artifacts should generally be reproducible; if generated files must be tracked, document why. Do not hand-edit generated files unless the toolchain explicitly requires it.

## §55 Commit hygiene

When Git commits are part of the workflow, prefer coherent commits with one clear intent. Avoid combining architecture restructuring, feature implementation, unrelated bug fixes, dependency cleanup and documentation rewrites in one large commit unless they are inseparable. A useful commit tells future engineers what changed and why.
