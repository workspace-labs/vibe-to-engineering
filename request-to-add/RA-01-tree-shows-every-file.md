# RA-01 — `tree` shows every file, not only the ones a checkpoint saves

## What is missing

`checkpoint.py tree` lists only the files a checkpoint saves. Files git ignores, nested repositories and the skill's own `.vibe-to-engineering/` folder are dropped **without a word**, and the closing count covers only what is shown. Nothing in the output says the tree is partial.

The skill's rules for those files are right: never move, edit or delete them. What's missing is saying so in the tree. The owner reads the tree to judge whether the skill saw the whole project. A silent omission looks the same as an oversight.

A second, related gap: checkpoints don't save ignored files. `diff` reports one that disappeared (G10), but no checkpoint can bring it back. The skill's docs say this only indirectly ("files git ignores … are not in any checkpoint"). Nowhere does the owner see a list of which of *their* files that applies to.

## How it showed up

Project `spendly`: 18 files on disk, not counting `.git/`.

```
$ python3 checkpoint.py --project ~/vibe-test/spendly tree --current
spendly (current files)
├── static/
│   ├── app.js
│   ├── app_old.js
│   └── style.css
├── .gitignore
├── app copy.py
├── app.py
├── config.py
├── db.py
├── helpers.py
├── ideas.txt
├── README.md
├── test_app.py
└── utils.py

13 files
```

Left out, with no mention: `.env`, `expenses.db`, `exports/expenses-2026-08.csv` (all git-ignored), and `.vibe-to-engineering/` (3 files). The plan's CURRENT and TARGET trees mentioned the ignored files only because the agent added a note by hand. The template doesn't ask for one.

## Where

- `skills/vibe-to-engineering/scripts/checkpoint.py:705` → `def current_files_read_only(project):`. It calls `survey(...)`, which already returns `Found(files, ignored, nested, disk)`, and then keeps only `.files`.
- `checkpoint.py:720` → `def print_tree(title, paths, depth):`. It takes one flat list of paths.
- `checkpoint.py:750` → `def cmd_tree(project, args):`. For `tree <label>` the ignored and nested lists are already recorded in the checkpoint message (`IGNORED_MARK`, line 56; `recorded(...)`, line 591).
- `SKILL.md:83` → `- the current tree without dependency, build-output and vendored folders — \`checkpoint.py tree --current\` prints it and writes nothing;`
- `SKILL.md:240` → `Follow the outcome with the before and after trees, …`
- `assets/plan-template.html`: the overview page's trees, and the fill-in rules in its header comment.

## Added means

1. `tree --current` and `tree <label>` print every ignored path and every nested repository in the tree, where it sits, each with a mark. For example:
   ```
   ├── .env                  [ignored — never touched, not in checkpoints]
   ├── expenses.db           [ignored — never touched, not in checkpoints]
   ├── exports/              [ignored — 1 file, never touched, not in checkpoints]
   ├── vendor/lib/           [nested repository — not in checkpoints]
   ```
   An ignored folder is one line with its file count, not opened. Dependency and build-output folders (`node_modules/`, `.venv/`, `dist/`…) stay collapsed to one line, so the tree stays short.
2. The closing line counts both kinds: `13 files saved · 3 ignored (1 folder) · 0 nested repositories — not saved, never touched`.
3. `.vibe-to-engineering/` appears as one line: `.vibe-to-engineering/  [the skill's own folder]`.
4. `--saved-only` gives today's output, for the final review's tree comparison (`SKILL.md:221`), which compares saved files only.
5. `SKILL.md` INSPECT and the final report say the owner sees the full tree. The plan template's CURRENT and TARGET trees show the marked lines (or one summary line when there are many), so the plan itself lists which files the migration will never touch.
6. `tree` still writes nothing (G9). The existing test `test_tree_of_the_current_files_writes_nothing` still passes, and new tests cover:
   - ignored files and folders shown and marked, at their places in the tree;
   - a nested repository marked;
   - `tree <label>` shows the ignored and nested lists recorded in that checkpoint;
   - `--saved-only` output equals today's output byte for byte;
   - the count line.

## Ideas (not tried)

- `survey()` already has the lists, so this could be a change to `print_tree` and `cmd_tree` alone: pass `Found` in, merge the three lists, and tag each path.
- Reuse the collapse rule the tree already applies at `--depth` for ignored folders, so a huge `node_modules/` costs one line.
