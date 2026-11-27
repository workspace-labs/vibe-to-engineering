# Team workflow and project lifecycle

Apply each responsibility only when its **due at** trigger is met (§22). A solo or tiny
project does not earn team ceremony by existing. Accepted project workflows — AGENTS.md,
CONTRIBUTING, branch policy, ADR format and release process — take precedence (§61).

## Contents

- §74 Test levels
- §75 CI quality gates
- §76 Branches, pull requests and code review
- §77 ADR format and lifecycle
- §78 Releasing a project
- §79 Environments and feature flags
- §80 Privacy and the data lifecycle
- §81 Dependency health over time
- §82 Incidents
- §83 Code ownership
- [§84 Teach while building](#84-teach-while-building)
- [§85 The ten-year handover](#85-the-ten-year-handover)
- [§86 Taking over a project](#86-taking-over-a-project)

## §74 Test levels

**Due at:** the first behavior that needs verification; use the existing
[test folders and their triggers](layout-map.md#tests), not a new scaffold (§15).

- Unit tests prove one rule or function in isolation. Integration tests prove two real
  parts together, such as code and a real database. Contract tests prove an interface both
  sides own (§39). End-to-end tests prove one flow a person completes.
- Put most checks at the fastest level that proves the behavior. Use end-to-end checks for
  critical user journeys and consequential failure paths that need the whole system to prove.
- A flaky test is a defect: find its cause or quarantine it with an owner and a note.
  Never hide it with automatic retries or silently delete it. Quarantine that weakens a
  gate needs the owner's recorded decision under §75.
- Coverage is a signal, not a target; never add assertion-free tests to raise it. Use
  synthetic test data (§27).

## §75 CI quality gates

**Due at:** the first check that should run without being asked — the existing CI trigger.

- CI runs the same commands developers run locally, documented in README/AGENTS.md:
  format check, lint, type check where the language has one, tests and build, as applicable
  to the project. Add the secret scan (§69) and dependency audit (§68) when each is due.
- Apply the [speed target check (§45)](data-state-and-runtime.md#45-performance-without-premature-optimization)
  when due, using its conditions for a blocking CI check or release verification.
- Main stays green: merge a change only when its gates pass. Never weaken a gate to get
  green by deleting tests, skipping checks, adding blanket suppressions or lowering a
  threshold without the owner's explicit decision, recorded in the change.

## §76 Branches, pull requests and code review

**Due at:** the second person or agent changing the same repository, or the owner asking
for review before merge. A solo project keeps §55 commit hygiene; PRs are optional.

- Use short-lived branches from main with one intent per pull request, small enough to
  review in one sitting; preserve truthful Git state and coherent commits (§18, §55).
- A PR description says what changed and why, how it was tested with commands and
  results, risks, rollback and any Human Gate needed.
- The author reviews their own diff first; the reviewer applies §52. Nobody merges a PR
  with failing gates (§75). Protect main where the platform allows.

## §77 ADR format and lifecycle

**Due at:** an important decision earns an ADR under §36; its timing stays there.

- Use the project's own ADR format when one exists. Otherwise use
  `docs/adr/NNNN-short-title.md`, numbered in order, never reusing a number.
- Sections: Status, Date, Context, Decision, Alternatives considered, Consequences.
- Status values: Proposed, Accepted, Rejected, Deprecated, Superseded by NNNN. An agent
  writes Proposed; it becomes Accepted only after the owner's answer at the Human Gate
  (§30). A proposal may instead be Rejected; an accepted decision may later be Deprecated
  or Superseded.
- Never edit an Accepted ADR to change its decision: a new ADR supersedes it, and the old
  one names its successor (§36).
- **`docs/adr/README.md` is due at the second ADR:** an index of number, title and status.

## §78 Releasing a project

Apply the selected [distribution and assurance checks (§90)](coverage-and-evidence.md#90-distribution-and-assurance-claims); disclose missing receiver/platform proof.

**Due at:** the first release someone else installs, deploys or depends on.

- Use semantic versioning for things others depend on: libraries, APIs, CLIs and skills.
  An app may use the version scheme its platform or owner requires.
- Every release bumps the version once, has a dated CHANGELOG entry (§19), a tag and
  release notes for users, and is built reproducibly (§26), ideally from CI.
- Before release, write down the signal that triggers recovery, who decides and how to recover.
  Record whether rollback is safe, to which version and under what conditions. Record a time
  window where it helps and any cutoff, such as an irreversible migration or writes the earlier
  version cannot read (§43, §44). Record whether each data migration can be reversed.
  A timer alone cannot decide whether rollback is safe. Check compatibility both inside and
  after any time window.
- Rehearse the recovery route for the release channel and its saved data. Use the channel's
  supported route, such as stopping a staged rollout or shipping a recovery update if a
  downgrade would put data at risk. Follow the [data recovery checks (§89)](coverage-and-evidence.md#89-recovery-and-compatible-data-changes)
  and the distribution checks above (§90). Automated rollback needs a preapproved trigger
  and a tested safe path.
- Publishing is the owner's action unless the project grants that authority.

## §79 Environments and feature flags

**Due at:** the first environment actually used; flags have their separate trigger below.

- Keep only environments that exist: development, test, staging, production. Each has its
  own configuration (§49) and keys (§69); `config/<environment>/` follows the
  [existing settings trigger](layout-map.md#settings-commands-tools-published-files), not an earlier split.
- Keep environments as similar as practical. Production data never goes to development
  or test environments; use synthetic data (§27).
- **A feature flag is due at the first unfinished feature that must merge to main, or the
  first staged rollout.** Every flag has an owner and a removal condition; remove it after
  full rollout (§25). Never use flags as permanent configuration.

## §80 Privacy and the data lifecycle

**Due at:** the first personal data stored or processed — names, email, phone, IDs,
location, device identifiers or anything that identifies a person.

- Keep a data inventory in `docs/privacy.md`: what is collected, why, where it is stored,
  who can access it, how long it is kept and how it is deleted.
- Collect the minimum. Every stored category has a retention period and a working deletion
  path, including backups where practical. Log access by people when the data is sensitive,
  without exposing the personal records in those logs (§27).
- Laws differ by country; UAE PDPL and EU GDPR are examples. Name likely obligations for
  the owner, but never claim the product is legally compliant: that decision belongs to
  the owner and their legal adviser.

## §81 Dependency health over time

**Due at:** the first deployed or published release; extends §25 and §47.

- Lockfiles stay authoritative. Use an automated update tool or a scheduled review to
  keep dependencies current. Triage vulnerability alerts by severity; fix them or record
  them as accepted debt (§57).
- A major-version dependency upgrade is its own change with its tests run, never mixed
  into a feature (§55).
- When deprecating an API, option or feature, announce it, give a migration path and a
  timeline, and keep it working until the next major version. Removal still needs the
  deliberate, documented approval required by §44; a version number is not permission.

## §82 Incidents

**Due at:** the first deployment someone depends on. A runbook in `docs/operations/`
says how to check health, roll back and restore.
After an incident, write a short blameless review: what happened, impact, cause, fix and
prevention. Add a regression test for the cause, following the
[existing test folders and triggers](layout-map.md#tests).

## §83 Code ownership

**Due at:** different people or teams own different parts of the repository.
Use CODEOWNERS or the platform's equivalent to record that ownership.
CONTRIBUTING keeps its [existing layout-map trigger](layout-map.md#root-files-and-documentation).

## §84 Teach while building

**Due at:** the person says they are new, asks a basic question, or asks for something unsafe
without seeming to know the risk; or the owner or project asks for explanations.

- On a new project, say in plain words which project type was chosen from the
  [tree chooser](trees/README.md) and why. Explain what each day-one file or folder is for,
  one short line each. Create only what the [layout map](layout-map.md#day-one) says is due (§22).
- When making an important decision about a secret, personal data, storage, structure,
  a Human Gate or refusing an unsafe request, explain in one or two plain sentences what
  was done and why. Define any technical word the first time, or avoid it.
- Safety first: an unsafe request gets the safe build and the explanation, never the unsafe
  build because the person asked for it (for example, §69). Required decision gates still apply (§30).
- At the end, give a short **What I set up and why** list in plain words.
- Keep it proportional: no lessons on tiny tasks; a typo fix gets no explanation. Never
  lecture or repeat the same explanation in one session. Explanations never replace doing the work.

## §85 The ten-year handover

**Due at:** the first README on day one; grow each part below only when its trigger is met.

- Day one: explain what the project is and how to run it in numbered steps.
- Past the kit: add a **Project map**, one line each for where the frontend, backend,
  database/migrations, tests and docs live; include only parts that exist.
- The first setting earns a **Settings** section. List each setting's name, purpose and
  where its value comes from. Point to the configuration sources the code actually uses.
- The first deployment: explain how to build and deploy, and where the project runs.
- The first stored data: explain where the data and its backups live (§43).
- Point to `CHANGELOG.md` for what changed and `docs/adr/` for why important decisions were
  made (§19, §36), once decision records are earned; do not create an empty ADR folder.
- Keep the settings list and any required examples current in the same change. Use
  `.env.example` for environment variables, with names and safe placeholders. For file-based
  settings, give a usable example in the project's format, such as `settings.example.toml`
  for a TOML reader, and explain how to use it. Document flags and managed settings where
  the operator supplies them. Keep real secrets and private values out of all examples (§69).
- Before calling substantial work done, apply the ten-year test: could a stranger holding
  only the repository, with no chat or original builder, find the frontend and backend that
  exist, run it, know every setting it needs and see why big decisions were made? If not,
  fix the documentation first (§59, §65).

## §86 Taking over a project

**Due at:** taking over feature development or maintenance in an unfamiliar project that lacks a map or settings list. A tiny isolated correction follows the narrow workflow (§33).

- Map it before changing features. From what the code actually does, write or repair the
  README **Project map** and numbered how-to-run steps, and `docs/architecture/overview.md`
  when the [layout map](layout-map.md#root-files-and-documentation) makes it due.
  Never describe what you have not read.
- If settings are undocumented, search the code for what it reads and apply §85 to those
  sources. Mark unknown values. Never invent or guess a secret value or copy one from
  logs, history or other machines into a file. Ask the owner to supply the real values
  through the project's secure configuration mechanism. Keep secrets out of handoff notes,
  example files and logs. Follow §19 before adding new documentation to a shared repository.
- If history is missing, start `CHANGELOG.md` from today and put what is unknown or broken
  in `docs/risks-and-debt.md` (§57). Never invent the past.
- A wrong project tree is a finding (§28, §29), not a reason to rebuild. Report it, then
  move to the right structure in small slices through the Human Gate (§20, §30).
