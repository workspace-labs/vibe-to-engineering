# Engineering standard

How vibe-to-engineering judges an existing project's structure. Use it in DIAGNOSE, to check your own target design, and again in the FINAL REVIEW.

## Contents

1. How to judge
2. Context before criteria: type, stack, size
3. The criteria (C1–C16)
4. Severity and the verdict rule
5. Where vibe-coded structure usually shows
6. What is never a finding
7. Precedence

## 1. How to judge

- **Evidence or no finding.** Every finding names files and gives something a second reviewer can re-check: line counts or line ranges, import statements, the two locations of a duplicate, the list of files one change touches. An impression is not evidence.
- **Judge fitness, not resemblance.** The question is whether this structure makes the project's typical changes cheap, safe and easy to find — not whether it looks like a template you like. No layout is correct in general.
- **Proportion.** Structure must be earned by the project's real size and responsibilities. More folders, layers or abstractions are not more engineering; often the right answer is fewer.
- **Conventions first.** The stack's and framework's conventions (where routes, pages, migrations, configuration files or packages must live) outrank generic preferences.
- **Structural means structural.** A structural problem is one whose fix is moving, splitting, grouping, re-bounding or de-duplicating code. Bugs, style, performance, security flaws and missing features are reported separately and never justify a migration by themselves.

## 2. Context before criteria

Record these before judging anything; read every criterion in their light.

