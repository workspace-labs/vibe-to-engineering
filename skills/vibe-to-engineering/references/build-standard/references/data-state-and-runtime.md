# Data, state and runtime

## Contents

- §11 Persistence is a boundary
- §12 Data model before high-frequency or historical features
- §13 State ownership
- §39 Data contract quality gate
- §40 Units and representation
- §41 Time model
- §42 Error and failure ownership
- §43 Migration safety
- §44 Backward compatibility
- §45 Performance without premature optimization
- §46 Concurrency and async boundaries

## §11 Persistence is a boundary

Application and domain logic should not casually know the database implementation, storage keys, file paths, serialization details or migration mechanics. Where appropriate, separate:

- data contract;
- validation;
- migration;
- persistence interface;
- backend implementation.

Design persistence so that replacing one backend with another — for example local storage, then a database, then a remote backend — happens behind an intentional boundary and does not force unrelated application or UI rewrites. Do not introduce an abstraction solely because a second backend might theoretically exist someday.

Before replacing a storage backend, inspect the current persistence contract, the real stored data shapes, existing migrations, compatibility with data already in use, and how any change from synchronous to asynchronous access would propagate through callers (§43, §44, §46).

## §12 Data model before high-frequency or historical features

Before implementing movement, telemetry, track history, replay, collaboration, event streams, background automation or time-based simulation, verify that the data model supports what the feature requires. Consider:

- stable identity;
- timestamps;
- ordering;
- history;
- versioning;
- persistence frequency;
- recovery;
- event semantics;
- current state versus historical state.

Do not force high-frequency, time-based behavior into an unsuitable snapshot model merely to finish the feature quickly. If the model is not ready, report the gap and propose the minimum foundation work first; a change to data-model semantics goes through the Human Gate.

## §13 State ownership

Every important piece of state has an understandable owner. Avoid scattering one conceptual aggregate across many unrelated local states when that makes transitions difficult to reason about. Ask:

- Who owns this state?
- Who may mutate it?
- What is derived, and what is persisted?
- What is UI-only?
- What must survive restart?
- What is historical?

Do not introduce a global state library unless the actual state architecture requires it.

## §39 Data contract quality gate

For important persisted or shared data, know explicitly:

- canonical representation;
- units;
- identity;
- timestamps;
- optional versus required fields;
- validation;
- versioning;
- migration behavior.

Display preferences must not silently change canonical storage semantics. Unit conversions happen at explicit boundaries. UI labels must not define data contracts implicitly.

## §40 Units and representation

Whenever software handles physical or measured quantities — distance, speed, depth, temperature, angle, time, currency, coordinates — define the canonical internal representation. Treat display and input units separately from canonical storage unless the architecture explicitly says otherwise. Convert at clear boundaries.

Tests verify invariance wherever changing a display preference must not change the underlying physical meaning.

## §41 Time model

Time-based systems require an explicit time model. Distinguish, where relevant:

- wall-clock time;
- simulation time;
- elapsed time;
- monotonic time;
- persisted timestamps;
- display-formatted time.

Avoid mixing formatted strings with numeric timestamps as the primary domain model. Before movement, history or replay features, establish what time means in the system.

## §42 Error and failure ownership

Error handling is not a scatter of UI messages. For each important operation, determine:

- what can fail;
- where failure is detected;
- whether the failure is recoverable;
- what data remains authoritative;
- whether partial writes are possible;
- what the user sees;
- what evidence or logging is appropriate.

Persistence and migration failures must fail safely. Do not automatically repair or destroy data unless that behavior was explicitly designed and approved.

## §43 Migration safety

Apply the triggered [recovery and compatible-data checks (§89)](coverage-and-evidence.md#89-recovery-and-compatible-data-changes) alongside the rules below.

When changing persisted data:

- inspect existing real data shapes;
- define compatibility expectations;
- preserve recovery evidence where appropriate;
- make the migration deterministic;
- test valid and malformed cases;
- test repeated launches;
- avoid destructive fallback;
- prove idempotence where required.

A successful clean install is never proof that an upgrade path is safe.

## §44 Backward compatibility

For released software, consider compatibility before changing persisted data, public APIs, package or application identity, signing identity, file formats, configuration or user workflows. Breaking compatibility must be deliberate, documented and approved.

## §45 Performance without premature optimization

Do not optimize blindly; first establish whether performance matters for the task. For performance-sensitive features:

1. measure;
2. establish a baseline;
3. identify the bottleneck;
4. change one meaningful factor;
5. measure again.

Do not sacrifice architecture or correctness for speculative optimization. Interaction-heavy systems may need real-device validation.

**Speed target. Due at:** when wait time or throughput materially matters for an important flow.
Use the project's accepted target, or propose one for the owner and record it as open until agreed.
Name what counts as completion and measure under repeatable conditions on a representative device and workload.
Compare the result with the accepted target and record a pass or fail. If existing CI can measure
the agreed conditions reliably, make the check block a failing change (§75). Otherwise run it during
release verification and record the device result.
Meeting the target removes the performance reason for a rewrite. Correctness and maintainability can still justify one.

## §46 Concurrency and async boundaries

When introducing asynchronous or concurrent behavior, reason explicitly about ordering, cancellation, stale results, retries, idempotence, race conditions, ownership and partial failure. Do not convert synchronous APIs to asynchronous ones across an entire codebase without understanding the propagation cost.

**Offline edits with later sync.** An edit is saved locally when both the edit and its
pending sync survive closing the app. It is synced when the remote system confirms the
write. Make that distinction clear to the user. Agree with the owner how to resolve competing edits.
On a disposable copy, save offline, close the app, reopen offline and check the edit
is still pending. Change the same record remotely, reconnect and verify the agreed
outcome on both sides. Retry delivery and repeat the acknowledgement. The edit must
produce just one logical write. A local-only app needs no sync work.
