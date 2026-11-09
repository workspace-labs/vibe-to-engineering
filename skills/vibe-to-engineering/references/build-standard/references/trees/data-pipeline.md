# Example tree — data pipeline

Scheduled or streaming jobs that move and transform data: ingestion, ETL, reports, syncs. The
defining risks here are ordering, idempotence, malformed input and re-runs — so the data
model and failure ownership come before volume (§12, §42, §43). Snapshots of growth, never a
template (§22).

## Stage 1 — day one

```
mypipeline/
  README.md               what flows where, on what schedule
  CHANGELOG.md
  .gitignore
  docs/scope.md
  src/
  tests/
```

## Stage 2 — the first flow

```
  src/
    ingestion/            earned by: the first source read — every external input checked
                          against a schema before it is trusted (§39)
    transforms/           earned by: the first transformation — pure where practical:
                          same input, same output, no clock or network inside (§8)
    sinks/ or loaders/    earned by: the first destination written — partial writes and
                          retries designed, not discovered (§42)
    quality/              earned by: the first stated data-quality requirement — validate
                          before a bad batch reaches a sink, not after an incident
    config/               earned by: the first connection string or schedule — an example
                          file, no real values (§49)
  docs/architecture/boundaries.md   earned by: past the kit
  data/schemas/           earned by: the first shape that flows through — the contract for
                          every stage, defined once
```

Re-run safety is a stage-2 property, not a later hardening: running the same job twice must
not duplicate or corrupt (§43).

## Stage 3 — operated and trusted

```
    jobs/ or orchestration/   earned by: the first time two steps must run in order
  tests/fixtures/         earned by: the first test needing data — synthetic records,
                          NEVER copied production data (§27)
  tests/integration/      earned by: the first two stages that must work together
  docs/operations/        earned by: the first build, ship, release, backup, restore or operated
                          run — re-run, backfill and recovery steps; scheduling is not a prerequisite
  data/backups/           earned by: the first real data the pipeline produces — ignored by
                          version control from the same day (§27)
  docs/security.md        earned by: the first stored data, sign-in, network call or secret
```

## Stage 4 — quality at scale

```
  tests/regression/       earned by: the first defect that came back
  tests/performance/      earned by: the first stated throughput or window requirement (§45)
  docs/adr/               earned by: the ordering and idempotence model (§36) — event time
                          versus processing time, deduplication keys, replay semantics (§12, §41)
  data/migrations/        earned by: the first change to a shape that downstream consumers
                          already read (§43, §44)
```

What this tree must never do: never let a transform know the orchestrator, never let a sink
silently drop malformed records, and never optimize for volume before the baseline is
measured (§45).
