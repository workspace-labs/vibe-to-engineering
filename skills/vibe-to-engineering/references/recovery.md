# Recovery

The backup and checkpoint system. Section 1 is the contract: what any implementation must guarantee, whatever the operating system or language. Section 2 is the store format, so different implementations can share one store. Section 3 is the bundled implementation, `scripts/checkpoint.py`. Section 4 covers the differences between platforms. Section 5 is how to investigate a break with it.

## Contents

1. The recovery contract
2. Store format
3. The bundled tool: scripts/checkpoint.py
4. Platforms
5. Investigating a break

## 1. The recovery contract

Every implementation of the checkpoint tool must guarantee all of these. The conformance tests in the skill's source repository (`tests/test_checkpoint.py`) check each one.

| # | Guarantee |
|---|---|
| G1 | **Complete.** A checkpoint holds every file of the project that git would not ignore — tracked or not, committed or not — byte for byte, with symbolic links and the executable bit, under the names the files have on disk. In a project without git, it holds everything except the default exclusions (section 2) and whatever the project's own `.gitignore` files exclude. |
| G2 | **Hands off.** Creating, verifying, listing, comparing and extracting checkpoints write nothing in the project outside `.vibe-to-engineering/`. The project's own git repository is only ever read: its commits, branches, index and configuration never change. |
| G3 | **Permanent labels.** A label names one checkpoint forever; creating it again is refused. |
| G4 | **Proven restorable.** `verify` extracts the checkpoint into an empty temporary folder and confirms, by hashing the raw bytes, that every file comes back identical. |
| G5 | **Honest comparison.** `diff` lists every added, deleted, modified and moved file between two states, recognizing moves. |
| G6 | **Safe restore.** `restore` changes nothing without `--apply`. With it, it first saves the current state as a new checkpoint, never touches files outside the checkpoints' scope (ignored or excluded files), and afterwards confirms that the project matches the checkpoint, reporting any difference. |
| G7 | **Self-contained.** Everything lives in `<project>/.vibe-to-engineering/`, which excludes itself from the project's git and from every checkpoint. |
| G8 | **Fail closed.** Any error stops the command with a non-zero exit code and a message, and the protocol then stops. |
| G9 | **Read-only tree.** `tree --current` writes nothing anywhere in the project. |
| G10 | **Ignored files are watched, not saved.** Files git ignores (dependencies, build output, but also local databases and `.env` files) are not in checkpoints. Each checkpoint records which ignored files and folders existed, and `diff` and `restore` report any that have disappeared since — so a phase that moved one by mistake is caught, and nobody believes a restore brought it back. |

## 2. Store format

Every implementation must read and write exactly this, so tools on different platforms can share one store.

