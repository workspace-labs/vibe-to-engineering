# Request to add

Things vibe-to-engineering does not do yet and should. These are additions, not bugs: nothing here breaks a safety rule, but each one left the owner unable to confirm from the skill's own output that the skill had handled the whole project. Each request says what is missing, how it showed up, where in the skill it belongs, and what "added" means.

Found on 2026-09-24 while testing the skill on Linux, on the fake vibe-coded app `~/vibe-test/spendly` (installed skill = `fix/f02-store-writes-outside` @ 99e1a6a). The owner tested it by putting the project's tree **without** the skill next to its tree **with** the skill. In that comparison, files were missing from the skill's tree and there was no project-side record of the decisions.

| # | Request | Why it matters |
|---|---|---|
| [RA-01](RA-01-tree-shows-every-file.md) | `tree` shows every file, with ignored files and nested repositories marked instead of silently dropped | The owner can't tell "left alone on purpose" from "never seen" |
| [RA-02](RA-02-decision-record-in-the-project.md) | The migration leaves a short record of its structural decisions **inside the project** | Today the reasons live only in `.vibe-to-engineering/`, which git ignores and the owner may delete |

Line numbers are for `main` @ f709639; the quoted text of each line is the anchor if the numbers move (in `checkpoint.py` they move by about +14 on the F02 branch).

These are separate from `FIX-FIRST.md`. Items there come first, and nothing here should be started before the owner schedules it.
