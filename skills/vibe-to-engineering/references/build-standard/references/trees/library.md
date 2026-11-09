# Example tree — published library / package

Code other projects import. The contract IS the product here: consumers pin versions, so
backward compatibility (§44) and the changelog carry more weight than in an app. Snapshots of
growth, **never a template** — create only what is earned (§22).

## Stage 1 — day one

```
mylib/
  README.md               what it does, one usage example
  CHANGELOG.md            consumers read this before every upgrade — it is not optional here
  .gitignore
  docs/scope.md           what it does, and what it will NOT do
  src/
    index.*               the public entry point — everything exported here is a promise (§44)
  tests/
```

## Stage 2 — the internals grow

```
  src/
    index.*               still the only public door — internals are NOT exported casually
    <module>/             earned by: the first internal responsibility too big for one file
  docs/architecture/boundaries.md   earned by: past the kit — what is public, what is private
  the runtime version file          earned by: the first build or dependency
```

The module boundary quality gate (§38) applies doubled: what is the public contract, what
stays private, and can it change without breaking consumers?

## Stage 3 — published and versioned

```
  LICENSE                 earned by: distribution requires an explicit licence — the owner chooses,
                          including when consumers receive it privately
  docs/api/               earned by: the first public surface a consumer must look up
  docs/deployment/        earned by: the first release — versioning and publish procedure
  the CI folder           earned by: the first check that should run on every change —
                          for a library this includes the test matrix of supported runtimes
  docs/adr/               earned by: the first intentional limitation or compatibility
                          commitment (§36)
```

A breaking change is a Human Gate decision (§30): it breaks released compatibility, so it is
deliberate, documented in the CHANGELOG, versioned accordingly, and approved.

What a library never earns: `apps/`, `server/`, `data/`, deployment environments, feature
folders. If it grows an executable, that executable is its own app — see
[cli-tool.md](cli-tool.md) — and imports the library like any other consumer.
