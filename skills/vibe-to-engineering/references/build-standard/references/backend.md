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
- When cross-origin browser access is needed, CORS uses an explicit allow-list of origins;
  never allow `*` with credentials.
- Cookie-based sessions need CSRF protection. When passwords are used, hash them with the
  platform's standard password-hashing function; never store or log plaintext passwords.
- **Security headers and a dependency vulnerability check are due at the first public
  deployment.**
- Record these choices in `docs/security.md`, already **due at the first stored data,
  sign-in, network call or secret**, as in the layout map.

## §69 Secrets and API keys

**Due at:** the first setting the server has earns `config/` and `.env.example`; secret
handling applies from the first secret the project uses.

- A key lives in an environment variable or a secret manager, and is read in **one place**
  behind the configuration boundary (`config/`, §49). Other code uses that boundary; never
  copy keys or duplicate their lookup across files.
- `.env.example` lists every setting name with **no real values**. Keep the real `.env` in
  `.gitignore`; follow the framework's accepted configuration location (§61).
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
- If a key leaks, **REVOKE AND REPLACE IT FIRST, then clean history**. Deleting a commit
  does not make a leaked key safe.
- **Secret scanning, through a pre-commit or CI scanner, is due at the first secret the
  project uses.**

## §70 Containers (Docker)

**Due at:** the first time the server must run somewhere other than the developer's
machine, or needs a local service (database, cache, queue) to run at all. Not earlier:
a small local tool or a static site does not get a Dockerfile (§22).

- If the project already has a working container setup, use it as it is (§61).
- When a Dockerfile is earned, pin the base image version, never `latest`. Use a multi-stage
  build so build tools stay out of the final image, run as a non-root user, keep one main
  process, and provide a `HEALTHCHECK` or the platform's equivalent.
- **`.dockerignore` is due at the first Dockerfile.** Exclude `.git`, `.env` and other secret
  files, dependency folders and build output from the build context.
- No secrets in the image, build arguments or layers. Secrets arrive at run time (§69).
- **`compose.yaml` is due at the first local multi-service setup.** It is for development
  unless the project decided otherwise. Data the app needs to keep lives in a named volume.
- A dedicated Docker skill, when installed, may supply deeper container guidance.
