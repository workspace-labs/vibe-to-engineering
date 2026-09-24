# RA-03 — notice when an ignored file's contents change, not only when it disappears

> **Severity note:** this is closer to a safety fix than an addition. It sits here because it was found in the same test; the owner may move it into `FIX-FIRST.md`.

## What is missing

Checkpoints don't save files git ignores: local databases, `.env`, exports (G10). They record each one **by name only**. `diff` and `restore` then report an ignored file that is `gone`, but a change to its **contents** is invisible. So a check or a phase that overwrites, empties or corrupts the owner's database passes the architecture check with nothing reported. That file is the one thing no checkpoint can bring back.

## How it showed up

Reproduced on a throwaway git project on 2026-09-24 (installed skill 99e1a6a). `.gitignore` held `data.db` and `.env`:

```
$ checkpoint.py create 00-baseline                          # data.db holds "ROWS: 5"
$ echo "ROWS: 0  (wiped by a check)" > data.db
$ checkpoint.py diff 00-baseline
changes from 00-baseline to the current files:
  A     newcache.db
1 change: 1 added                                            # nothing about data.db
$ rm data.db
$ checkpoint.py diff 00-baseline
  …
  gone  data.db                                              # only deletion is seen
```

In the spendly test, the real `expenses.db` is ignored and is the app's default database (`DB_PATH` defaults to `expenses.db`, `app.py:22`, `db.py:4`).

## Where

- `skills/vibe-to-engineering/scripts/checkpoint.py:56` → `IGNORED_MARK = "ignored-by-git: "  # the line in a checkpoint's message that lists every ignored file it did not save`
- `checkpoint.py:579` → `def save_checkpoint(store, tree, label, found):` writes the name list.
- `checkpoint.py:600` → `def missing(before, after):` and `checkpoint.py:616` → `def gone_since(store, commit, ignored, nested):` compare names only.
- `references/recovery.md`, G10 → `**Ignored files are watched, not saved.** …`
- `SKILL.md:165` → the architecture check requires only that `` it reports no ignored file or nested repository `gone` ``.

## Added means

1. Each checkpoint also records, for every ignored file outside dependency and build-output folders, its size and a content hash. It still doesn't save the contents.
2. `diff` reports a changed one: `changed  expenses.db  (ignored — not in checkpoints, cannot be restored from here)`. `restore` reports it too, before changing anything.
3. The architecture check (`SKILL.md:165`) and the final review treat a changed ignored file like a `gone` one: it's a break, unless the plan names it (for example a cache the checks rewrite, recorded at `00-baseline-checked`).
4. Tests cover:
   - an overwritten ignored file is reported;
   - a same-size edit is reported;
   - an unchanged file is not reported;
   - files inside a dependency folder are not hashed;
   - `restore` shows the report before it changes anything.

## Ideas (not tried)

- To keep large projects fast (FIX-FIRST item 11), hash only ignored files outside the folders the tree already treats as dependency or build output, and use size + modification time as a pre-check before hashing.
- Record the hashes in the checkpoint message next to `IGNORED_MARK`, so older checkpoints (which have only names) still read correctly.
