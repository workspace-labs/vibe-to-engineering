# Request to add

Things vibe-to-engineering does not do yet and should. These are additions, not bugs: nothing here breaks a safety rule, but each one left the owner unable to confirm from the skill's own output that the skill had handled the whole project. Each request says what is missing, how it showed up, where in the skill it belongs, and what "added" means.

Found on 2026-09-24 while testing the skill on Linux, on the fake vibe-coded app `~/vibe-test/spendly` (installed skill = `fix/f02-store-writes-outside` @ 99e1a6a). The owner tested it by putting the project's tree **without** the skill next to its tree **with** the skill. In that comparison, files were missing from the skill's tree and there was no project-side record of the decisions. RA-03 to RA-08 came from a follow-up check of the skill's text and tools against the same run.

| # | Request | Why it matters |
|---|---|---|
| [RA-01](RA-01-tree-shows-every-file.md) | `tree` shows every file, with ignored files and nested repositories marked instead of silently dropped | The owner can't tell "left alone on purpose" from "never seen" |
| [RA-02](RA-02-decision-record-in-the-project.md) | The migration leaves a short record of its structural decisions **inside the project** | Today the reasons live only in `.vibe-to-engineering/`, which git ignores and the owner may delete |
| [RA-03](RA-03-notice-changed-ignored-files.md) | Notice when an ignored file's **contents** change, not only when it disappears | Proven: an overwritten ignored database is reported as nothing at all. **Closer to a safety fix, so it could move into FIX-FIRST.md** |
| [RA-04](RA-04-checks-run-on-throwaway-data.md) | Checks run on throwaway data, never the owner's | A smoke run with the app's defaults writes into the real database |
| [RA-05](RA-05-smoke-run-proves-it-reached-the-right-server.md) | A server smoke run uses a free port and proves it's talking to the server it started | Another service or a stale server answers instead, which can cause a false pass |
| [RA-06](RA-06-never-read-secret-values.md) | Report where secrets are, never their values | Values would land in the transcript, plan, ledger and evidence |
| [RA-07](RA-07-see-the-plan-with-firefox.md) | Visual check of the plan with Firefox when no Chrome-family browser works | On standard Ubuntu there's no PDF and no way to do the required look |
| [RA-08](RA-08-every-file-before-and-after.md) | The plan shows every file, before → after, and who owns each job | The one view that lets the owner confirm the whole project was accounted for |

Line numbers are for `main` @ f709639; the quoted text of each line is the anchor if the numbers move (in `checkpoint.py` they move by about +14 on the F02 branch).

These are separate from `FIX-FIRST.md`. Items there come first, and nothing here should be started before the owner schedules it.
