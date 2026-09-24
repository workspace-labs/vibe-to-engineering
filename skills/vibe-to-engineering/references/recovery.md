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
| G1 | **Complete.** A checkpoint holds every file of the project that git would not ignore — tracked or not, committed or not — byte for byte, with symbolic links and the executable bit, under the names the files have on disk, each exactly once (on a disk that ignores letter case or Unicode normalization, `Ä.txt` and `ä.txt` are one file and one name). In a project without git, it holds everything except the default exclusions (section 2) and whatever the project's own `.gitignore` files exclude. The tool proves it before saving: a walk of the disk made without git must find exactly the listed files plus the ignored ones, and every saved file's bytes, link and executable bit are hashed and compared by the tool itself. A folder it cannot read, or a file git leaves out without saying so, refuses the checkpoint. **Nested repositories** (folders with their own git) are not saved: they are named on every `create`, and a checkpoint is refused while one holds uncommitted changes or untracked files. |
| G2 | **Hands off.** Creating, verifying, listing, comparing and extracting checkpoints write nothing in the project outside `.vibe-to-engineering/`. The project's own git repository is only ever read: its commits, branches, index and configuration never change. |
| G3 | **Permanent labels.** A label names one checkpoint forever; creating it again is refused. |
| G4 | **Proven restorable.** `verify` writes the checkpoint into an empty folder on the project's own disk and confirms that exactly the saved names come back — two names the disk treats as one collide there, and one goes missing — and, by hashing the raw bytes, that every file, link and executable bit is identical. |
| G5 | **Honest comparison.** `diff` lists every added, deleted, modified and moved file between two states, recognizing moves. |
| G6 | **Safe restore.** `restore` changes nothing without `--apply`. With it, in this order: it saves the current state as a new checkpoint; proves that this checkpoint and the one to restore both come back identical (G4); refuses — changing nothing in the project — if either does not, if the restore would overwrite, replace or remove anything checkpoints do not hold (an ignored or excluded file or link, a folder that still holds one, a nested repository, or a folder only reachable under another spelling), or if the project changed meanwhile; only then deletes and writes files; and afterwards confirms that the project matches the checkpoint and that everything checkpoints do not hold is still there, reporting any difference. Without `--apply` it reports the same refusal. |
| G7 | **Self-contained.** Everything lives in `<project>/.vibe-to-engineering/`, which excludes itself from the project's git and from every checkpoint. Before writing anything, the tool refuses a state folder, ignore file or store that is — or holds — a link, junction or special file, and a store that points git at another repository (`commondir`, `objects/info/alternates`). It also refuses a store it cannot read in full, and any store file that is a second name (hard link) for another file — except its own `config`, `info/attributes` and `info/exclude`, which it replaces whole. Every git command on the store runs with `core.logAllRefUpdates=false`, so git creates no missing reference log there; a reference log that already exists still receives git's appends, and the hard-link refusal is what keeps them from reaching a file outside the store. It writes its own files whole and renames them into place, never through a link or a second name for another file. |
| G8 | **Fail closed.** Any error stops the command with a non-zero exit code and a message, and the protocol then stops. |
| G9 | **Read-only tree.** `tree --current` writes nothing anywhere in the project. |
| G10 | **Ignored files are watched, not saved.** Files git ignores (dependencies, build output, but also local databases and `.env` files) are not in checkpoints. Each checkpoint records every ignored file by name — one entry per file, so losing one file from a folder that still exists is caught — and every nested repository, and `diff` and `restore` report any that have disappeared since — so a phase that moved one by mistake is caught, and nobody believes a restore brought it back. |
| G11 | **Isolated from git settings.** No hook or file-system monitor that git is configured with ever runs, and no setting from the environment or the user's configuration changes what a checkpoint holds (executable bits and links included) or makes git write anywhere else: settings given through the environment (`GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG`), templates and trace files are ignored. The project's own ignore rules still apply, including the user's global excludes file. |

## 2. Store format

Every implementation must read and write exactly this, so tools on different platforms can share one store.

