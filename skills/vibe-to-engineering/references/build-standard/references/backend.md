# Backend

How a server behaves as it earns endpoints, storage and deployment. Apply only the parts
whose **due at** trigger the product has reached (§22). A project's accepted rules and
framework conventions still win (§61); responsibilities do not require a new folder when
the existing structure already owns them.

## Contents

- §66 API contract and errors
- §67 Reliability and operations
- §68 Backend security
- §69 Secrets and API keys
- §70 Containers (Docker)
- §106 Overload and traffic spikes

## §66 API contract and errors

**Due at:** the first endpoint; the additional triggers below earn pagination, API
documentation and rate limits separately.

- Use one error response shape across the API: `code`, `message`, optional `details`, and
  a `request_id`. Use correct HTTP status codes: 4xx means a caller-side problem; 5xx means
  a server-side failure. Never expose stack traces, SQL or internal paths to the caller.
- **Pagination is due at the first endpoint that returns a list that can grow.** Bound
  the page size, including a maximum enforced by the server.
- Additive changes keep existing callers compatible. Breaking a published API goes
  through the Human Gate (§30, §44); do not silently change its contract.
- **An API description in `docs/api/` is due at the first endpoint something else calls.**
  Use the project's appropriate format, such as OpenAPI, and keep it true with a contract
  test (§39).
- **Rate limits are due at the first endpoint reachable by the public or by untrusted
  callers.** Enforce them on the server.
  An internal endpoint counts when callers whose trust has not been established can
  reach it; network location alone establishes none (§68).

## §67 Reliability and operations

**Due at:** the first outside call, request or job that can fail; storage and operational
controls become due at their own triggers below.

- Every outside call has a timeout. Retry only operations that are safe to repeat, with
  backoff. A write that may be retried carries an idempotency key, enforced by the receiver
  so a repeated request cannot repeat the effect: retrying a payment must not charge twice.
- **A transaction is due at the first operation that writes more than one row or record
  that must succeed or fail together.** Test the failure path as well as success.
- Once real data volume exists, inspect for N+1 queries and missing indexes. Measure the
  actual query behavior before optimizing (§45).
- **A health check endpoint is due at the first deployment anywhere beyond the developer
  machine.**
- Graceful shutdown finishes or safely stops in-flight requests and jobs when the server
  stops; do not abandon partially completed work without an explicit recovery path.
- **Logs are due at the first error worth keeping**, as in the layout map. Make them
  structured, carry one request id through the request, and never log a secret or personal
  data (§27).
- **Metrics and alerts are due at the first deployment someone depends on.** Record enough
  operational evidence to detect failures without exposing private data.

### Self-managed server checks

**Due at** the first deployment anywhere beyond the developer machine on a server the
project team maintains, including a rented virtual machine. Complete the checks before
making the deployment available to its users. Where a hosting provider manages part of
the server, record who owns each control and verify the settings the project controls.

- **Firewall rules.** Read the rules in effect on the running server and in the hosting
  provider console, where applicable. Allow only the ports and source networks the
  service requires, and restrict access to administration and internal services. From an
  authorized test client outside the allowed network, confirm that a connection to a
  running restricted service is blocked.
- **Administrative access.** Compare administrator accounts, roles and any authorized
  keys on the running server and in the provider console with the approved list, where
  applicable. Verify individual accounts, strong authentication and only the privileges
  they need. Record how access is removed.
- **Operating-system security updates.** Check that the host runs a supported release
  and that required security patches are applied. Name who applies updates and how
  urgent fixes and restarts are handled.
- Record the environment, results and any checks awaiting evidence in the existing
  Plan or operations runbook (§82, §87).

## §68 Backend security

