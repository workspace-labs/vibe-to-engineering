# Platform services

The services a product grows around its code as it meets real users: a public address,
sessions, background work, files, mail, money, outside systems, search, caching, more than one
running copy, infrastructure, public pages, and measurement. Each applies only at its
**due at** trigger (§22); a small local tool or a static page never earns most of this.
Accepted project rules, framework conventions and a hosting platform's documented defaults
still win (§61). A responsibility does not require a new folder when the existing structure
already owns it; the [layout map](layout-map.md) names the home when one is earned.

## Contents

- §91 HTTPS, domains and certificates
- §92 Sessions and multi-tenancy
- §93 Background jobs, queues and scheduled tasks
- §94 Realtime connections
- §95 Files, uploads and object storage
- §96 Email and notifications
- §97 Payments and billing
- §98 Webhooks and integrations
- §99 Search
- §100 Audit log
- §101 Caching, CDN and running more than one copy
- §102 Infrastructure as code
- §103 Public pages and SEO
- §104 Product analytics and error tracking

## §91 HTTPS, domains and certificates

**Due at:** the first address anyone but the developer opens.

- Everything served to users travels over HTTPS. Plain HTTP only redirects to HTTPS. Add
  HSTS once the redirect is proven; it is hard to take back.
- Certificates renew automatically through the hosting platform or an ACME client; a
  certificate a person must remember to renew will expire on a weekend.
- Where the domain is registered, who owns the account and where DNS is managed are
  written in `docs/deployment/`, with the records the product depends on and why each one
  exists — a product nobody can renew or move is lost on handover (§85).
- Local development may use plain HTTP on `localhost`; cookies and redirects behave
  differently there, so the first deployment is checked over its real address (§78).

## §92 Sessions and multi-tenancy

**Due at:** the first sign-in earns the session rules; the first customer whose data must
never be seen by another customer earns the tenancy rules.

- A session has an expiry, is created fresh at sign-in, and can be revoked on the server:
  sign-out and a password change end the old sessions. Store sessions where every running
  copy can read them (§101), never only in one process's memory. Transport and CSRF rules
  are in §68 and §72.
- When more than one organisation shares the same deployment, every row they own carries
  its tenant, and the check that a caller belongs to that tenant lives **once**, at the
  persistence or authorization boundary (§11, §68), never repeated in each handler.
- Test tenancy with two synthetic tenants: everything one sees, the other does not, after
  denied reads, writes and deletes (§88). Decide early whether tenants share one database
  or get one each — that is a persistence decision through the Human Gate (§30).

### Keycloak and LDAP — when each fits

**Due at:** a requirement for central sign-in, single sign-on (SSO), or an organisation's
existing user directory. Ordinary sign-in alone requires neither Keycloak nor LDAP.

- **Choose from the need.** Keycloak is an identity and access management service: consider
  it for shared sign-in across applications, central account management or identity
  federation. LDAP is a protocol for accessing a directory, such as OpenLDAP or Active
  Directory; connect it when the product must use that directory's accounts or groups.
  LDAP alone does not supply an application's browser sessions or SSO. Reuse the accepted
  identity provider before proposing another; introducing or replacing one follows the
  existing Human Gate (§30, §44), never a second approval of an accepted design.
- **Keep the boundary clear.** When both are selected, applications normally sign in
  through Keycloak using OpenID Connect (OIDC), while Keycloak federates the LDAP directory.
  Keep directory access on the server; do not give browsers LDAP bind credentials or copy
  directory passwords into the application's database. A direct LDAP integration belongs
  behind one server boundary only when the accepted design calls for it. Keep product
  authorization on the server (§68); successful sign-in is not permission to every record.
- **Use the chosen protocol safely.** For interactive OIDC clients, use a maintained
  library and Authorization Code flow, with PKCE for public clients; never embed a client
  secret in a browser, mobile or desktop build (§69). Preserve an accepted SAML integration
  rather than replacing it just to use OIDC. Restrict redirect addresses and allowed
  origins, and validate callbacks with the library's state/nonce protections. APIs verify
  access tokens against the expected issuer, audience, signature and validity window,
  then check permissions; decoding a JWT or accepting an ID token is not API authorization.
