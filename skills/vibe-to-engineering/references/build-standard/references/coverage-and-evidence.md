# Project coverage and engineering evidence

Read applicable sections at a new project, a substantial change, or a change to stored
data, trust boundaries, distribution or an assurance claim. A tiny unrelated correction
keeps its narrow workflow. These rules extend existing responsibilities; they require
neither another document set nor every example folder.

## Contents

- [§87 Project coverage and approved documents](#87-project-coverage-and-approved-documents)
- [§88 Threat assessment and security failure evidence](#88-threat-assessment-and-security-failure-evidence)
- [§89 Recovery and compatible data changes](#89-recovery-and-compatible-data-changes)
- [§90 Distribution and assurance claims](#90-distribution-and-assurance-claims)

## §87 Project coverage and approved documents

**Due at:** a new project or substantial change; revisit when scope or risk changes.

Start with the actual repository and accepted requirements. When project-docs documents
exist, read the relevant approved PRD, TRD, DESIGN.md, Data, Security and Plan. Use current
choices and requirement IDs such as M1. Follow their approval, TBD and progress rules:
a draft or unresolved decision is not approval; historical text is not a second current
choice. Reuse prior approval of the same concrete decision (§30).

project-docs owns that planning information; this skill owns implementation and engineering
verification. Both work independently: without project-docs, use the project's accepted
requirements and plan. Do not start a new document interview, impose its filenames or
require its installation for a code task.

Before substantial building, account for these areas against the actual product:

- users, behavior, exclusions, platforms and material quality/operating constraints;
- module/dependency boundaries, public interfaces, state ownership and important decisions;
- persisted data, changes to it, recovery and concurrency;
- untrusted input, access, secrets, sensitive/personal data and external services;
- test levels, failure cases, dependencies, settings and automated checks;
- build, distribution, upgrades, support/operations and handover;
- contractual or explicitly adopted assurance obligations, only where applicable.

Use the existing plan, issue or a short checklist. For each selected responsibility, record
what makes it due, its implementation/document home, owner and observable check. One item
or check may cover several duties. Link checks to accepted requirement IDs where available;
include failing/rejected cases and conditions for quality targets. Mark unknown targets
rather than inventing numbers. Do not ask the owner to remember engineering artifact names
or choose ordinary safety controls.

At handoff every selected item has one honest disposition:

- **Verified:** actual artifact/operation, check result and evidence location.
- **Not applicable:** why its trigger is false for this product.
- **Unresolved or deferred:** missing proof/work, impact and the decision/access needed.

Unresolved work never counts as verified. Claim completion for approved scope only and
retain debt/exclusions (§57, §73). Revisit the record after new risks or requirements.
Do not create a fixed 91-item questionnaire or speculative empty directories.

Preserve canonical information: an approved PRD can own scope; a required scope.md can
point there. docs/api.md and docs/api/ may be equivalent homes; keep one. An ADR may cite
an already approved TRD choice instead of asking again. A locked choice changes through
its existing approval/history process. Where the Plan reserves checked status for the
owner, the builder records its actual run and waits for that check; tests alone never
authorize the owner's status.

## §88 Threat assessment and security failure evidence

**Due at:** a material untrusted-input, sensitive-data, plugin, account or external-use
boundary is introduced or changed. Reuse existing security/data notes (§27, §68, §80).

Name the assets and trust boundaries, plausible misuse or accidental loss, selected
responses and the owner of remaining risk. Explain what the system does, what could go
wrong, how it is addressed and how the response is checked. A small local tool may need
only a few sentences about its real untrusted files and data-loss risks. Do not invent
accounts, a named methodology or a large threat-model document for appearance.

Connect retained risks to actual failure checks using synthetic data/disposable profiles.
Reuse the approved Plan's checks, including its two-account checks. As applicable, verify:

- permitted and denied object/role/tenant operations through the trusted boundary;
  another person's data stays unchanged after denied reads, writes and deletes;
- bounded input before expensive parsing, invalid values/types and semantic rejection;
  rejected input cannot expose secrets or create unsafe log entries;
- a retried side effect happens once; conflicting reuse of a deduplication key is rejected
  when that mechanism is selected. Respect HTTP semantics; no draft header is mandatory;
- credential-cookie protection in actual responses and existing CSRF controls when used;
  consult current guidance for the chosen deployment context;
- sensitive fields stay protected across logs, exports and backups; newlines in untrusted
  log input cannot create fake events. Retention/deletion follow the selected policy.

A schema, hidden button, scanner score or document alone cannot prove every property.
Record outcomes and untested boundaries. Never probe a live third party, expose real
secrets or create a network surface solely to run a checker.

## §89 Recovery and compatible data changes

**Due at:** valuable persisted data or a supported stored-data change. Add operational
failure detection when recovery depends on scheduled backups (§43, §44, §82).

Identify the actual storage engine and its supported consistency requirements. Explain
what the backup includes, how it gets a consistent copy and which companion state must be
restored. A casual copy of live database files may be unusable. Do not generalize one
engine's commands to every store. Keep private backups outside version control.

Restore into a disposable destination. Inspect errors and exit status, then read meaningful
restored data or perform an application operation. A wrapper returning zero after an
inner failure, partial restore or the existence of a dump is insufficient. Try a failure
control so failed/unusable recovery cannot look successful. For relied-on scheduled
backups, prove the failure signal reaches the chosen operator.

Verify fresh construction and supported upgrades with representative synthetic old states,
the appropriate engine and repeat runs. A clean install alone does not prove an upgrade.
When versions coexist, retain compatible shapes during an expand/migrate/contract or
equivalent transition, and test old/new versions before retiring the old shape. An approved
stopped-system migration need not acquire rolling-deployment machinery.

Before release state the recovery path: preserved prior artifact/data, reversible migration
where supported, or an explicitly accepted alternative. Exercise promised upgrade/recovery
on a copy. Choose targets from product commitments; invent no universal backup frequency,
recovery time or retention period.

## §90 Distribution and assurance claims

**Due at:** a chosen technology/channel or explicit claim introduces the obligation.
Consult current authoritative guidance for that choice. Keep generic trees proportional.

- **Packages:** inspect packed contents and install/use the actual distribution in a clean
  consumer location. A Python package must not pass only through checkout imports. Agent
  Skills get metadata/resource checks, not an app scaffold. Follow selected ecosystem
  conventions such as dbt without imposing them on other project types.
- **Desktop/mobile/stores:** record channel and receiver. Check applicable signing,
  notarization, sandbox/entitlements, install/update identity, device-permission grant/denial,
  and store/SDK privacy submissions. A no-collection store app may still need a declaration.
  Read current channel rules; do not freeze disputed timelines here. Keep normal platform
  protections enabled. A test requirement authorizes no real submission or permission change.
- **Install/offline web promises:** exercise installation and offline lifecycle behavior
  in target browsers. A manifest alone does not prove offline operation.
- **Stronger assurance:** identify scope/version for an adopted security/accessibility
  standard, required component inventory (SBOM), build provenance or field-speed target.
  Verify its actual criteria. Scanner scores, lockfiles and lab metrics cannot prove a
  broader claim. Do not add telemetry or buy services merely to obtain proof.
- **Law/contracts:** establish use case, jurisdiction and authoritative requirements with
  appropriate expert review. Unknown/unread rules remain unresolved. This skill or a
  research checklist never establishes legal compliance.

Make release and workflow claims checkable (§26, §75, §78):

- Distinguish a repeatable working build from bit-identical reproducibility. Claim the
  latter only for declared conditions and selected artifacts with matching hashes.
- Tie published releases to source/artifact identities and preserve immutable published
  bytes. Unpublished repair candidates do not replace already published versions silently.
- Check required third-party notices/licenses in the actual distribution.
- Verify claimed branch/check/owner-review enforcement in actual settings or disclose
  unavailable access. Written policy does not enable a control; access changes still
  require the project's authority.
- Match support/deprecation and vulnerability-response commitments to real versions, a
  reachable owner and the chosen window. Exercise the proportionate incident path already
  planned in Security/operations. Invent no support duration or compulsory on-call rota.

When a needed platform, identity, service or current reference is unavailable, name the
unverified claim. Successful local checks cannot substitute for that evidence.
