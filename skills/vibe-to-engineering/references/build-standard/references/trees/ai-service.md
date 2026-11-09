# Example tree — AI service (a product that calls models)

A product whose features call an LLM or another model. The AI part is engineered like the
rest of the product: the provider is an external system behind a boundary (§11), a prompt is
source, a model's answer is untrusted external input (§39). Usually this tree grows INSIDE one
of the others — most often [webapp.md](webapp.md) or [api-backend.md](api-backend.md). A
project that never calls a model never grows any of this.

## Stage 1 — the first model call

```
  src/  (or apps/api/src/ — wherever the host app lives)
    ai/prompts/           earned by: the first prompt — a prompt is source, versioned and
                          reviewed, not a string buried in a handler
    ai/providers/         earned by: the first model call — ONE boundary owning the
                          provider client, retries and errors; keys come from the one
                          configuration boundary (§11, §42, §49, §69)
    ai/contracts/         earned by: the first shape a model answer must satisfy — checked
                          like any other external input before it is trusted (§39)
  docs/security.md        earned by: the first stored data, sign-in, network call or secret —
                          any API key stays out of source, logs and fixtures (§27, §69)
```

Product code calls `ai/` through its contract; nothing outside `ai/providers/` knows which
provider or model serves the call. Swapping providers must not rewrite product code.
The key is read only in `config/`, from an environment variable or secret manager; `.env.example`
at the host app's root is due at the first setting the server has and contains names, no real
values (§69). A secret never reaches the frontend: when there is a browser frontend, the
backend calls the model provider and the frontend calls that backend proxy (§69).

## Stage 2 — the feature earns structure

```
    ai/tools/             earned by: the first tool the model is permitted to call — each
                          tool is a boundary with its own validation (§39)
    ai/agents/            earned by: the first agent — a model loop with a defined goal,
                          tools and stop conditions
    ai/orchestration/     earned by: the first time two steps must run in order
    ai/memory/            earned by: the first thing carried between runs — state with an
                          owner, like any other state (§13): what is persisted, what is
                          derived, what must survive restart
```

## Stage 3 — real users, real stakes

```
    ai/runtime/           earned by: the first time this runs in the real product —
                          timeouts, cancellation, cost limits, partial failure (§46)
    ai/evaluations/       earned by: the first prompt worth not breaking — the AI part's
                          test folder; a prompt change without an eval run is an unverified
                          behavior change (§31)
  docs/adr/               earned by: the provider and model choice (§36) — it shapes cost,
                          privacy and behavior, and an owner-approved change belongs to the
                          Human Gate
  docs/operations/        earned by: the first build, sign, ship, release, backup or restore —
                          record model/prompt versions and eval locations before incidents
```

## What this tree must never do

- Never let a model's output write to persistence, call tools or reach users without passing
  its contract check (§39, §42).
- Never log prompts or completions that carry private user data (§27).
- Never build agents, orchestration or memory for a product that makes one model call —
  stage 1 is complete on its own (§22).