- **Apply the §68 sign-in and administration rules.** Where Keycloak verifies the
  credential, enable and configure its brute-force detection to meet the failed-sign-in
  limit; where an upstream provider verifies it, establish the limit there. Prove the
  configured limit and its recovery with synthetic users in the integration checks
  below. Manage realms, clients, users and roles in the Keycloak admin console or
  approved operator tooling, never from the product's screens; a product account
  workflow uses a dedicated service account with only the realm-management roles it
  needs.
- **Decide directory ownership before syncing.** Record the stable user identifier,
  attribute/group-to-role mapping, account linking, import/cache/sync behaviour and who
  owns account changes. Do not auto-link accounts solely by a matching email. Prefer
  `READ_ONLY` LDAP federation unless directory writes are explicitly required and approved;
  user edit mode and group/role mapper write settings are separate decisions. Use a bind
  account with only the required permissions, protect its secret (§69), and require LDAPS
  or StartTLS with certificate validation; a failed TLS connection never falls back to
  plaintext or disabled verification.
- **Design access removal and outages.** Agree how quickly a disabled/deleted account or
  removed group must lose access, including cached directory data, local sessions and
  issued tokens. Logout or a directory change does not automatically invalidate every
  JWT already accepted offline; meet the agreed delay with expiry and the selected
  revocation/session checks. Bound directory/provider calls (§67), and never grant new
  access or use a weaker login fallback when they fail. Existing sessions follow the
  documented expiry and revocation policy; an outage must not silently extend them.
- **Prove the integration and hand it over.** Use an isolated realm/directory and
  synthetic users (§79, §88): try allowed and denied access, wrong credentials, expired
  or wrong-issuer/audience tokens, logout, removed groups, disabled/deleted users, sync
  delay, invalid certificates and provider outages as applicable to the selected path.
  A mocked test does not prove real federation; name untested paths. Document the issuer,
  realm, client IDs, redirects, directory address/search bases, mappings, TLS trust and
  secret sources, plus sync/revocation policy, operator ownership and recovery in the
  existing settings/security/deployment docs (§85, §89). Keep real credentials, users and
  unsanitized realm exports out of source and evidence (§27, §69).