- **Location:** `<project>/.vibe-to-engineering/checkpoints.git` — a bare git repository, separate from the project's own.
- **Self-exclusion:** `<project>/.vibe-to-engineering/.gitignore` holds the single line `*`.
- **Store configuration:** `core.autocrlf=false`, `core.safecrlf=false`, `core.longpaths=true`.
- **`info/attributes`** holds `* -text -filter -ident -working-tree-encoding`. It outranks the project's own `.gitattributes`, so no line-ending conversion or filter ever changes a file's bytes on the way in or out.
- **`info/exclude`** holds `/.vibe-to-engineering/` and, for projects without git, the default exclusions: `node_modules/`, `bower_components/`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.tox/`, `.gradle/`, `.next/`, `.nuxt/`, `.parcel-cache/`, `.turbo/`, `.DS_Store`, `Thumbs.db`.
- **Is it a git project?** Yes when the project folder is inside a git work tree and that repository does not ignore the folder itself.
- **Which files:** in a git project, the project's own view — `git ls-files --cached --others --exclude-standard`, run in the project folder read-only (`GIT_OPTIONAL_LOCKS=0`), with each path spelled the way it is on disk (on a case-insensitive file system git may report the case a file had when it was added). Otherwise, the store's view — `git --git-dir=<store> --work-tree=<project> ls-files --others --exclude-standard`. In both cases paths under `.vibe-to-engineering/` are dropped, and nested repositories (listed as folders) are skipped and reported.
- **Snapshot:** those paths are added to a temporary index file (`update-index --add --remove`) and written as a tree (`write-tree`). The project's own index is never used.
- **Checkpoint:** a commit of that tree (`commit-tree --no-gpg-sign`, author and committer `vibe-to-engineering <checkpoint@vibe-to-engineering.invalid>`, no parent) referenced by `refs/checkpoints/<label>`, which is created only if it does not exist yet. Its message is `vibe-to-engineering checkpoint: <label>`, a blank line, then `ignored-by-git: ` followed by a JSON list of the ignored entries at that moment — `ls-files --others --ignored --exclude-standard --directory` in the same view as above, a wholly ignored folder listed once with a trailing `/`, the state folder left out.
- **Labels:** lowercase letters, digits, `.`, `_` and `-`; starting with a letter or digit; at most 64 characters; no `..`; not ending in `.` or `.lock`.
- **Current state:** `diff` and `restore` snapshot the current files the same way, without creating a ref.

## 3. The bundled tool: scripts/checkpoint.py

Python 3.8 or newer, standard library only, plus git on the PATH. It calls git with argument lists, never through a shell, so the same file runs on every platform.

```
python3 <skill>/scripts/checkpoint.py --project <project> <command> …      (Windows: py -3 …)
```

| Command | Does | Writes |
|---|---|---|
| `create <label>` | snapshot the current files as checkpoint `<label>` | the store |
| `verify <label>` | extract into a temporary folder and confirm every file comes back identical | nothing in the project |
| `list` | list the checkpoints with time, file count and commit | nothing |
| `diff <from> [<to>] [--patch] [--path <p>]…` | changes from `<from>` to `<to>` (default: the current files); moves shown as `R`; ignored files that disappeared listed as `gone` | the store only (unreferenced objects) |
| `tree [<label>]`, `tree --current` `[--depth N]` | tree view of a checkpoint, or of the current files | nothing |
| `extract <label> <folder>` | write a checkpoint's files into a new or empty folder outside the project | only that folder |
| `restore <label> [--apply]` | without `--apply`: what would change. With it: save the current state as `pre-restore-<time>`, delete the files added since the checkpoint, write the checkpoint's files, confirm the result | the project — after approval only |

Exit codes: `0` success; `1` error; `2` usage; `3` `diff` found differences.

Comparing with the current files stores their changed contents in the store as unreferenced objects. On a large or binary-heavy project, `git --git-dir=<project>/.vibe-to-engineering/checkpoints.git gc` reclaims that space; every checkpoint is kept, because each is named by a ref.

Labels used by the protocol: `00-baseline`, `00-baseline-checked`, `01-phase-1`, `02-phase-2` …, `failed-02-phase-2`, `NN-final`, plus the tool's own `pre-restore-<time>`. A label can never be reused; add a suffix for a second attempt (`failed-02-phase-2-b`).

The tool refuses to treat a home folder or a file-system root as a project, and refuses to extract into the project itself.

## 4. Platforms

The contract and the store format are the same everywhere; only execution differs, and the tool keeps those differences in its "platform helpers" section.

- **macOS — validated in 0.1.0** (Python 3.9, git 2.54). Its default file system ignores letter case; the tool records on-disk names and a restore deletes before it writes, so a rename that only changes case is compared and restored correctly (covered by a conformance test).
- **Linux — expected to work unchanged** (it takes the same code paths as macOS); not yet validated.
- **Windows — designed for, not yet validated.** Needs Python 3 (`py -3`) and Git for Windows. Known differences: read-only files must be made writable before they can be deleted (handled); a file another program holds open cannot be replaced — the restore stops and names it, the saved `pre-restore` checkpoint keeps everything, and the restore can be run again after that program is closed; symbolic links need Developer Mode, otherwise git keeps them as plain files; there is no executable bit; long paths rely on `core.longpaths`.
- **Another implementation** (for example a PowerShell script for machines without Python) must follow sections 1 and 2 exactly and pass the same conformance tests.

To validate a platform, run `python3 -m unittest discover -s tests -v` from the skill's source repository on it.

## 5. Investigating a break

1. `create failed-NN-phase-n` — keep the broken state before anything else.
2. `diff <last-good> failed-NN-phase-n` — every change since the last known-good checkpoint. Add `--patch --path <file>` to see the lines of one file.
3. Re-run the failing check once: a failure that comes and goes is reported as such.
4. Tie the failure to specific changes. To test an idea, `extract` the last good checkpoint (or the failed one) into an empty scratch folder outside the project and try it there. If the scratch copy needs installed dependencies, point it at the project's own dependency folder; installing anything needs the human's approval.
5. Narrow it down: with many changes, apply half of them to a scratch copy of the last good checkpoint, check, and repeat on the half that fails.
6. Never undo changes in the project to investigate. Undoing is a restore, and a restore is the human's decision.
