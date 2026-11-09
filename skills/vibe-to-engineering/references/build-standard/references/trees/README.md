# The trees — which one are you building?

Staged example trees per project type. Each shows one project as it grows, stage by stage,
with the moment every piece is earned. **They are examples of the *due at* rule, never
templates to scaffold** (§22). A project that stops at stage 1 is finished, not unfinished.
A framework's or existing repository's own settled structure always wins (§61).

The code blocks show selected additions or changes, not a complete scaffold. The layout
map's *due at* rule still applies to every stage: a security, operations, test or ADR artifact
is due when its trigger happens, even if illustrated in a later section. Keep standalone
source in `src/`; use `apps/<name>/src/` when the current scope requires multiple deployables.

## Choose by what the product IS, not by what it might become

| If the product is… | Start here |
|---|---|
| pages people read — marketing site, blog, docs site | [website.md](website.md) |
| an interactive app in the browser, with or without its own server | [webapp.md](webapp.md) |
| a server other programs call — no UI of its own | [api-backend.md](api-backend.md) |
| a program for the desktop, shell-wrapped or native | [desktop-app.md](desktop-app.md) |
| a phone or tablet app | [mobile-app.md](mobile-app.md) |
| a game, with or without a dedicated engine | [game.md](game.md) |
| a command a person runs in a terminal | [cli-tool.md](cli-tool.md) |
| code other projects import as a dependency | [library.md](library.md) |
| a product whose core features call a model | [ai-service.md](ai-service.md) |
| jobs that move and transform data on a schedule | [data-pipeline.md](data-pipeline.md) |
| several deployable apps sharing code, one repository | [monorepo.md](monorepo.md) |

One product can outgrow its tree: a website that grows a server moves to webapp; a library
that grows an executable adds a CLI app; a single app that gains a sibling moves to monorepo.
The move happens when the current scope requires the second deployable, in one coherent
slice (§20) — never for a speculative future. If both are required at the start, begin with
the monorepo tree.

## What every mature project eventually earns

Whichever tree applies, a long-lived project grows these on the day each becomes true:

| Piece | Due at |
|---|---|
| `docs/adr/` | the first decision a future engineer would question (§36) |
| `docs/risks-and-debt.md` | the first known problem or deliberate shortcut (§57) |
| `docs/operations/` | the first build, sign, ship, backup or restore |
| `docs/security.md` | the first stored data, sign-in, network call or secret (§27) |
| `docs/privacy.md` | the first personal data stored or processed (§80) |
| `tests/architecture/` | the first boundary worth guarding automatically (§9) |
| `tests/regression/` | the first defect that came back |
| `tests/fixtures/` | the first test needing data — synthetic, never real user data (§27) |
| `data/migrations/` | the first change to a data shape that has shipped (§43) |
| the CI folder | the first check that should run without being asked |
| `infra/` | the first cloud resource someone would have to recreate by hand (§102) |
| `scripts/`, `tooling/` | the first command a person runs; the first check that runs by itself |

None of these is created as an empty placeholder. Each arrives the day it is true, and the
CHANGELOG, README and `docs/architecture/boundaries.md` stay truthful the whole way (§18, §19).
