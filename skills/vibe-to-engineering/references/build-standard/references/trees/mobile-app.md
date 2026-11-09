# Example tree — mobile application

A mobile app. Snapshots of one project as it grows — **never a template to scaffold**. Create
only what is earned (§22). The names below follow the layout map's mobile row; the mobile
framework's own settled structure wins over them (§61). The responsibilities are the rule.

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

## Stage 2 — screens and the first feature

```
  src/
    app/                  earned by: the first screen — where the app starts
    screens/              earned by: the second screen
    features/<feature>/   earned by: the first feature that owns more than one file
    assets/               earned by: the first image, icon or font
  docs/architecture/boundaries.md   earned by: past the kit — the one-home rule lives here
  a written design reference        earned by: the first screen
```

## Stage 3 — device capabilities and a backend

```
  src/
    services/             earned by: the first server call — ONE API client owning
                          addresses, headers and error handling
    state/                earned by: the first state two features share
    platform/             earned by: the first thing only this OS does — camera, push,
                          biometrics, permissions (§14). Shared product logic must not
                          import from here; the capability sits behind a boundary
    domain/               earned by: the first product rule — independent of screens and
                          of the OS (§8): testable without a device
  docs/security.md        earned by: the first stored data, sign-in, network call or secret — tokens on a
                          device are private data (§27); no project secret goes inside the
                          shipped app (§69). Private APIs are called through the project's
                          backend; a user's own token goes in the platform's secure storage
```

## Stage 4 — store release

```
  docs/operations/        earned by: the first build, sign, ship, release, backup or restore —
                          add signing identity and store steps when used
  docs/deployment/        earned by: the first release — install, staged rollout and rollback,
                          including store delivery when used
  docs/adr/               earned by: the signing-identity and minimum-OS decisions (§36) —
                          both are compatibility commitments (§44) through the Human Gate
  tests/e2e/              earned by: the first flow a person completes end to end, including
                          a simulator flow; real-device validation is added when the product's
                          interaction or performance requirements justify it (§45)
```

If the product later grows a desktop or web twin, shared rules move to `packages/domain/` on
the day the second app needs them — and `platform/` at the root is earned only when **two**
apps share that one concern, never earlier.