At a material trust boundary, use the [threat assessment and failure evidence (§88)](coverage-and-evidence.md#88-threat-assessment-and-security-failure-evidence); reuse the approved Security/Plan checks.

**Due at:** the first outside input; authorization, session, password and public-deployment
controls become due when those capabilities exist.

- Validate every outside input at the edge (§39). The server never trusts the browser,
  including values the browser already validated.
- Use parameterized queries or the ORM's safe API. Never build SQL or shell commands by
  concatenating input; use a safe process API with separate, validated arguments when a
  process is needed.
- Check authorization on the server for every protected operation. Hiding a UI control
  does not protect its endpoint.
- **Network location alone establishes no trust.** A caller on a LAN, office network or
  VPN is not trusted because of where it connects from: an insider, an infected machine
  on the same network, or a later change that opens the service further can all reach
  it. Authenticate and authorize it like any other caller; network restrictions (§67)
  reduce exposure but replace neither.
- **Identity-provider administration stays out of the product, due when the product
  integrates an identity provider.** Provider-wide administration (users, roles, realms
  and clients) belongs in the provider's own console or approved operator tooling, not
  in the application's screens. An approved product account workflow, such as inviting
  a user to the product, runs as a narrow server operation that authorizes the caller,
  the action, the target and the tenant where applicable, using a dedicated
  least-privilege service identity whose credentials and privileged tokens stay on the
  server at build time and at runtime (§69).
- When cross-origin browser access is needed, CORS uses an explicit allow-list of origins;
  never allow `*` with credentials.
- Cookie-based sessions need CSRF protection. When passwords are used, hash them with the
  platform's standard password-hashing function; never store or log plaintext passwords.
- **Limit repeated failed sign-ins, due at the first sign-in that verifies a password
  or one-time code**, a second-factor code included. The server or identity provider
  that verifies the credential enforces a per-account limit on failed attempts, counted
  across all sources, and the sign-in entry point throttles each source separately
  (§66). Prefer a bounded delay or temporary lockout, and record the threshold or
  delay, the reset window and the recovery path with the other §68 choices. The
  rejection a client sees, a throttled one included, never reveals whether the account
  exists or is locked: a source limit may answer with §106's generic 429, while an
  account limit answers like any failed sign-in. Never enforce the limit only in the
  browser.
- **Security headers and a dependency vulnerability check are due at the first public
  deployment.**
- Record these choices in `docs/security.md`, already **due at the first stored data,
  sign-in, network call or secret**, as in the layout map.

## §69 Secrets and API keys

**Due at:** the first server setting earns a configuration boundary. Environment-backed
settings earn `.env.example`. Secret handling applies from the first secret the project uses.

- A key lives in an environment variable or a secret manager, and is read in **one place**
  behind the configuration boundary (`config/`, §49). Other code uses that boundary; never
  copy keys or duplicate their lookup across files.
- `.env.example` lists the environment variable names with safe placeholders. Keep a local
  `.env` out of Git when the project uses one. Document other settings using their actual
  configuration source (§61, §85).
- Use separate keys for development, test and production when each environment exists,
  with only the permissions that environment's job needs.
- **A project's secret never ships to users.** Anything shipped is public — browser code,
  mobile apps, desktop apps and published CLI binaries — including obfuscated or "hidden"
  keys and build-time variables with public prefixes such as `NEXT_PUBLIC_`, `VITE_` and
  `REACT_APP_`. A paid or private API, including an AI/model provider, is called through a
  server the project controls; the client calls that backend proxy, and the project's key
  stays on the server. Exception: a tool where **each user supplies their own key at run
  time** through an environment variable or OS keychain/secure storage is fine. The rule
  forbids the project's key baked into a build.
- Never log, print or echo a key, or put one in test fixtures, error messages or screenshots.
- If a key leaks, report where it was exposed immediately without printing the value.
  A reviewer or an agent without response authority leaves credentials and history alone.
  The authorized operator revokes and replaces the key immediately.
  If the key reached a shared repository, get the owner's approval before rewriting shared
  history (§30). If only a runtime log was exposed, address that log after rotation and
  leave Git history alone.
  Deleting a commit does not make a leaked key safe.
- **Secret scanning, through a pre-commit or CI scanner, is due at the first secret the
  project uses.**

## §70 Containers (Docker)

**Due at:** add an application Dockerfile when the chosen way to run or deliver the
app uses a container image. A local development database, cache or queue can run on
its own. Leave out the Dockerfile for a small local tool, a source-deployed function
or a static site when its runtime and delivery use no app image (§22).

- If the project already has a working container setup, use it as it is (§61).
- When a Dockerfile is earned, pin the base image version, never `latest`. Use a multi-stage
  build so build tools stay out of the final image, run as a non-root user, keep one main
  process, and provide a `HEALTHCHECK` or the platform's equivalent.
  Build and start the image, then check that it becomes healthy.
- **`.dockerignore` is due at the first Dockerfile.** Exclude `.git`, `.env` and other secret
  files, dependency folders and build output from the build context.
- No secrets in the image, build arguments or layers. Secrets arrive at run time (§69).
- **`compose.yaml` is due at the first local multi-service setup.** It is for development
  unless the project decided otherwise. Data the app needs to keep lives in a named volume.
- A dedicated Docker skill, when installed, may supply deeper container guidance.

## §106 Overload and traffic spikes

**Due at:** the first endpoint, queue or job that the public or another system can drive
faster than it can be served. A tool used by a few known people earns only the first
bullet (§22).

A spike is not a reason to build for millions. It is a reason to know what happens at the
limit: the server slows down or says "busy", and never crashes or loses work it accepted.

- Everything that can grow has a bound: request body size, page size (§66), queue length
  (§93), work running at once, and connections to the database. An unbounded one is where
  a spike becomes an outage.
- At the bound, refuse cheaply and honestly, and say which kind of "no" it is, because
  the caller must know whether trying again can help. Never a hung request and never a
  500. Over HTTP:
  - **one input is too big** (an upload or a body over the size limit): 413. Sending the
    same thing again will never work, so no `Retry-After`; the message says the limit;
  - **one caller is sending too fast** (a rate limit, §66, §68): 429 with a `Retry-After`;
  - **the server is full for now** (queue full, no free worker or connection): 503 with a
    `Retry-After`.
- Work already accepted is finished or kept durably; it is never dropped silently
  (§67, §93).
- Callers told to try again do so with backoff and a little randomness, so retries do
  not become a second spike (§67). Rate limits (§66, §68) protect one caller from
  another; they do not replace the bounds above.
- When not everything can be served, the product decides what is served last to fail:
  usually sign-in and payment before browsing. That order is the owner's decision; ask in
  plain words (§84).
- A request measured to be slow is first a bottleneck to find and fix (§45): a missing
  index or a repeated query is repaired, and the request keeps answering directly. Slow
  alone never turns a request into a job. Only work that meets §93's own trigger, work
  that should not make a request wait even when it runs well, such as sending mail or
  building a large export, becomes a job; then the request answers quickly with
  "accepted" and a way to see the result.
- Know the limit by measurement, never by guess. Before a known peak such as a launch, a
  sale or a campaign, load-test a non-production copy with synthetic data until it bends,
  and record the number and what bent first in `docs/operations/`. More copies, a bigger
  machine or automatic scaling follow that measurement and never come first (§45, §101).
- Alert when a bound is nearly reached, not only after it fails (§67).