- **Location:** `<project>/.vibe-to-engineering/checkpoints.git` — a bare git repository, separate from the project's own.
- **Self-exclusion:** `<project>/.vibe-to-engineering/.gitignore` holds the single line `*`.
- **Store configuration:** `core.autocrlf=false`, `core.safecrlf=false`, `core.longpaths=true`, written with `git config --file <store>/config`. The store is created with `git init --bare --template=`, so no template hooks are copied in.
- **Every git command** runs with `-c core.hooksPath=<the null device> -c core.fsmonitor=false`, which outrank every configuration file, and without the environment variables that set configuration for one command or redirect git's reads and writes (`GIT_CONFIG`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` and its keys and values, `GIT_TEMPLATE_DIR`, `GIT_TRACE*`). Commands on the store also run with `-c core.filemode=true -c core.symlinks=true`, except on Windows.
- **`info/attributes`** holds `* -text -filter -ident -working-tree-encoding`. It outranks the project's own `.gitattributes`, so no line-ending conversion or filter ever changes a file's bytes on the way in or out.
- **`info/exclude`** holds `/.vibe-to-engineering/` and, for projects without git, the default exclusions: `node_modules/`, `bower_components/`, `.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.tox/`, `.gradle/`, `.next/`, `.nuxt/`, `.parcel-cache/`, `.turbo/`, `.DS_Store`, `Thumbs.db`.
- **Is it a git project?** Yes when the project folder is inside a git work tree and that repository does not ignore the folder itself.
- **Which files:** in a git project, the project's own view — `git ls-files --cached --others --exclude-standard`, run in the project folder read-only (`GIT_OPTIONAL_LOCKS=0`). Otherwise, the store's view — `git --git-dir=<store> --work-tree=<project> ls-files --others --exclude-standard`. In both cases paths under `.vibe-to-engineering/` are dropped, and git may print no warning (it warns, and exits 0, when it cannot open a folder). Each path is spelled the way it is on disk: a name the folder does not list exactly (git may report the letter case a file had when it was added, or a precomposed form of a decomposed Unicode name) is replaced by the one directory entry that is the same file — found by the file's identity (device and inode), never by comparing spellings — and each path is kept once. Nested repositories — listed by git as folders ending in `/`, or tracked as gitlinks — are not saved.
- **Complete:** a walk of the project made without git — every regular file and link, skipping entries named `.git`, the state folder and the contents of nested repositories — must find exactly the listed files plus the ignored files (below). Any difference, or a folder the walk cannot read, refuses the snapshot. Each nested repository must report nothing in `git status --porcelain --untracked-files=all`, run inside it.
- **Snapshot:** those paths are added to a temporary index file (`update-index --add`) and written as a tree (`write-tree`). The project's own index is never used. The tool then reads the tree back and compares it with the files on disk itself — the same names; for each, the blob id of its bytes (or link target) computed without git, and its mode — and refuses the snapshot on any difference.
- **Checkpoint:** a commit of that tree (`commit-tree --no-gpg-sign`, author and committer `vibe-to-engineering <checkpoint@vibe-to-engineering.invalid>`, no parent) referenced by `refs/checkpoints/<label>`, which is created only if it does not exist yet. Its message is `vibe-to-engineering checkpoint: <label>`, a blank line, then `ignored-by-git: ` followed by a JSON list of the ignored entries at that moment — `ls-files --others --ignored --exclude-standard` in the same view as above: every ignored file listed on its own, an ignored nested repository once with a trailing `/`, the state folder left out — and a line `nested-repositories: ` followed by a JSON list of the nested repositories it does not save, each with a trailing `/`. A checkpoint without one of these lines is read as recording nothing on it.
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
| `verify <label>` | write the checkpoint into an empty temporary folder on the project's disk and confirm that exactly its names come back, every file identical | a temporary folder inside `.vibe-to-engineering/`, removed afterwards |
| `list` | list the checkpoints with time, file count and commit | nothing |
| `diff <from> [<to>] [--patch] [--path <p>]…` | changes from `<from>` to `<to>` (default: the current files); moves shown as `R`; ignored files and nested repositories that disappeared listed as `gone` | the store only (unreferenced objects) |
| `tree [<label>]`, `tree --current` `[--depth N]` | tree view of a checkpoint, or of the current files | nothing |
| `extract <label> <folder>` | write a checkpoint's files into a new or empty folder outside the project | only that folder |
| `restore <label> [--apply]` | without `--apply`: what would change, or why it would be refused. With it: save the current state as `pre-restore-<time>`, prove it and `<label>` come back identical, refuse if anything checkpoints do not hold is in the way, then delete the files added since the checkpoint, write the checkpoint's files and confirm the result (G6) | the project — after approval only |

