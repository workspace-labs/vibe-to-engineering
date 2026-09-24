# RA-08 — the plan shows every file, before and after

## What is missing

The plan lists only the files each phase changes (per-phase "Changes" tables), and trees that show names without jobs. Nowhere does it list **every** file in the project, the unchanged and ignored ones included, with what the file holds today and what it will hold afterwards. That's the one view that lets the owner confirm the skill accounted for the whole project, not just the parts it chose to touch.

## How it showed up

After plan v1 was written, the owner asked three times, in different words, to see "the tree with the skill and without", then "what will be in each file and what is the difference". The plan had the information spread across findings, decisions and four phase tables, but no single view. The agent had to build one by hand, a localhost page with a before/after table of every file and a "who owns each job" table, before the owner could check the result.

## Where

- `assets/plan-template.html`: the overview page (CURRENT → MIGRATION → TARGET) and section 2, Target architecture.
- `references/migration-plan.md:62-76`: section 4, the plan document's list of sections.
- `SKILL.md:240`: the final report's "before and after trees".

## Added means

1. A new plan section, **"Every file: before → after"**. One row per file in the project (with RA-01, ignored files and nested repositories too, marked):
   - path;
   - change (same · edited · moved → new path · split → parts · removed · new · ignored, never touched);
   - what it holds today, in one line;
   - what it holds after, in one line.
   Dependency and build-output folders are one row each.
2. A short **"Who owns each job"** table: each responsibility (database access, settings, routes, UI, tests…) with the file or files that own it before and after. Two owners before and one after is the migration's point, in one glance.
3. The final report (`SKILL.md:240`) repeats both tables as they actually came out, so the owner can compare them with the plan line by line.
4. For large projects the table groups rows by folder and may collapse a folder whose files all stay the same into one row ("`src/ui/` — 42 files, unchanged").
5. A protocol test checks that the template and `migration-plan.md` require both tables.
