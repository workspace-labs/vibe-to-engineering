# RA-04 — checks must run on throwaway data, never on the owner's

## What is missing

The skill forbids *moving, editing or deleting* databases and user data (`SKILL.md:245`), and its "checks stay local" rule covers the network, installs and migrations (`SKILL.md:247`, `migration-plan.md:56`). Nothing says that **running** a check must not touch the owner's data. Yet a smoke run that starts the app with its defaults, and posts to it, writes into the real database. And under RA-03, nothing would notice.

## How it showed up

Spendly reads `DB_PATH` from the environment and defaults to `expenses.db` in the project folder (`app.py:22`, `db.py:4`). The plan's smoke run posts to `/add`, `/api/expenses` and `/delete/<id>`. Run the obvious way (`python3 app.py`), it would add and delete rows in the owner's real `expenses.db`. In this run the agent set `DB_PATH` to a temporary file and `PYTHONDONTWRITEBYTECODE=1` by its own choice. No rule asked for either.

The project's own tests happened to be safe (`test_app.py:5-6` points `DB_PATH` at a temporary folder), but the skill doesn't check that either.

## Where

- `SKILL.md:245` → `- **Scope:** only planned changes. Files git ignores, secrets, databases, user data … are never moved, edited or deleted …`
- `SKILL.md:247` → `- **Checks stay local:** a check never installs or updates dependencies, deploys, publishes, migrates a database or sends anything anywhere. …`
- `references/migration-plan.md:41-60`: section 3, Verification, and the smoke run list.
- `assets/plan-template.html`: the verification table has no column saying what data a check uses.

## Added means

1. A rule in `SKILL.md` ("Always") and in `migration-plan.md` section 3: **every check runs against throwaway data.** Before the baseline, the plan names, for each check, where the app reads and writes data and how the check redirects it: an environment variable, a temporary copy, or a test fixture. If a check can't be redirected, it isn't run; the human decides.
2. INSPECT records the data locations: database files, upload folders, export folders, and the variables or settings that choose them.
3. The plan's verification table gets a "Data it uses" column. A check that would touch the owner's data is refused at the plan stage.
4. Checks also avoid writing caches into the project where the stack allows it (for example `PYTHONDONTWRITEBYTECODE=1`), or the plan names the caches they write.
5. A protocol test checks that `SKILL.md`, `migration-plan.md` and the template carry the rule.

## Ideas (not tried)

- When the app has no way to redirect its data, run the check in a copy made with `checkpoint.py extract <label> <temp>` (plus a copy of the ignored data file), never in the project.
- With RA-03 in place, "the owner's data files are unchanged" becomes a check that can be proven after every phase.
