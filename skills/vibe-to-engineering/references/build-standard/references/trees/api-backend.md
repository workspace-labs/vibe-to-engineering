# Example tree — API-only backend

A service other programs call: REST or GraphQL API, worker processes, queues — no UI of its
own. Snapshots of one project as it grows — **never a template to scaffold**. Create only what
is earned (§22). A framework's own conventions win (§61); the responsibilities are the rule.

## Stage 1 — day one

```
myservice/
  README.md               what it serves, how to run it
  CHANGELOG.md
  .gitignore
  docs/scope.md
  src/
  tests/
```

## Stage 2 — the first endpoints

```
  src/
    server/               earned by: day one — where it starts and listens
    api/routes/           earned by: the first endpoint
    api/schemas/          earned by: the first input from outside — the contract, defined
                          once and checked at the edge (§39)
    api/middleware/       earned by: the first step that runs on every request
    config/               earned by: the first setting the server has — read configuration
                          in one place (§49, §69)
    logging/              earned by: the first error worth keeping — never a secret,
                          never personal data (§27)
  docs/architecture/boundaries.md   earned by: past the kit
  .env.example            earned by: the first setting the server has — every setting name,
                          no real values (§69)
  the runtime version file   earned by: the first build or dependency
  the appropriate lockfile(s)   earned by: managed dependencies for this runtime
```

## Stage 3 — the product gets rules and storage

```
  src/
    application/use-cases/    earned by: the first operation with more than one step
    domain/entities/          earned by: the first thing the product has rules about
    domain/rules/             earned by: the first rule that must not live in a handler (§8)
    domain/interfaces/        earned by: the first time the rules need the outside world —
                              keeps dependencies pointing inward (§9)
    infrastructure/database/, repositories/   earned by: the first stored row (§11)
    security/authentication/  earned by: the first sign-in
    security/authorization/   earned by: the first thing one caller may do and another may not
  data/schemas/             earned by: the first table
  docs/security.md          earned by: the first stored data, sign-in, network call or secret (§27)
  docs/api/                 earned by: the first endpoint something else calls — for an
                          API-only service this arrives early and stays truthful
```

## Stage 4 — shipped and operated

Each entry is earned by its own trigger, even if that happens before the other entries here.

```
  Dockerfile             earned by: the first time the server must run somewhere other
                          than the developer's machine, or needs a local service
                          (database, cache, queue) to run at all (§70)
  .dockerignore          earned by: the first Dockerfile (§70)
  compose.yaml           earned by: the first local multi-service setup (§70)
  data/migrations/        earned by: the first change to a table that has shipped —
                          numbered, applied in order, never edited afterwards (§43)
  src/infrastructure/messaging/   earned by: the first queue or background job
  src/jobs/               earned by: the first background or scheduled job — safe to run twice,
                          seen when it fails (§93)
  src/api/webhooks/       earned by: the first message another system sends — raw body read,
                          verified, recorded, then acknowledged; processed once (§98)
  src/infrastructure/storage/   earned by: the first file the product keeps (§95)
  infra/                  earned by: the first cloud resource someone would have to recreate
                          by hand (§102)
  src/infrastructure/cache/       earned by: the first thing MEASURABLY worth not computing
                          twice — never earlier (§22, §45)
  tests/contract/         earned by: the first interface both sides own — for an API, the
                          published contract itself (§39)
  docs/operations/        earned by: the first build, sign, ship, release, backup or restore —
                          add deploy runbooks and verify restore when those operations arrive
  docs/deployment/        earned by: the first release, including rollback
  docs/adr/               earned by: the persistence-strategy decision (§36) — it is a
                          compatibility commitment (§44), through the Human Gate
```

An API's public contract is released software: breaking it is a Human Gate decision (§30),
versioned and documented — the same discipline as [library.md](library.md).
