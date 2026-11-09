# Example tree — game

A game, with or without a dedicated engine. These are selected additions as one game grows,
**never a template to scaffold** (§22). The engine's accepted source, scene and asset layout
wins (§61); the names below describe responsibilities, not a choice of engine or dependency.
A tiny playable game can stay small. Choose only the pieces the approved gameplay earns.

## Stage 1 — day one

```
mygame/
  README.md               what it is, how to run and play it
  CHANGELOG.md
  .gitignore              excludes generated imports, caches, builds and live save data
  docs/scope.md           the playable scope, target devices and acceptance checks
  src/                    the first playable loop; use the engine's accepted source location
  tests/
```

One small loop can stay in one file. Do not add an empty `src/` beside the engine's own
source location. Keep authored source and assets, required engine metadata and their licences
under version control; generated imports, caches and export builds are reproducible output,
not automatically source (§26, §48).

## Stage 2 — the first playable feature earns separate responsibilities

```
  src/
    runtime/              earned by: substantial startup, input or update-loop wiring that
                          needs its own owner; use the engine's lifecycle when it provides one
    gameplay/             earned by: product rules that need separation from rendering or input,
                          testable without launching the full game where practical (§8)
    assets/               earned by: the first authored image, sound or font — engine paths win
  docs/architecture/boundaries.md   earned by: past the kit — runtime, rules and asset ownership
  a written design reference        earned by: the first screen
  a credits file          earned by: the first borrowed asset or font, with its licence
```

The engine owns engine state; product state has an explicit owner (§13). A rendering or input
callback calls the gameplay boundary rather than duplicating rules across scenes.

## Stage 3 — scenes or saved progress

```
  src/
    scenes/               earned by: distinct scenes or levels that need separate homes
    infrastructure/       earned by: saving progress or calling an outside service — storage
                          and network details stay behind a boundary (§11)
  docs/architecture/save-data.md   earned by: persisted progress — its owner, shape, version,
                                  write location and failure behavior (§12, §43)
  docs/security.md        earned by: the first stored data, sign-in, network call or secret
  tests/integration/      earned by: the first two parts that must work together, such as save/load
  tests/fixtures/         earned by: the first synthetic level or save needed by a test
```

Live saves and backups do not enter version control (§27). Version the save contract and
migration code, not the player's files; retain only synthetic save fixtures. A shipped save
format change earns migration and compatibility checks before existing saves are touched (§43, §44).

## Stage 4 — measured and released

```
  tests/e2e/              earned by: the first complete player flow, such as start → play → finish
  tests/performance/      earned by: a stated frame-time, input-latency or memory requirement (§45)
  scripts/release/        earned by: the first release command a person runs
  docs/operations/        earned by: the first build, sign, ship, backup or restore
  docs/deployment/        earned by: the first release — export targets, install and upgrade paths
  LICENSE                 earned by: distribution requires an explicit licence — the owner chooses
```

Measure on representative target hardware when the acceptance criteria require it. Multiplayer
servers, accounts, downloadable content and shared packages arrive only when the approved
product needs them; use the relevant server or multi-app tree for those responsibilities.
