# Example tree — command-line tool

A CLI. The smallest project type in this set, and the best demonstration of the standard: most
CLI tools should end at stage 2 or 3 and never grow the rest. Snapshots of growth, **never a
template** — create only what is earned (§22).

## Stage 1 — day one

```
mytool/
  README.md               what it is, how to install and run it
  CHANGELOG.md
  .gitignore
  docs/scope.md           what it does, and what it will NOT do
  src/
    (the one command can BE the first file)
  tests/
```

## Stage 2 — more than one command

```
  src/
    commands/             earned by: commands need separate files — a one-file command
                          can stay directly under src/
  docs/architecture/boundaries.md   earned by: past the kit
  AGENTS.md               earned by: past the kit — how to run, test, build and ship
```

## Stage 3 — a command stops being one file

```
  src/
    core/ or application/ earned by: one command needs a separate owner for substantial product
                          logic, or commands share that logic — the commands stay thin (§8)
    infrastructure/       earned by: the first filesystem or network call with error handling
    output/               earned by: formatting is shared or substantial — one owner
                          for formatting; printing one value needs no folder
  config/ with an example file   earned by: the first setting — no real values (§49, §69);
                          a published binary never contains the project's key; each user
                          supplies their own key at run time
```

## Stage 4 — published

```
  scripts/release/        earned by: the first release command
  docs/deployment/        earned by: the first release — install and upgrade paths
  LICENSE                 earned by: distribution requires an explicit licence — the owner chooses
  CONTRIBUTING.md          earned by: a public contribution workflow needs it
  the CI folder           earned by: the first check that should run without being asked
```

What a CLI almost never earns: `domain/events/`, `apps/`, `packages/`, a state library, a
database. If the tool starts growing a server, that is a new deployable — see
[webapp.md](webapp.md) stage 3.
