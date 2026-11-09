# Example tree — monorepo (several apps, one repository)

One repository holding multiple deployable apps plus any code they actually share. Start
here when the current approved scope already requires multiple deployables; otherwise a
project grows into this shape when it earns a second one. A standalone app keeps plain
`src/`, and future optional apps earn no folders. Snapshots of growth, not a template (§22).

## When this tree is earned

When the current scope requires a second deployable — a web app plus its API, an app plus
its mobile twin, a product plus its admin tool. Both may be needed from the first release;
there is no requirement to build one in the wrong layout and move it later. For an existing
single app, the move into `apps/` is one coherent slice (§20) with zero intended behavior
change (§54), through any required Human Gate.

## Stage 1 — the second deployable arrives

```
myproduct/
  README.md
  CHANGELOG.md
  .gitignore
  docs/scope.md
  apps/
    web/src/, web/tests/        one app per folder — moved as-is if it already exists
    api/src/, api/tests/        earned by: the required second deployable in current scope
  docs/architecture/boundaries.md   the one-home rule, now critical: WHERE shared code
                                    lives is decided once and written here
  docs/architecture/overview.md     earned by: two parts that talk to each other
```

## Stage 2 — the first thing two apps share

Each of these is earned by the **second app that needs that exact thing** — before that, the
code lives in the app's own folders, and that is correct, not a finding.

```
  packages/
    contracts/            earned by: the first type two apps both import
    domain/               earned by: product rules two apps share (§8)
    ui/                   earned by: the first component two apps share
    validation/           earned by: the second app checking the same shapes
  tests/contract/         earned by: the first interface both sides of the repo own (§39)
  docs/api/               earned by: the first endpoint another app calls
```

`packages/` is product code apps import. It is not a dumping ground: a package exists because
two apps import it today, not because something *might* be shared someday.

## Stage 3 — the machinery beneath the apps

```
  platform/
    persistence/          earned by: TWO apps sharing that one concern — until then it
    logging/                  lives in each app's own infrastructure/ (§11)
    authentication/
    telemetry/
  apps/worker/              earned by: the first background work that cannot run inside the
                            server's own process (§93)
  infra/                    earned by: the first cloud resource someone would have to
                            recreate by hand — per environment that exists (§102)
  scripts/build/, release/    earned by: the first command a person runs per job
  tooling/architecture-checks/  earned by: the first boundary worth guarding automatically —
                              the check that dependencies still point inward (§9)
  tests/architecture/       earned by: same moment
  docs/adr/                 earned by: the repository-structure decision itself (§36)
  docs/operations/          earned by: the first build, sign, ship, release, backup or restore
  docs/risks-and-debt.md    earned by: the first known problem or deliberate shortcut (§57)
```

`packages/` against `platform/`: if it carries product rules, it is a package; `platform/` is
the machinery beneath them.

## What a monorepo must never do

- Never create `apps/` with one child, or `packages/` with nothing two apps import today.
- Never let app A import app B's internals — sharing goes through a package, decided in
  `boundaries.md`.
- Never treat different runtimes' lockfiles as competing resolutions of one dependency
  graph. Follow each package manager's workspace rules and document who owns each graph.
- Never split one product into several repositories or several apps without the Human Gate —
  repository boundary is an architectural decision (§30).
