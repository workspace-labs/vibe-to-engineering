# Example tree — desktop application

A desktop app (Electron-style shell or a native wrapper around shared product logic).
Snapshots of one project as it grows — **never a template to scaffold**. Create only what the
product has earned (§22). The `main/ preload/ renderer/` names below are the Electron
vocabulary; another shell names them differently, and its conventions win (§61). The
responsibilities — platform process, bridge, interface — are the rule.

## Stage 1 — day one

```
myapp/
  README.md
  CHANGELOG.md
  .gitignore
  docs/scope.md
  src/
  tests/
```

## Stage 2 — the first window

```
  src/
    main/                 earned by: the first desktop build — the platform process
    preload/              earned by: the first bridge between the shell and the interface
    renderer/             earned by: the interface itself
  docs/architecture/boundaries.md   earned by: past the kit — the one-home rule lives here
  the runtime version file          earned by: the first build or dependency
```

Shared product logic must not depend on the shell (§14): nothing in `renderer/` or a future
`domain/` imports from `main/` casually.

## Stage 3 — the app gets rules and storage of its own

```
  src/
    application/          earned by: the first operation with more than one step
    domain/               earned by: the first product rule — independent of the shell (§8)
    infrastructure/       earned by: the first file written or stored row
    platform/             earned by: the first thing only this operating system does (§14)
  data/backups/           earned by: the first real user data — and .gitignore carries it
                          from the same day; a backup never enters version control (§27)
  docs/security.md        earned by: the first stored data, sign-in, network call or secret —
                          no project secret goes inside the shipped app (§69). Private APIs
                          are called through the project's backend; a user's own token goes
                          in the platform's secure storage
```

## Stage 4 — signed and shipped

```
  scripts/release/        earned by: the first release command a person runs
  docs/operations/        earned by: the first build, sign, ship, release, backup or restore —
                          document each actual operation and verify restore when it arrives
  docs/deployment/        earned by: the first release
  docs/adr/               earned by: the signing-identity decision (§36) — it is a
                          compatibility commitment (§44), so it goes through the Human Gate
```

If the product later grows a mobile twin, the shared rules move to `packages/domain/` — on the
day the second app needs them, not before.