- **Project type:** web front end, web application with a backend, API service, command-line tool, library or package, desktop app, mobile app, game, data or machine-learning pipeline, collection of scripts, monorepo.
- **Stack and frameworks**, with the conventions they impose on the layout.
- **Runtime and deployment:** how many runtimes or deployable units there are (browser, server, worker, a desktop app's main and renderer processes) and how it is shipped.
- **Size:** source files, lines, the largest files, the number of distinct features or responsibilities, contributors and change frequency (from history, if there is any).

Size orientation — the numbers orient, the responsibilities decide:

| Size | Typical shape | Right structure |
|---|---|---|
| Small | one main job, roughly under 20 source files, one runtime | Flat or one level deep. A single well-organized file can be correct. Findings must show real harm. |
| Medium | several features, roughly 20–150 source files | Grouped by feature or by clear responsibility; one consistent place for tests; configuration read in one place. |
| Large | many features, several runtimes or deployables, several contributors, roughly over 150 source files | Explicit boundaries between runtimes and features, one dependency direction, shared contracts in one owned place. |

## 3. The criteria

Each criterion gives what good looks like, the evidence of a problem, what is not a problem, and how to check.

### C1 Separation of concerns

- **Good:** each file or module does one kind of work — presentation, domain rules, data access, integration with outside systems, configuration, or wiring.
- **Problem evidence:** one file mixing three or more kinds of work (for example rendering, SQL or HTTP calls, business rules and configuration constants), shown with line ranges.
- **Not a problem:** a small script where one file is simplest; framework units designed to combine concerns (single-file components; a route module the framework expects to hold its data loading and its view).
- **Check:** for the largest and most-imported files, list the kinds of work each one does, with line ranges.

### C2 Responsibility and feature ownership

- **Good:** every feature and responsibility has one obvious home, and every important piece of state has one owner.
- **Problem evidence:** one feature's logic spread across unrelated files or folders (list the files a single change to it must touch); two modules each acting as the owner of the same responsibility or state.
- **Not a problem:** a consistent layered split in which each layer holds its own part of every feature.
- **Check:** pick two or three real features and list every file you would have to touch to change each. With git history, see which files change together.

### C3 Frontend/backend boundaries (when both exist)

- **Good:** client and server code are separated by a clear rule; the client never reaches server internals, secrets or the database; shared data shapes live in one deliberate place.
- **Problem evidence:** server-only code (database drivers, secrets, filesystem access) reachable from client code; client and server files interleaved with no rule; the same data shape defined separately on each side and already different.
- **Not a problem:** frameworks that deliberately place client and server code together and enforce the boundary themselves.
- **Check:** follow the imports from the client entry points; find where database and secret access happens.

### C4 API boundaries (when there is an API)

- **Good:** handlers are thin (read the request, call the logic, respond); request and response shapes are defined once; every route can be found from one place.
- **Problem evidence:** handlers holding business rules and queries; endpoints defined in scattered places with no way to list them; the same validation written differently in several handlers.
- **Not a problem:** a small API with one routes file.
- **Check:** list the routes and where each one is defined; read two handlers end to end.

### C5 Domain and business logic placement

- **Good:** product rules (calculations, validations, state changes, permissions) live in code that does not depend on UI, transport or storage details, where practical.
- **Problem evidence:** the same rule implemented in the UI and again on the server; calculations inside templates, click handlers or SQL strings; rules that cannot run without a browser or a database.
- **Not a problem:** a thin create-read-update-delete application with no real rules; logic in the place the framework intends for it.
- **Check:** find the three or four most important rules of the product and note where each one lives.

### C6 Dependency direction

- **Good:** dependencies point from the changeable outside (UI, transport, frameworks, input and output) toward the stable inside (domain rules, shared contracts). No cycles between modules.
- **Problem evidence:** domain or shared code importing UI or framework-specific code; import cycles (name every module in the cycle); a shared or "utils" module importing feature code.
- **Not a problem:** the composition root — the entry file that wires the application together — importing everything. That is its job.
- **Check:** read the import statements; sketch the dependencies between top-level folders; list every cycle.

### C7 File and folder responsibility

- **Good:** every folder and file name says what it holds, and the contents match the name.
- **Problem evidence:** grab-bag folders (`utils`, `helpers`, `misc`, `common`, `stuff`) holding business logic or unrelated code (list what is inside); folders whose names no longer describe their contents; dead or obsolete structure — files nothing references, backup copies (`app-old.js`, `copy of…`, `*.bak`, `final2`), abandoned experiments inside the source tree.
- **Not a problem:** a small, cohesive helpers module.
- **Check:** compare folder contents with folder names; search for references to a suspected dead file before calling it dead.

### C8 Naming and discoverability

- **Good:** one naming convention for each kind of file; a newcomer can guess where something lives.
- **Problem evidence:** several conventions in the same layer (`UserService.js`, `user_helper.js`, `usersMgr.JS`); misleading names; two files with the same name doing different things.
- **Not a problem:** names a language or framework requires (`__init__.py`, `page.tsx`, `mod.rs`).
- **Check:** compare the names inside each folder; try to find three features by their names alone.

### C9 Configuration boundaries

- **Good:** environment-specific values are read in one place and passed in; secrets never live in the source.
- **Problem evidence:** the same URL, key, port or path hard-coded in several files (give the count); environment variables read ad hoc throughout the code; secrets committed to the repository.
- **Not a problem:** true constants; configuration files at the location a tool requires.
- **Check:** search for literals such as URLs, ports and keys, and for every place the environment is read.
- A committed secret is a security finding: report it at once, in plain words. Moving it is not a silent migration step — the secret needs rotating, and that is the human's decision.

### C10 Test organization

- **Good:** the important behavior has automated tests; the test runner actually finds them; tests follow one consistent placement (beside the code, or in a tests tree that mirrors it); tests exercise stable interfaces.
- **Problem evidence:** no automated tests in a non-trivial project; tests kept as one-off scripts; test files the runner's pattern does not match, so they silently never run; tests that reach into internals so that any move breaks them.
- **Not a problem:** a small project with a few focused tests.
- **Check:** find the test command in the manifests and its file pattern; list the test files and whether the pattern matches them.
- Missing or unreliable tests also weaken the migration's safety: the plan must then begin with a safety net.

### C11 Duplication

- **Good:** one source of truth for each rule, data shape and constant.
- **Problem evidence:** the same logic in two or more places, worst when the copies have already drifted apart (show both locations and the difference); data shapes defined more than once.
- **Not a problem:** incidental similarity (two short loops); duplication between deployables that are deliberately independent.
- **Check:** search for the distinctive names and literals of the important rules; compare the matches.

### C12 Oversized multi-responsibility modules

- **Good:** no "god" file that everything depends on and every change touches.
- **Problem evidence:** a file that is large for this project AND holds several unrelated responsibilities, usually with many importers or frequent changes — give its line count, its responsibilities with line ranges, how many files import it and, with history, how many commits touched it.
- **Not a problem:** a long but cohesive file (a data table, generated code, one complex algorithm). Size alone is never a finding.
- **Check:** list the largest files; for each, count its responsibilities and its importers.

### C13 Structural consistency

- **Good:** the same kind of thing is organized the same way throughout the project.
- **Problem evidence:** two patterns side by side with no rule (some features grouped by feature, others by layer); a half-finished earlier reorganization; the same kind of component built with different structures.
- **Not a problem:** a documented reorganization the project itself has planned and is carrying out.
- **Check:** compare how three features of the same kind are laid out.

### C14 Maintainability — the cost of change

- **Good:** typical changes touch few, predictable files and can be verified.
- **Problem evidence:** a concrete, typical change (taken from history or traced by hand) that needs edits in many unrelated places, or lands in areas with no way to verify it.
- **Use:** C14 turns C1–C13 into severity. It is not a separate finding without evidence of its own.

### C15 Appropriate scalability

- **Good:** the structure can absorb the project's next realistic growth — its roadmap, or the direction its history shows — without that growth spreading everywhere.
- **Problem evidence:** recent features each had to be threaded through the same god file or the same unrelated places (history shows it); the next planned feature has no sensible home.
- **Not a problem:** a small project that is not prepared for a scale it will never need.
- **Check:** see how the last few features were added.

### C16 Overengineering risk

- **Good:** every layer, abstraction and folder earns its keep.
- **Problem evidence in the current project:** layers that only pass calls through; interfaces with a single implementation and no boundary or testing reason; factories, managers or services created for appearance; deep folder nesting around a handful of files; a home-made framework inside the application. Excess structure is ad-hoc structure too, so it is a finding.
- **For your own target design:** never add any of these. Apply C16 to every folder and abstraction you propose.

## 4. Severity and the verdict rule

- **Material** — the evidence shows a real, present cost or risk: changes demonstrably spread across unrelated places; a module everything depends on mixes unrelated jobs; duplicates that have already drifted; dependency cycles or reversed dependencies that block testing or reuse; a leak across the client/server boundary; tests that never run.
- **Minor** — local or cosmetic: inconsistent names in a few files; one grab-bag helper; a long but mostly cohesive file.
- **Outside structure** — bugs, security problems, performance, missing features, style. Report them separately and plainly; never use them to justify a migration. Report security problems immediately.

**The verdict:**

- **MIGRATION RECOMMENDED** only when all four hold: there is at least one Material finding; its fix is structural; the fix can preserve the product's behavior; and the benefit clearly outweighs the migration's risk (state both).
- Otherwise **NO MIGRATION REQUIRED**. Minor findings are listed as optional notes and are not acted on.
- If a Material problem can only be fixed by changing behavior or by rewriting, say so: it is outside this skill. Plan only what restructuring can fix; if nothing remains, the verdict is NO MIGRATION REQUIRED, with that explanation.

## 5. Where vibe-coded structure usually shows

These are places to look, not verdicts. Each still needs evidence under a criterion.

- One or two giant files carrying the whole application (an HTML page with thousands of lines of inline script and style; a single main or app file holding everything).
- Copy-pasted blocks with small differences.
- Names like `final`, `new`, `old`, `v2`, `copy`, `temp`, `test123` or `backup` inside the source tree.
- Dead files, commented-out blocks, abandoned experiments.
- Configuration values and URLs repeated across files.
- Business rules inside click handlers or templates; SQL or HTTP calls inside UI code.
- No tests, or tests kept as one-off scripts.
- Several organizing styles side by side — the project grew by accretion.
- Folders whose contents no longer match their names.
- Import cycles.

## 6. What is never a finding

- Differing from any template, including your own preferences.
- Following the stack's or framework's conventions.
- A small project being flat, or having few files.
- File size alone.
- A deliberate, documented decision — unless it causes demonstrable harm; then report it, never override it.
- Generated, vendored or third-party code.
- Formatting and style preferences.
- Missing documentation alone — unless it hides ownership; then it is C2 or C8, with evidence.

## 7. Precedence

1. The human's explicit instructions for this run.
2. The project's own written rules and decisions: README, CONTRIBUTING, architecture notes, ADRs, AGENTS.md, CLAUDE.md, style guides.
3. The stack's and framework's conventions.
4. This standard.

If a project rule looks harmful, report it with evidence and let the human decide. Never override it silently.