Check the selected version's official [OIDC integration guide](https://www.keycloak.org/securing-apps/oidc-layers),
[client adapter guide](https://www.keycloak.org/securing-apps/javascript-adapter),
[LDAP federation guide](https://www.keycloak.org/docs/latest/server_admin/index.html#_ldap)
and [TLS guidance](https://www.keycloak.org/server/enabletls) when implementing; these
instructions explain the engineering decisions, not a fixed deployment recipe.

## §93 Background jobs, queues and scheduled tasks

**Due at:** the first work that should not make a request wait, the first repeat on a
schedule, or the first work that must survive a restart.

- Start with the simplest mechanism the stack already has — a database-backed queue or
  the platform's scheduler. A separate queue service or a separate worker app
  (`apps/worker/`) is earned when the work cannot run inside the server's own process
  or must scale on its own (§22).
- Every job is safe to run twice: it checks what was already done or carries an
  idempotency key (§67). Jobs have a timeout, bounded retries with backoff, and a place
  where a job that keeps failing lands and is seen by someone (a dead-letter queue or an
  alert).
- Scheduled work runs **once** per schedule, not once per running copy: use the
  platform's single scheduler, or a lock the copies share (§101). The schedule itself is
  source, next to the job, not a setting only one person knows.
- A job's run is observable: when it ran, how long, whether it succeeded, with the request
  or job id in the logs and never a secret (§67). A job that silently stops running is the
  most common quiet outage.

## §94 Realtime connections

**Due at:** the first screen that must change without the person refreshing, when
polling at a sensible interval is measured to be insufficient (§45).

- The connection is authenticated like any request, and authorization is checked for each
  subscription, not once at connect.
- The stream is a notification, not the source of truth. On reconnect the client re-reads
  the current state from the server; a client that only replays events will drift.
- Every connection has a reconnect strategy with backoff, and a limit on connections and
  message size on the server. A product that works only while the socket is open falls
  back to polling or shows the person that it is offline (§71).
- Realtime code has one home (`realtime/`), with the same boundary toward product rules
  as the HTTP side (§8, §9).

## §95 Files, uploads and object storage

**Due at:** the first file a user uploads, or the first file the product generates and
keeps.

- Files live outside the application folder and outside version control: on object
  storage, or a dedicated directory the deployment backs up (§89). Backups include the
  files and the database together; one without the other does not restore (§89).
- Validate every upload: an enforced size limit before the body is read, the real content
  type checked from the bytes and not the extension or the browser's claim, and a name
  the server chooses. Never execute or include an uploaded file, and never serve uploads
  from a path that can run code.
- Private files are reached through the application's authorization (§68), for example
  short-lived signed links, never by a public guessable address. Public files may use a
  CDN (§101).
- The storage provider sits behind one boundary (`infrastructure/storage/`) so switching
  providers or running locally changes one place (§11). Record the retention and deletion
  of files in `docs/privacy.md` when they hold personal data (§80).

## §96 Email and notifications

**Due at:** the first message the product sends to a person.

- One sender boundary (`infrastructure/email/`, or `infrastructure/notifications/` when it
  also sends push or SMS — one home, not both) owns the provider,
  templates and sending; features ask it to send, they do not call the provider.
- Review mail templates as source. Keep secrets out of templates and include only the
  personal data the message needs (§27). A sign-in, password-reset or other access link
  is a secret while it works, even if it expires or can be used only once. Ordinary
  links to public information can be shared.
- Development and tests use synthetic mail in an isolated inbox or fake sender. Check
  that the intended test recipient can use the access link. Keep usable access links,
  their tokens and private recipient data out of ordinary logs, error output and
  retained test reports. Check those outputs on both a successful send and a failed one.
- Sending is retried safely (§67) and never duplicated by a retried request. Transactional
  mail (receipts, sign-in links) and marketing mail are different things; marketing needs
  consent and an unsubscribe that works (§80). The sending domain's authentication
  records (SPF, DKIM, DMARC) are set up with the domain (§91), or the mail will not arrive.

## §97 Payments and billing

**Due at:** the first money the product takes, or the first subscription it tracks.

- The product never sees, stores or logs a card number: the provider's hosted or tokenised
  flow does, and the product keeps only the provider's references. This is also what
  keeps most card-industry obligations out of the project (§90).
- Money is stored as an integer in the currency's minor unit with its currency code, never
  as a float (§40).
- The provider's confirmation — its webhook or a verified server-side lookup — is the
  source of truth for whether a payment happened; the browser's redirect is not (§98).
  Every charge carries an idempotency key so a retry cannot charge twice (§67).
  Before requesting a charge, save a pending payment with a reference the provider can
  match. If confirmation is missing after a restart, look up that payment with the
  provider. Recovery checks the original charge without starting another (§100).
- Test and live provider keys are different keys, held as any secret (§69); development
  uses the provider's test mode only. Keep a record that lets the owner reconcile the
  provider's statement with the product's own records, and write refunds and failed
  payments into the design from the first version.

## §98 Webhooks and integrations

**Due at:** the first message another system sends to the product, or the first one the
product sends to another system.

- Incoming webhooks are untrusted input (§39, §68). Read the raw body up to a size limit,
  then verify it the way the chosen provider documents — usually a signature over those
  exact raw bytes, plus the provider's own replay protection such as a signed timestamp
  where it offers one — **before** parsing, trusting or acting on it. A delivery that
  fails verification is rejected and never reaches product code; accept only the events
  the product handles.
- Accept durably, then respond, then do the work: after verification, record the event
  with its id (or enqueue it) and only then return success; if that write fails, return
  a failure so the sender retries. Processing happens afterwards as a job (§93). The same
  event id is processed once, across restarts; senders retry and deliver out of order.
- Outgoing webhooks are signed so receivers can verify them, retried with backoff and
  limits, and their payloads documented in `docs/api/` like any contract (§66).
- Each outside system sits behind one boundary (`infrastructure/external-services/`,
  §11) with a timeout (§67); its sandbox credentials are separate from live ones (§69).
  Never call a live third party from tests (§88).

## §99 Search

**Due at:** the first screen where a person types to find things. A separate search
engine, and its home, are earned only when the database's own search is measured to be
insufficient for the data size and the need (§45).

- Start with the database the product already has: an index, a full-text feature, or a
  simple filter is often enough for years. A separate search engine is earned by
  measurement, not by the word "search" (§22).
- A search index is **derived** data: rebuildable from the source of truth, updated when
  the source changes, and never written to directly as if it were the record. The rebuild
  is a documented, tested command (§89).
- Search obeys the same authorization as the data it finds (§68, §92): a result a person
  may not open is a result they must not see.

## §100 Audit log

**Due at:** the first action someone will later ask "who did this, and when?" about —
sign-ins, permission changes, money, deletion, access to sensitive records.

- An audit record carries who, what, which object, when, and from where. When one local
  store controls the action, write the action and its audit record in the same
  transaction so both commit together (§67).
- It is append-only: never edited, never deleted by the application, retained by the
  policy in `docs/privacy.md` (§80). It holds no secrets and no more personal data than
  the question needs (§27).
- It is separate from debug and operational logs (§67): those rotate and are for the
  engineers; the audit log is for the owner, the customer and the investigator.
- When an outside provider owns the outcome, match its verified confirmation to the
  pending action. For a payment (§97), a webhook and a recovery lookup can report the
  same success. In one local transaction, mark the original payment paid and append its
  audit record with the provider reference. Enforce one success per payment even if
  both confirmations arrive together. A repeat leaves the existing result in place.

## §101 Caching, CDN and running more than one copy

**Due at:** the first result measured to be worth not computing twice earns a cache; the
first public static files at volume earn a CDN; the second running copy of the server
earns the stateless rules.

- A cache is derived data with an owner, a time-to-live and an invalidation when the
  source changes; the key includes everything that changes the answer, including the
  user or tenant, or per-user data leaks between people (§13, §92). Never cache a response
  that carries credentials.
- A CDN serves public static files and never private ones; cache headers say what may be
  cached and for how long, and a changed file gets a new name or a purge.
- Before a second copy runs behind a load balancer, nothing the next request needs lives
  in one process's memory: sessions, caches, locks and uploaded files live in shared
  stores (§92, §93, §95). The balancer uses the health check (§67), and every copy shuts
  down gracefully (§67). Scaling is a response to measurement, never a starting design
  (§45, §58).

## §102 Infrastructure as code

**Due at:** the first cloud resource someone would have to recreate by hand after it is
lost — a database, a bucket, a DNS record, a server.

- Infrastructure lives in `infra/` as code that can be read, reviewed and applied again
  (Terraform, Pulumi, the platform's own manifests), one folder per environment that
  exists (§79). A resource clicked together in a console and never written down is a
  handover failure (§85).
- The tool's state file and its variables hold secrets and identifiers: keep state in the
  tool's remote backend, never in version control, and pass secrets at apply time (§69).
- Review the plan before applying it, and apply from one place (a person or CI, not both
  at once). Take planned destruction or new recurring spend through the Human Gate (§30).
  Keep infrastructure destruction out of automatic runs.

## §103 Public pages and SEO

**Due at:** the first public page meant to be found by search or shared by link. Pages
behind sign-in earn none of this.

- Each public page has one canonical address, a title and a description, a sensible
  heading structure (§72), and an honest 404 for addresses that do not exist.
- A `robots` policy and a `sitemap` are added when they serve a need: a small, well-linked
  site may have neither or keep a short hand-maintained file. Once the site has many or
  changing pages, the sitemap is generated from the real routes so it never drifts from
  the pages that exist; a `robots` file is a policy, written and reviewed on purpose.
- Pages render their essential content without client-side scripting when the framework
  allows it, and measured page speed (§72) is checked on the public address, not only
  locally.

## §104 Product analytics and error tracking

**Due at:** the first deployment someone depends on earns error tracking; the first
question "do people use this?" that the owner actually asks earns product analytics.

- Error tracking captures unhandled errors with their request id (§67), scrubs personal
  data and secrets before sending (§27), and alerts someone on a **new** error, not on
  every repeat. The provider sits behind the logging boundary; a free tier is enough until
  measurement says otherwise.
- Analytics events are a contract: a listed set of event names with their meaning, kept
  in the project's documentation, sent from one place (`platform/telemetry/` or the app's
  `infrastructure/`), never from scattered components (§13, §49).
- Analytics never carries personal data or secrets and respects consent where the law or
  the owner requires it; it is listed in `docs/privacy.md` (§80). Measurement is added
  for a question the owner has, never "to have data later" (§22).
