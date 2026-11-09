# Review and completion

Where a project prescribes its own finding format, severity scale or delivery note, fill that format with the substance below.

## Contents

- §29 Engineering findings
- §52 Review standard
- §54 Zero-behavior-change refactor rule
- §57 Engineering debt policy
- §31 Definition of done
- §32 Engineering self-check
- §60 Handoff quality

## §29 Engineering findings

Every engineering finding explains:

- the evidence;
- the affected area;
- the consequence;
- why it matters;
- the recommended correction;
- the risk of that correction.

Classify each finding as exactly one of:

| Class | Use for |
|---|---|
| BUG | incorrect behavior, or a real correctness or safety risk |
| ARCHITECTURAL DEBT | a wrong or missing boundary, ownership or dependency direction |
| MAINTAINABILITY ISSUE | code that works but is harder to understand or change than it should be |
| CLEANUP | dead, duplicated or untidy material with no structural consequence |
| OPTIONAL IMPROVEMENT | worthwhile, but not needed now |

Do not call every imperfection a defect, and do not inflate severity to justify restructuring.

## §52 Review standard

Review is not only "do the tests pass?". It also asks:

- Is the behavior correct?
- Is the implementation in the correct architectural location?
- Did dependency direction worsen?
- Was duplicated logic introduced?
- Did state ownership become less clear?
- Did persistence or platform concerns leak?
- Do the tests prove the contract rather than merely the implementation?
- Did the change introduce hidden technical debt?
- Did scope expand without approval?

## §54 Zero-behavior-change refactor rule

When a task is explicitly structural, the expected product behavior change is NONE.

- **Before refactoring:** establish a baseline, capture tests, identify the protected behavior.
- **After refactoring:** run the same verification, compare outputs where practical, and review independently.

Never hide feature changes inside structural commits.

## §57 Engineering debt policy

Technical debt may be accepted intentionally. Accepted debt is named, its consequence explained, its severity classified, and the point at which it should be revisited recorded. Never pretend accepted debt is solved.

Do not block every feature on low-value cleanup. Prioritize debt that affects correctness, safety, future architecture, maintainability or upcoming roadmap pressure.

## §31 Definition of done

For substantial work, reconcile the [project coverage record (§87)](coverage-and-evidence.md#87-project-coverage-and-approved-documents) with the actual artifacts and results. Unresolved duties remain visible. Preserve the approved Plan’s human-only checked status.

Working code alone is not done. For substantial work, done means the relevant combination of:

- behavior is correct;
- responsibility has the correct architectural home;
- state ownership is understandable;
- tests exist at the appropriate level;
- unnecessary coupling was not introduced;
- accidental duplication was not introduced;
- the repository remains understandable;
- documentation is updated where necessary;
- settings added or changed in code have their names, purposes and value sources in `.env.example` and README Settings, following [§85](team-and-lifecycle.md#85-the-ten-year-handover);
- Git state is intentional;
- the build and release path remains valid;
- review is complete;
- the Human Gate is satisfied where required.

The exact checklist is proportional to the task.

## §32 Engineering self-check

Before finishing substantial software work, answer:

1. Did I put this code where its responsibility belongs?
2. Did I increase coupling unnecessarily?
3. Did I duplicate an existing rule?
4. Did I hide product or domain logic inside UI code?
5. Did I leak storage or platform concerns?
6. Is state ownership understandable?
7. Can another engineer find this feature?
8. Can they find its tests?
9. Is the repository still understandable?
10. Is Git a truthful representation of the product?
11. Did I create technical debt merely to finish faster?
12. Did I over-engineer something simple?
13. Would I be comfortable maintaining this structure one year from now?

If a significant answer is concerning, do not silently ignore it: report it and propose the smallest appropriate engineering correction.

## §60 Handoff quality

At the end of substantial work, leave enough evidence for another engineer or reviewer to verify it. A good handoff states:

- the objective;
- the files changed;
- the architectural impact;
- the behavior impact;
- the tests run;
- the results;
- known limitations;
- unresolved risks;
- the exact next gate.

Do not hide uncertainty.
