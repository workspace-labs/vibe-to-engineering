# Fix first

What is still open in vibe-to-engineering 0.1.0, in the order to work on it. Each item says what is wrong, how to see it, where it is, and what "fixed" means. Take one item at a time and run the tests after each.

## Before you start

- **Run the tests** on the machine you are using, from the repository root: `python3 -m unittest discover -s tests -v` (`py -3` on Windows). Needs Python 3.8+ and git; the two PDF render tests also need a Chrome-family browser and are skipped without one. On macOS all 45 pass.
- **Never point the skill at a real project.** Copy the project to a scratch folder and use the copy.
- **Where things stand:** the independent re-review (2026-09-24) of the corrections in `502d3c5` closed F01, F04, F05, F07, F09 and F10, and reopened four: F02, F03, F06 and F08 — items 1 to 4 below. It also confirmed NEW-1 (item 5). Line numbers below are for `502d3c5`; the quoted text of each line is the anchor if the numbers move.
- **Ideas** under an item are suggestions that have not been tried.

## 1. F02 (High) — the backup store can still change files outside it

> **Status (2026-09-24): fixed, waiting for independent review.** See the CHANGELOG entry; tests `test_a_store_file_with_a_second_name_outside_is_refused_and_git_appends_to_no_file` and `test_a_store_folder_that_cannot_be_read_stops_every_command_before_a_write`. Suite run on Linux, not yet on macOS.

- **What:** two ways are left for a store command to write outside the store:
  - **A hard-linked log file.** If the store's settings turn on git's reference log and a file in its `logs/` folder is another name for an outside file, git appends to that outside file. In the re-review an outside file grew from 17 to 177 bytes during `create`.
  - **An unreadable folder hides a link.** The store check walks the store with `os.walk`, which silently skips a folder it cannot read. A `config` that is a link to an outside file goes unnoticed, and `git config --file` writes through it — even during `list`.
- **See it** (in a scratch project):
  1. `create base`; add `logAllRefUpdates = always` under `[core]` in `.vibe-to-engineering/checkpoints.git/config`; create the folder `.vibe-to-engineering/checkpoints.git/logs/refs/checkpoints/` and hard-link `second` inside it to an outside file holding `KEEP THESE BYTES`; run `create second`. It exits 0 and the outside file has grown.
  2. `create base`; replace the store's `config` with a link to an outside git config containing `autocrlf = true`; `chmod 0300` the store folder; run `list`. It exits 0 and the outside config now says `autocrlf = false`. Put the folder's permissions back afterwards.
- **Where:**
  - `skills/vibe-to-engineering/scripts/checkpoint.py:234` → `    for folder, dirs, names in os.walk(str(store)):`
  - `checkpoint.py:237` → `            if is_link(path) or not (os.path.isdir(path) or os.path.isfile(path)):`
  - `checkpoint.py:256` → `        git(["config", "--file", str(store / "config"), key, value])`
- **Fixed means:** no write into the store — git's own appends included — can reach another name for the same file, and a store the tool cannot fully read stops the command before any write. Tests for both routes check that the outside bytes are unchanged and the command refuses. The existing link, redirect, config, attribute and exclude tests still pass, and deep `refs`, object folders, `logs` and `packed-refs` are covered.
- **Ideas:** refuse any store file with more than one name (a link count above 1); switch the reference log off for store commands (`-c core.logAllRefUpdates=false`); make the store walk stop on any folder it cannot read.

## 2. F03 (High) — checking a nested repository can run a program named in the git settings

- **What:** the check that a nested repository holds no unsaved work runs `git status` inside it. When git has to re-read a file, `git status` runs any "filter" program the git settings name for it (`filter.<name>.clean`). So a program from the user's or the repository's settings can run during a checkpoint, before the refusal. This check was added by the corrections.
- **See it:** a nested repository with tracked `code.txt` holding `COMMITTED`; in the global git config, `filter.review.clean` set to a small script that writes a marker file and echoes its input; `.gitattributes` in the nested repository holding `*.txt filter=review`; change `code.txt` to `OTHERDATA` (same length) and move its modified time forward; run `create base` in the parent project. The marker file appears, then `create` refuses because the nested repository is dirty.
- **Where:**
  - `checkpoint.py:427` → `            unsaved = git(["status", "--porcelain", "-z", "--untracked-files=all"],`
  - `checkpoint.py:441` → `    check_nested(project, found.nested)`