Exit codes: `0` success; `1` error; `2` usage; `3` `diff` found differences.

One case a restore cannot see in advance: it brings back older ignore rules under which a file that is ignored now would be in scope, and the checkpoint does not hold that file. The restore leaves the file untouched, its own check afterwards reports the difference as "did not complete", and the state from before is in the pre-restore checkpoint.

Comparing with the current files stores their changed contents in the store as unreferenced objects. On a large or binary-heavy project, `git --git-dir=<project>/.vibe-to-engineering/checkpoints.git gc` reclaims that space; every checkpoint is kept, because each is named by a ref.

Labels used by the protocol: `00-baseline`, `00-baseline-checked`, `01-phase-1`, `02-phase-2` …, `failed-02-phase-2`, `NN-final`, plus the tool's own `pre-restore-<time>`. A label can never be reused; add a suffix for a second attempt (`failed-02-phase-2-b`).

The tool refuses to treat a home folder or a file-system root as a project, and refuses to extract into the project itself. It also refuses a state folder or store it cannot show to be isolated (G7), a folder it cannot read (G1) and a nested repository holding unsaved work (G1) — each with a message naming what to look at.

## 4. Platforms

The contract and the store format are the same everywhere; only execution differs, and the tool keeps those differences in its "platform helpers" section.

- **macOS — validated in 0.1.0** (Python 3.9, git 2.54). Its default file system ignores letter case and Unicode normalization; the tool matches every name git reports to the on-disk entry that is the same file, and a restore deletes before it writes, so a rename that only changes letter case — `Utils.js` → `utils.js`, `Ä.txt` → `ä.txt`, or a folder — is saved once, compared and restored correctly, and a name the disk keeps decomposed keeps its exact bytes (covered by conformance tests).
- **Linux — expected to work unchanged** (it takes the same code paths as macOS); not yet validated.
- **Windows — designed for, not yet validated.** Needs Python 3 (`py -3`) and Git for Windows. Known differences: read-only files must be made writable before they can be deleted (handled); a file another program holds open cannot be replaced — the restore stops and names it, the saved `pre-restore` checkpoint keeps everything, and the restore can be run again after that program is closed; symbolic links need Developer Mode, otherwise git keeps them as plain files — and `verify` then accepts a link that comes back as a plain file, which G1 does not allow: this has to be settled before Windows is validated; there is no executable bit; junctions and other reparse points count as links for G7; long paths rely on `core.longpaths`.
- **Another implementation** (for example a PowerShell script for machines without Python) must follow sections 1 and 2 exactly and pass the same conformance tests.

To validate a platform, run `python3 -m unittest discover -s tests -v` from the skill's source repository on it.

## 5. Investigating a break

1. `create failed-NN-phase-n` — keep the broken state before anything else.
2. `diff <last-good> failed-NN-phase-n` — every change since the last known-good checkpoint. Add `--patch --path <file>` to see the lines of one file.
3. Re-run the failing check once: a failure that comes and goes is reported as such.
4. Tie the failure to specific changes. To test an idea, `extract` the last good checkpoint (or the failed one) into an empty scratch folder outside the project and try it there. If the scratch copy needs installed dependencies, point it at the project's own dependency folder; installing anything needs the human's approval.
5. Narrow it down: with many changes, apply half of them to a scratch copy of the last good checkpoint, check, and repeat on the half that fails.
6. Never undo changes in the project to investigate. Undoing is a restore, and a restore is the human's decision.
