# Migration plan

How to design the target architecture, cut the phases, prove behavior is preserved, and write the plan the human approves.

## Contents

1. Designing the target architecture
2. Cutting phases
3. Verification: proving behavior is preserved
4. The plan document
5. Filling the template and rendering the PDF
6. Revising an approved plan

## 1. Designing the target architecture

Start from what the project is, never from a template.

- **Inventory first.** List the responsibilities you found — features, domain rules, integrations, persistence, UI, configuration, wiring — and where each one lives now.
- **Choose the organizing principle from evidence.** Group by feature when changes mostly stay inside one feature (history shows a feature's files changing together); group by technical responsibility when the project is small or has a single feature. Use one principle consistently, mixing only where the stack dictates (for example a framework's routes folder).
- **Shared code** is code that two or more features use today. Code one feature uses lives with that feature.
- **The composition root** — the entry file — wires modules together and holds no feature logic.
- **Respect conventions and contracts.** Paths the framework or tools require stay where they must. External contracts keep their names and locations, or get a compatibility path that the plan names explicitly.
- **Proportion.** Every folder in the target tree has a one-line responsibility and at least one file that belongs there today. No folders for future use, no layers that only pass calls through, no interfaces with a single implementation unless a boundary or testing need is named.
- **Traceability.** Every structural change cites the finding it fixes. A change without a finding is not part of the plan.
- **Minimal movement.** A file that is already in a sensible place stays there. Rename only when a name misleads (C8), never for taste.

Before writing the plan, check the design against `engineering-standard.md`, above all C16 (overengineering).

## 2. Cutting phases

- **One objective per phase,** small enough that a failure can be traced to it and a reviewer can read its diff in one sitting. Split large moves by area.
- **The application works at the end of every phase,** and every phase is a safe place to stop for good.
- **Typical order:** safety net (only if needed) → pure moves and renames → splitting oversized modules → fixing boundaries and dependency direction → removing duplication → removing remnants and temporary shims → updating documentation that describes the structure. Leave out what the project does not need.
- **Keep moves apart from logic edits.** A move phase moves files and updates the references to them, nothing else, so the diff recognizes every move. Splitting or rewriting code comes in its own phase.
- **Tests travel with their code:** a phase that moves code updates the tests' paths and imports in the same phase.
- **A rename that changes only letter case** (`Utils.js` → `utils.js`) is its own small step: on case-insensitive file systems (the macOS and Windows defaults) it is easy to get wrong. Prefer renames that change more than case.
- **Temporary compatibility shims** (for example a re-export left at an old path) only where an external contract or a large set of importers needs one. Each shim has a phase that removes it, or is declared permanent because a contract requires it.
- **No dependency changes.** If a finding can only be fixed by adding, removing or upgrading a dependency, list it in the plan as out of scope; the human decides about it separately.
- **Move files by name.** Never move with wildcards or whole-folder moves that could also carry files git ignores (local databases, `.env` files, build output): those are not in any checkpoint.

## 3. Verification: proving behavior is preserved

List the exact commands that run at the baseline and after every phase:

- **Build, type check, lint** — only the ones the project already uses.
- **Tests** — the project's own test command; record how many tests it finds.
- **A smoke run of the real entry point**, chosen by project type:
  - command-line tool or script: run it on a sample input and compare the output with the baseline's;
  - web server or API: start it, call the main routes, compare status codes and key content, stop it;
  - web front end: build it, load the main page in a headless browser, check the key content renders without errors;
  - library: from a small throwaway script outside the project, import the public entry points and call one function of each;
  - desktop or mobile app: build it, launch it, capture the main screen and compare it with the baseline capture.

  Stop anything the smoke run starts.

**Checks stay local.** A check never installs or updates dependencies, deploys, publishes, migrates or seeds a database, or sends anything anywhere. If the project's own build or test command does any of that (an `npm ci` inside `build`, for example), say so in the plan and propose a local alternative; if dependencies are missing, the baseline stops and the human decides.

**Pass means:** every check that passed at the baseline passes; the number of tests found is not lower (moved tests can silently fall outside the runner's file pattern); the smoke results match the baseline.

**Thin safety net?** If the tests do not cover the behavior the migration touches, the plan starts with a safety-net phase: characterization checks that record today's behavior (outputs for sample inputs, responses of key routes, rendered text) and compare against it after every phase. Keep them in `.vibe-to-engineering/checks/` unless the human wants them added to the project's own tests.

## 4. The plan document

The plan is written for the project's owner, who may not be a developer: plain language first, technical detail after. Its sections, in this order (the template has them all):

1. **Summary for the owner** — where the project is now; what is wrong (the Material findings in plain words); the proposed architecture in one paragraph; how it gets there (one line per phase); what approving authorizes (the backup and Phase 1, nothing else).
2. **CURRENT → MIGRATION → TARGET** — one landscape page: the current tree (trimmed), the phases as numbered steps, the target tree.
3. **Findings** — ID, severity, criterion, evidence, impact. Minor findings too, marked as not acted on.
4. **Target architecture** — the target tree with a one-line responsibility for each folder, and every major decision with its reason and the simpler alternative rejected.
5. **Migration phases** — a summary table, then for each phase: objective, findings fixed, changes (old path → new path; what is split into what), files in scope, expected tree afterwards, verification, risks.
6. **Verification and recovery** — the checks and what a pass means; how the backup and checkpoints work; what happens on a failure; that a restore needs approval.
7. **What will not change** — the behavior and external contracts that stay as they are; what is out of scope (features, bug fixes, dependencies, data).
8. **Risks** — each with likelihood, impact and mitigation.
9. **Approval** — plan version and date, what approval authorizes, how to approve.

Trees are plain text in the checkpoint tool's tree format, trimmed to the depth that shows the change — at most about 30 lines per tree on the overview page (`checkpoint.py tree --depth 2` shortens one). The page never hides a line that does not fit; it spills visibly, which is one more reason to look at the PDF. In the current tree, mark what moves or disappears (`→ moves`, `✗ removed`); in the target tree, mark what is new (`+ new`).

## 5. Filling the template and rendering the PDF

1. Copy `<skill>/assets/plan-template.html` to `<project>/.vibe-to-engineering/Engineering-Migration-Plan.html`.
2. Replace every `{{PLACEHOLDER}}`. Repeat the rows and blocks marked "repeat" as often as needed and delete unused ones. Escape `&`, `<` and `>` in inserted text. Text that really contains two braces is written `&#123;&#123;`.
3. Keep the file static and self-contained: no scripts or event handlers, and no external stylesheets, fonts or images. The renderer refuses leftover placeholders, scripts and external resources, and blocks every network lookup while it prints.
4. Render: `python3 <skill>/scripts/render_pdf.py <html> <pdf>`. It looks for Chrome, Chromium, Edge or Brave, including browsers downloaded by Playwright; set `V2E_BROWSER` to a browser's path to choose one. It prints under a content security policy — the browser runs no script and loads nothing but images written into the plan — and refuses any `<meta>` line besides the template's two.
5. Look at the PDF before reporting it.

## 6. Revising an approved plan

A revision gets a new version number in the plan, a new PDF, a new fingerprint and a new approval. Record in the ledger what changed and why. Completed phases stay completed; the revision covers what remains.