- **Fixed means:** unsaved nested work is still found and refused, but no configured filter or other configured program runs. Reading the global ignore rules and the hook and file-system-monitor protections stay as they are. A test uses the same-length edit with a global filter and shows no marker, unchanged files and a refusal, through `create`, `diff` and `restore`.
- **Idea:** check the nested repository without `git status`: list its tracked files with `git ls-files -s` and its untracked files with `git ls-files --others --exclude-standard` (neither runs filters), hash the files in Python and compare them with the index. Treat any difference as unsaved work — a file with a filter may then count as changed, which only makes the check stricter.

## 3. F06 (High) — an ignored nested repository with unsaved work still gets a checkpoint

- **What:** a nested repository that git ignores is recorded as ignored and never checked for unsaved work, so `create` succeeds while that repository's uncommitted work is held nowhere.
- **See it:** the parent's `.gitignore` holds `module/`; `module` is a nested repository with committed `code.txt`; edit `code.txt` and add an untracked `new.txt`; run `create base` in the parent. It exits 0 with no warning, and the checkpoint records `ignored-by-git: ["module/"]` but `nested-repositories: []`.
- **Where:**
  - `checkpoint.py:410` → `        ignored.add(disk.locate(rel.rstrip(b"/"))[0] + (b"/" if rel.endswith(b"/") else b""))`
  - `checkpoint.py:411` → `    unsaved = {rel[:-1] for rel in nested | ignored if rel.endswith(b"/")}`
  - `checkpoint.py:441` → `    check_nested(project, found.nested)`
- **Fixed means:** ignored nested repositories are found, recorded and refused while they hold unsaved work, exactly like tracked and untracked ones — without starting to save ignored files such as secrets or dependencies. Do item 2 first: this repair uses its safe check. Tests: an ignored clean and an ignored dirty nested repository, a dirty tracked file and an untracked file inside one, its disappearance reported as `gone`, and a refusal that leaves the project and the nested repository unchanged.

## 4. F08 (Medium) — broken HTML can still run a script or pull a local file into the PDF

- **What:** Python's HTML reader and Chrome read some malformed markup differently, so the checks see nothing while Chrome runs code or loads a local file. Two inputs, each placed before `</body>` of a filled plan, print with exit 0:

  ```html
  <!-- hidden --!><img/src="data:,"/onerror="document.body.append('EVENT-SCRIPT-EXECUTED')"> -->
  ```

  Python reads it as a comment; Chrome runs the event handler, and `EVENT-SCRIPT-EXECUTED` appears in the PDF.

  ```html
  <style/>div{width:500px;height:100px;background-image:url(file:///ABSOLUTE/PATH/local.svg)}</style><div></div>
  ```

  Python treats `<style/>` as closed; Chrome still reads a style and loads the local file (with an absolute path to a local SVG, its text appears in the PDF). The same local image also loads from behind the malformed comment above.
- **Where:**
  - `skills/vibe-to-engineering/scripts/render_pdf.py:48` → `NESTED = re.compile(r"""<\s*(script|iframe|frame|frameset|object|embed|applet|portal|fencedframe|base|link|svg|math)\b"""`
  - `render_pdf.py:103` → `        self.in_style = False`
  - `render_pdf.py:118` → `    markup.feed(text)`
