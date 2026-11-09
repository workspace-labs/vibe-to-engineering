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
- Templates are source, reviewed like code, and carry no secrets or more personal data
  than the message needs (§27). A link in a message is a one-time or expiring token, never
  a credential.
- Development and test never send real mail: use the provider's sandbox, a local catcher
  or a logged message. Test the sending path with a fake provider, not by mailing people.
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

- An audit record carries who, what, which object, when, and from where, written in the
  same transaction as the action so neither can exist without the other (§67).
- It is append-only: never edited, never deleted by the application, retained by the
  policy in `docs/privacy.md` (§80). It holds no secrets and no more personal data than
  the question needs (§27).
- It is separate from debug and operational logs (§67): those rotate and are for the
  engineers; the audit log is for the owner, the customer and the investigator.

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
  at once). Destroying infrastructure is a Human Gate action (§30), never automated.

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
