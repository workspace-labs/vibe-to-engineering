# The layout map

A map of where things live in a software project, and **when each piece becomes due**. It is a
map, never a template: a project is never created with these folders empty and waiting. It grows
into the shape it earns, and a small tool that never leaves the first section is finished, not
unfinished (§5, §6, §22).

## Contents

- Know the project first
- Day one
- The one rule that makes the map usable
- Root files and documentation
- Inside one app: frontend · backend · desktop, mobile, command line
- More than one app
- Data · the AI part · tests · settings, commands and tools
- What this never does

Worked examples per project type live in [trees/](trees/) — start at `trees/README.md` for the
chooser table: staged snapshots of the *due at* rule in action, never templates to scaffold.

## Know the project first

Nothing here is decided before the project is understood (§2, §3, §33–§35):

1. **What is it?** New or already existing. What kind — a website, a server, a desktop or mobile
   application, a command-line tool, a library, a game. Who uses it, and how large it has to be.
   For an existing project, read the real repository and never assume its architecture.
2. **What must it do, and what must it not do?** The scope, written down.
3. **Which pieces does that earn today?** Only those are created.
4. **Build.** Every later change adds the one folder it has just earned.

A one-page tool earns the first section and nothing else. A system with a website, a server and a
database earns `apps/`, `data/migrations/` and `tests/contract/` on the day each one exists.

## Day one

A new project starts with six pieces, and only these:

```
project-name/
  README.md        what it is, how to run it — grows a project map and a settings list as the project grows (§85)
  CHANGELOG.md     what changed in each version
  .gitignore       keeps build output, environment files and secrets out of the repository
  docs/scope.md    what it does, what it will NOT do, and how good it must be
  src/             the code
  tests/           the checks
```

These are the starting responsibilities for a standalone app. A framework's accepted
source location wins (§61); when the current approved scope already requires multiple
deployables, their source lives in `apps/<name>/src/` from day one. Do not add an empty root
`src/` beside them. A throwaway prototype follows its declared minimal scope (§62).

**Past the kit** means the project holds more than these six and one first file: a second source
file, a dependency, or anything to install, run, build, test or ship.

## The one rule that makes the map usable

**A feature has exactly one home, chosen once for the project and written down in
`docs/architecture/boundaries.md`.**

This map offers three legitimate homes for the same feature — inside the app
(`src/features/<feature>/`), shared at the root (`features/<feature>/`), or published
(`packages/`). All three are defensible; choosing a different one each time is not. Decide once,
record it, and every later feature follows it. The same applies to the machinery that can also
live in two places — authentication, persistence, logging, validation, configuration: one home
each, named in that same file (§5, §6, §11).

## Root files and documentation