- **Fixed means:** Chrome's actual print cannot run a supplied script or event handler, load local content or show a nested document, whatever the markup. The plan template, quoted code, inline `data:` images and the network block keep working. Adding one more pattern to a blocked list does not prove that: prefer a mechanism the browser itself enforces. Tests: the three exact inputs, real prints for the script and local-file cases, and the existing quoted-code and nested-document tests. Leaving remote `srcset` addresses to the network block was accepted by the re-review.
- **Idea:** print a temporary copy of the plan that begins with a Content-Security-Policy `<meta>` tag allowing no scripts, inline styles only and `data:` images only (for example `default-src 'none'; style-src 'unsafe-inline'; img-src data:`), keeping the text checks as a first layer. Test first that the plan still prints: switching scripts off another way made the printer produce no PDF at all.

## 5. NEW-1 (Medium) — a repository git refuses to open is treated as a plain folder

- **What:** when git refuses a repository — for example "detected dubious ownership", when the folder belongs to another user — `is_git_project()` reads that as "not a git project" and silently switches to the plain-folder rules. A tracked file that matches an ignore rule is then left out of every checkpoint, and `verify` still passes. Confirmed by the re-review; it was outside F01–F10, so it needs its own go-ahead.
- **See it:** commit `tracked.log`, then add `*.log` to `.gitignore`; run `GIT_TEST_ASSUME_DIFFERENT_OWNER=1 python3 skills/vibe-to-engineering/scripts/checkpoint.py --project <that repository> create base`. It exits 0 and the checkpoint has no `tracked.log`.
- **Where:**
  - `checkpoint.py:213` → `    inside = git(["rev-parse", "--is-inside-work-tree"], cwd=project, ok=(0, 128))`
  - `checkpoint.py:214` → `    if inside.returncode != 0 or inside.stdout.strip() != b"true":`
- **Fixed means:** a genuine non-repository still uses the plain-folder rules, but any other failure to open the repository stops the command with git's own message. A test reproduces the ownership refusal and shows the tracked file is not silently dropped.

## 6. Try it on copies of real projects

The corrections refuse more than before, on purpose: `create` stops for an unreadable folder anywhere in the project (ignored folders too), any warning git prints while listing files, a nested repository with uncommitted work, and two names the tool cannot tell apart. Run `create`, `verify`, `diff` and `restore` on copies of two or three real projects and write down every refusal with its exact message. A refusal that protects nothing real is a candidate fix.

## 7. Linux and Windows

Only macOS has been tested. Run the suite on Linux and on Windows. Known Windows gaps (`skills/vibe-to-engineering/references/recovery.md`, section 4): `verify` accepts a link that comes back as a plain file, because links need Developer Mode, and junctions are treated as links.

## 8. A restore that brings back older ignore rules

If a phase changed `.gitignore`, restoring an earlier checkpoint can turn a file that is ignored now back into a project file. The restore leaves that file untouched and ends with "did not complete"; the state before it is saved. The re-review found this is not the old F01 destruction. Fixed means one of two things, to be decided: the restore predicts it and refuses before changing anything, or it stays a documented limit (`recovery.md`, section 3).

## 9. Tests for four safety checks

Removing any of these four checks fails no test today: in `checkpoint.py`, the snapshot compared with the disk, the re-check just before a restore changes files, and the "nothing lost" check after a restore; in `render_pdf.py`, the element list. The re-review showed each can be tested directly, with no special hook: change a file between the snapshot and its comparison, edit a file between verification and the re-check, remove an ignored file after the restore writes, and use a harmless element that is not on the list (such as `<a>`). Turn those into tests.

## 10. Walk through the protocol once

The tests for STOP, RESTORE, CORRECT and RETRY MIGRATION, and for the ending with approved baseline failures, check the wording in `SKILL.md`, not what an agent does. Run the whole skill once with an agent on a small throwaway project, with one failing phase, one restore and a baseline that has a failing test, and check that the agent follows the text.

## 11. Speed on a large project

Timed only with 20,000 synthetic ignored files (about 0.3 seconds for `create`). Time `create` and `restore` on a copy of a large real project.

## Closed

F01, F04, F05, F07, F09 and F10 were closed by the independent re-review of 2026-09-24 — F05 on macOS (FAT and network drives were not tried), F09 and F10 for their wording. The full re-review, with its evidence, is kept on the Mac: `Desktop/vibe-to-engineering-re-review-2026-09-24.md`.