| Piece | Due at |
|---|---|
| the six pieces above | day one |
| `AGENTS.md` (how to run, test, build and ship it, for the coding agents that work on it) | past the kit |
| `LICENSE` | distribution requires an explicit licence; the owner chooses it, and a private local tool need not choose one just to grow past the kit |
| `.gitattributes`, `.editorconfig` | the project needs recorded line-ending, file-treatment or shared editing conventions |
| the language or runtime version file (`.nvmrc` or its equivalent) | the first build or dependency |
| the lockfile(s) required by the package manager(s) | the first managed dependency set — one authoritative resolution per dependency graph; separate runtimes or independently managed apps may need separate lockfiles |
| a linter and a formatter | the project's checks or shared editing needs justify them; reuse existing tooling, and never install tools solely because a tiny project grew past the kit |
| `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue templates | a public repository's contribution or reporting workflow actually needs them |
| a pull-request template | the second person or agent changing the same repository, or the owner asking for review before merge (§76) |
| `CODEOWNERS` (or the platform's location) | different people or teams own different parts of the repository (§83) |
| a written design or style reference | the first screen |
| a credits file for fonts and borrowed code, with each licence | the first font or borrowed code |
| `docs/roadmap.md` | the second planned piece of work |
| `docs/architecture/overview.md` | the second part that talks to another |
| `docs/architecture/boundaries.md` | past the kit — the one-home rule above lives here |
| `docs/architecture/dependencies.md` | the first dependency direction worth writing down |
| `docs/adr/` | the first real decision (§36, §77) |
| `docs/adr/README.md` (index) | the second ADR (§77) |
| `docs/api/` | the first endpoint something else calls |
| `docs/features/` | the first feature a newcomer would have to ask about |
| `docs/deployment/` | the first release — and where the domain, DNS and certificate ownership are recorded (§91) |
| `docs/operations/` | the first time it is built, signed, shipped or released — and where backup and restore live |
| `docs/security.md` | the first stored data, sign-in, network call or secret |
| `docs/privacy.md` | the first personal data stored or processed (§80) |
| `docs/glossary.md` | the first technical word a reader of the documentation would have to look up |
| `docs/risks-and-debt.md` | the first known problem or deliberate shortcut |
| `infra/` | the first cloud resource someone would have to recreate by hand after it is lost — one folder per environment that exists (§102) |

## Inside one app — the frontend

`apps/frontend/src/`, or simply `src/` while it is the only app.

| Folder | Due at |
|---|---|
| `app/bootstrap/` | the first screen — where the application starts |
| `app/routing/` | the second page |
| `app/providers/`, `app/layout/` | the first thing every page needs (a theme, a session, a shell) |
| `pages/` | the second page |
| `features/<feature>/` — `components/ hooks/ services/ state/ types/ tests/` | the first feature that owns more than one file, and only the subfolders it really has |
| `components/` | the first component used by two features — no product rules live here |
| `services/` | the first call to a server: **one API client** owning addresses, headers and error handling |
| `state/` | the first state two features share |
| `hooks/`, `types/` | the first one used twice |
| `validation/` | the first form, or the first response that must be checked before it is trusted |
| `config/` | the first setting the browser needs — never a secret: everything the browser gets is public (§69) |
| `styles/` | the first style not owned by one component |
| `locales/` | the second language — user-facing text out of components (§72); a right-to-left first language earns the direction and layout checks in §72, not this folder |
| `assets/` | the first image, icon or font |

## Inside one app — the backend

| Folder | Due at |
|---|---|
| `server/` | day one of the server — where it starts and listens |
| `api/routes/` | the first endpoint |
| `api/controllers/` | when a route does more than a few lines |
| `api/middleware/` | the first step that runs on every request |
| `api/schemas/` | the first input from outside — the contract, defined once and checked at the edge (§39) |
| `application/use-cases/` | the first operation with more than one step |
| `application/commands/`, `application/queries/` | when reads and writes stop looking alike |
| `application/services/` | the first job belonging to no single use case |
| `domain/entities/` | the first thing the product has rules about |
| `domain/rules/` | the first rule that must not live in a request handler |
| `domain/value-objects/` | the first value with its own validity (money, a coordinate, an identifier) |
| `domain/events/` | the first thing that happens because something else happened |
| `domain/interfaces/` | the first time the rules need the outside world — this is what keeps dependencies pointing inward (§9, §10) |
| `infrastructure/database/`, `repositories/` | the first stored row |
| `infrastructure/filesystem/`, `network/`, `external-services/` | the first file written, the first outside call |
| `infrastructure/messaging/` | the first queue or background job |
| `jobs/` | the first background or scheduled job — the job and its schedule are source (§93) |
| `realtime/` | the first screen that must change without a refresh, once polling is measured insufficient (§94) |
| `infrastructure/storage/` | the first uploaded or generated file the product keeps (§95) |
| `infrastructure/email/`, or `infrastructure/notifications/` when it also sends push or SMS | the first message the product sends to a person — one home, not both (§96) |
| `infrastructure/payments/` | the first money the product takes, or the first subscription it tracks (§97) |
| `api/webhooks/` | the first message another system sends to the product (§98) |
| `infrastructure/search/` | the first search the database's own features can no longer serve, by measurement (§99) |
| `audit/` | the first action someone will later ask "who did this?" about (§100) |
| `infrastructure/cache/` | the first thing measurably worth not computing twice — never earlier (§22) |
| `security/authentication/` | the first sign-in |
| `security/authorization/`, `permissions/` | the first thing one caller may do and another may not |
| `validation/` | the first check that lives outside a schema |
| `config/` with `.env.example` at the app root | the first setting the server has — `.env.example` names every setting with no real values; configuration is read in one place (§49, §69) |
| `logging/` | the first error worth keeping — never a secret, never personal data (§27) |
| `Dockerfile` at the app's build-context root | the first time the server must run somewhere other than the developer's machine, or needs a local service (database, cache, queue) to run at all (§70) |
| `.dockerignore` beside the Dockerfile | the first Dockerfile (§70) |
| `compose.yaml` at the local setup root | the first local multi-service setup (§70) |

## Inside one app — desktop, mobile, command line

Paths below are relative to that app's source root: `src/` for one standalone app, or
`apps/<name>/src/` when multiple deployables are in scope. A platform name does not earn
another wrapper directory on its own; accepted framework conventions still win (§61).

| Folder | Due at |
|---|---|
| desktop: `main/`, `preload/`, `renderer/` | each when the shell actually has that process, bridge or interface; these are Electron names, not required native-app layers |
| desktop: `application/`, `domain/`, `infrastructure/` | the same three layers as the server, the day the application has rules or storage of its own |
| desktop or mobile: `platform/` | the first thing only that operating system does (§14) |
| mobile: `app/`, `screens/`, `features/`, `services/`, `state/`, `assets/` | each as its frontend twin above |
| CLI: `commands/` | commands earn separate files when that separation helps; a one-file command stays one file |
| CLI: `core/`, `application/`, `infrastructure/` | when a command stops being one file |
| CLI: `output/` | formatting earns its own module when it is shared or substantial; printing one value needs no folder |

## More than one app

| Folder | Due at |
|---|---|
| `apps/<name>/src/`, `apps/<name>/tests/` | current approved scope requires multiple deployables, including day one when both are needed. One standalone app keeps a plain `src/`, unless its framework's accepted layout says otherwise |
| `features/<feature>/` at the root — `domain/ application/ infrastructure/ presentation/ contracts/ tests/` | a feature two apps both run, and only if the one-home rule named this as its home |
| `packages/contracts/` | the first type an app and a server both import |
| `packages/domain/` | product rules two apps share |
| `packages/ui/` | the first component two apps share |
| `packages/validation/`, `configuration/`, `logging/`, `utilities/` | each: the second app that needs that exact thing |
| `apps/worker/` | the first background work that cannot run inside the server's own process or must scale on its own (§93) |
| `platform/` — `persistence/ filesystem/ networking/ authentication/ authorization/ logging/ telemetry/ security/ integrations/ runtime/` | each folder: when **two** apps share that one concern. Before that it lives in the app's own `infrastructure/`, and having it in one app only is not a finding |

`packages/` against `platform/`: `packages/` is product code several apps import; `platform/` is
the machinery beneath them. If it carries product rules, it is a package.

## Data

| Folder | Due at |
|---|---|
| `data/schemas/` | the first table |
| `data/migrations/` | the first change to a table that has shipped — numbered, applied in order, never edited afterwards (§43) |
| `data/seeds/` | the first row a real installation needs in order to work |
| `data/backups/` | the first real data the project stores — and the ignore file carries `data/backups/` from that same day |

**A backup file never goes into version control.** The folder belongs to the project; what lands
in it does not. Version control is permanent, and a backup holds real user data, so one committed
by accident cannot be taken back (§27). How a backup is made and how one is restored belongs in
`docs/operations/`, and the restore is performed once for real: a backup that has never been
restored is not a backup.

**Synthetic test data lives with the test suite that owns it**, for example an app's
`tests/fixtures/` or the root suite's `tests/fixtures/`. Keep one authoritative home for each
fixture; production backups are never test fixtures.

## The AI part

A project that calls a model engineers that part like the rest of it. A project that does not
never grows this folder.

The `ai/` paths below belong inside the owning app's source root, as shown in
[the AI service example](trees/ai-service.md). They do not require a second root-level copy.

| Folder | Due at |
|---|---|
| `ai/prompts/` | the first prompt — a prompt is source, not a string buried in a file |
| `ai/agents/`, `ai/tools/` | the first agent, and the first tool it is permitted to call |
| `ai/orchestration/` | the first time two steps must run in order |
| `ai/providers/`, `ai/models/` | the first model call — the provider sits behind a boundary like any other external system (§11) |
| `ai/contracts/` | the first shape a model answer must satisfy, checked like any other external input (§39) |
| `ai/memory/` | the first thing carried between runs — with an owner, like any other state (§13) |
| `ai/runtime/` | the first time this runs in the real product |
| `ai/evaluations/` | the first prompt worth not breaking — this is the AI part's test folder |

## Tests

An app's own `tests/` holds its unit and component checks. The root `tests/` holds the kinds that
cross apps, so no check has two homes.

| Folder | Due at |
|---|---|
| `tests/unit/` | the first split, once a flat `tests/` holds more than a handful of files |
| `tests/integration/` | the first two parts that must work together |
| `tests/contract/` | the first interface both sides of this repository own (§39) |
| `tests/architecture/` | the first boundary worth guarding automatically — the check that dependencies still point inward |
| `tests/e2e/` | the first flow a person completes end to end |
| `tests/regression/` | the first defect that came back |
| `tests/performance/` | the first stated speed requirement (§45) |
| `tests/security/` | the first sign-in, permission or secret (§27) |
| `tests/fixtures/` | the first test needing data — never real user data |

A flat `tests/` is correct while it holds a handful of files.

## Settings, commands, tools, published files

| Folder | Due at |
|---|---|
| `config/` with an example settings file | the first setting |
| `config/<environment>/` | the second environment — only the ones that exist |
| `scripts/build/`, `test/`, `migration/`, `release/`, `maintenance/` | each: the first command a person runs for that job |
| `tooling/lint/`, `tooling/formatting/` | existing lint or format tooling needs maintained configuration beyond the runtime's normal config file |
| `tooling/architecture-checks/` | the first boundary worth guarding automatically |
| `tooling/code-generation/` | the first generated file — generated files are never hand-edited (§48) |
| `tooling/developer-tools/` | the first helper only a developer uses |
| `public/` | the first file served exactly as it is |
| the continuous-integration folder | the first check that should run without being asked — runs the same commands as local checks (§75) |

`scripts/` is what a person runs. `tooling/` is what runs by itself.

## What this never does

- **It never creates a folder before the product earns it.** Every row above says *due at* for
  that reason. Empty folders waiting for a future that may not arrive are the over-engineering
  this standard forbids (§22).
- **It never overrides a framework's own conventions, or a project's accepted layout.** Where a
  framework or an existing repository has a settled structure, that wins; this map describes the
  responsibilities, and layers are responsibilities rather than folders (§61).
- **It never reorganizes an existing project.** An existing project adopts the parts it needs as
  the work touches them, one coherent slice at a time (§20, §21, §28).
- **It never decides where a feature lives.** The project decides once and writes it down.
