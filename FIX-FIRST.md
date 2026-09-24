# Fix first

What is still open in vibe-to-engineering 0.1.0, in the order to work on it. Each item says what is wrong, how to see it, where it is, and what "fixed" means. Take one item at a time and run the tests after each.

## Before you start

- **Run the tests** on the machine you are using, from the repository root: `python3 -m unittest discover -s tests -v` (`py -3` on Windows). Needs Python 3.8+ and git; the three tests that print a PDF also need a Chrome-family browser and are skipped without one, and the one that reads the printed text also needs `pdftotext`. On macOS all 88 pass (branch `fix/f03-f06-f08-new1`, round 3, 2026-09-24).
- **Never point the skill at a real project.** Copy the project to a scratch folder and use the copy.
- **Where things stand:** the independent re-review (2026-09-24) of the corrections in `502d3c5` closed F01, F04, F05, F07, F09 and F10, and reopened four: F02, F03, F06 and F08 — items 1 to 4 below. It also confirmed NEW-1 (item 5). The round-2 re-review (2026-09-24, night) closed F06, F08, NEW-1 and ENG-01 and reopened F03, NEW-5 and NEW-6 — corrected in round 3, below. Line numbers below are for `502d3c5`; the quoted text of each line is the anchor if the numbers move.
- **Ideas** under an item are suggestions that have not been tried.

## 1. F02 (High) — the backup store can still change files outside it

> **Status (2026-09-24): CORRECTED / DELIVERED FOR RE-REVIEW** on branch `fix/f02-store-writes-outside` — not closed until the independent re-review decides. See the CHANGELOG entry; tests `test_a_store_file_with_a_second_name_outside_is_refused_and_git_appends_to_no_file` and `test_a_store_folder_that_cannot_be_read_stops_every_command_before_a_write`. Suite run on Linux, then on macOS (2026-09-24, at `99e1a6a`: 48 run, 48 passed, 0 skipped — macOS 27.0 arm64, Python 3.9.6, git 2.54.0; the four letter-case tests ran).

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

> **Status (2026-09-24): CORRECTED / DELIVERED FOR RE-REVIEW** on branch `fix/f03-f06-f08-new1` — not closed until the independent re-review decides. See the CHANGELOG entry; tests `test_checking_a_nested_repository_runs_no_filter_program_yet_finds_a_same_size_edit` and `test_a_nested_repository_is_compared_with_its_own_index_and_every_kind_of_unsaved_work_is_refused`. Suite run on macOS only.
>
> **Round 2 (2026-09-24, evening): REOPENED by the re-review — a nested repository set up as a partial clone made git fetch a missing object through a remote helper before the refusal — CORRECTED / DELIVERED FOR RE-REVIEW.** Every git call runs with `GIT_NO_LAZY_FETCH=1`; a partial clone is refused outright on a git older than 2.46, and a store configured as one always. Tests `test_a_nested_partial_clone_missing_an_object_is_refused_before_git_fetches_it` (tests/test_nested.py) and `test_a_store_configured_as_a_partial_clone_is_refused` (tests/test_checkpoint.py).

- **What:** the check that a nested repository holds no unsaved work runs `git status` inside it. When git has to re-read a file, `git status` runs any "filter" program the git settings name for it (`filter.<name>.clean`). So a program from the user's or the repository's settings can run during a checkpoint, before the refusal. This check was added by the corrections.
- **See it:** a nested repository with tracked `code.txt` holding `COMMITTED`; in the global git config, `filter.review.clean` set to a small script that writes a marker file and echoes its input; `.gitattributes` in the nested repository holding `*.txt filter=review`; change `code.txt` to `OTHERDATA` (same length) and move its modified time forward; run `create base` in the parent project. The marker file appears, then `create` refuses because the nested repository is dirty.
- **Where:**
  - `checkpoint.py:427` → `            unsaved = git(["status", "--porcelain", "-z", "--untracked-files=all"],`
  - `checkpoint.py:441` → `    check_nested(project, found.nested)`
- **Fixed means:** unsaved nested work is still found and refused, but no configured filter or other configured program runs. Reading the global ignore rules and the hook and file-system-monitor protections stay as they are. A test uses the same-length edit with a global filter and shows no marker, unchanged files and a refusal, through `create`, `diff` and `restore`.
- **Idea:** check the nested repository without `git status`: list its tracked files with `git ls-files -s` and its untracked files with `git ls-files --others --exclude-standard` (neither runs filters), hash the files in Python and compare them with the index. Treat any difference as unsaved work — a file with a filter may then count as changed, which only makes the check stricter.

## 3. F06 (High) — an ignored nested repository with unsaved work still gets a checkpoint

> **Status (2026-09-24): CORRECTED / DELIVERED FOR RE-REVIEW** on branch `fix/f03-f06-f08-new1` — not closed until the independent re-review decides. See the CHANGELOG entry; test `test_an_ignored_nested_repository_is_named_recorded_checked_and_watched`, and the ignored repository inside a nested one in the F03 test above. Suite run on macOS only.
>
> **Round 2 (2026-09-24, evening): REOPENED by the re-review — a committed link replaced by a plain file holding the link's target was called clean — CORRECTED / DELIVERED FOR RE-REVIEW.** A change now, unless the repository's `core.symlinks` is off. Test `test_a_link_replaced_by_a_plain_file_is_unsaved_work_unless_the_repository_keeps_links_as_files` (tests/test_nested.py).

- **What:** a nested repository that git ignores is recorded as ignored and never checked for unsaved work, so `create` succeeds while that repository's uncommitted work is held nowhere.
- **See it:** the parent's `.gitignore` holds `module/`; `module` is a nested repository with committed `code.txt`; edit `code.txt` and add an untracked `new.txt`; run `create base` in the parent. It exits 0 with no warning, and the checkpoint records `ignored-by-git: ["module/"]` but `nested-repositories: []`.
- **Where:**
  - `checkpoint.py:410` → `        ignored.add(disk.locate(rel.rstrip(b"/"))[0] + (b"/" if rel.endswith(b"/") else b""))`
  - `checkpoint.py:411` → `    unsaved = {rel[:-1] for rel in nested | ignored if rel.endswith(b"/")}`
  - `checkpoint.py:441` → `    check_nested(project, found.nested)`
- **Fixed means:** ignored nested repositories are found, recorded and refused while they hold unsaved work, exactly like tracked and untracked ones — without starting to save ignored files such as secrets or dependencies. Do item 2 first: this repair uses its safe check. Tests: an ignored clean and an ignored dirty nested repository, a dirty tracked file and an untracked file inside one, its disappearance reported as `gone`, and a refusal that leaves the project and the nested repository unchanged.

## 4. F08 (Medium) — broken HTML can still run a script or pull a local file into the PDF

> **Status (2026-09-24): CORRECTED / DELIVERED FOR RE-REVIEW** on branch `fix/f03-f06-f08-new1` — not closed until the independent re-review decides. See the CHANGELOG entry; tests `test_the_browser_runs_no_script_and_loads_no_local_file_whatever_markup_gets_past_the_checks` (real prints) and `test_refuses_a_meta_tag_that_other_markup_hides_from_the_checks`. Printed with Playwright's chrome-headless-shell only; the full Chrome build on this Mac hangs on every page, a hidden refresh included.
>
> **Round 2 (2026-09-24, evening): REOPENED by the re-review — a non-breaking space, a vertical tab or an em space before the doctype put the policy in the body, where the browser ignored it — CORRECTED / DELIVERED FOR RE-REVIEW.** Only a byte order mark and ordinary spaces may come before `<!DOCTYPE html>` (refused before the browser starts otherwise), and any content-security-policy line the browser logs refuses the print and deletes the PDF. Tests `test_refuses_a_plan_with_anything_but_spaces_before_the_doctype`, `test_refuses_the_print_when_the_browser_reports_the_policy_ignored`, and the real-print test, which now expects the refusal with the browser's sentence.

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

> **Status (2026-09-24): CORRECTED / DELIVERED FOR RE-REVIEW** on branch `fix/f03-f06-f08-new1`, on the owner's instruction to fix what the list says needs fixing — not closed until the independent re-review decides. See the CHANGELOG entry; test `test_a_repository_git_refuses_to_open_stops_every_command_instead_of_losing_tracked_files`. Apple's git prints no translated messages, so reading git's message untranslated (`LC_ALL=C`) is untested here: try it on Linux with a translated locale.
>
> **Round 2 (2026-09-24, evening): REOPENED by the re-review — a `.git` file whose pointer is broken made git say `not a git repository: (null)`, read as a plain folder — CORRECTED / DELIVERED FOR RE-REVIEW.** A folder is plain only when no `.git` entry exists in it or above it and git's message says `(or any of the parent directories)`. Tests `test_a_broken_git_pointer_is_refused_not_read_as_a_plain_folder` and `test_a_failure_to_open_that_is_not_a_missing_repository_stops_a_plain_folder_too` (tests/test_checkpoint.py); the walk stops at a file-system boundary, as git does.

- **What:** when git refuses a repository — for example "detected dubious ownership", when the folder belongs to another user — `is_git_project()` reads that as "not a git project" and silently switches to the plain-folder rules. A tracked file that matches an ignore rule is then left out of every checkpoint, and `verify` still passes. Confirmed by the re-review; it was outside F01–F10, so it needs its own go-ahead.
- **See it:** commit `tracked.log`, then add `*.log` to `.gitignore`; run `GIT_TEST_ASSUME_DIFFERENT_OWNER=1 python3 skills/vibe-to-engineering/scripts/checkpoint.py --project <that repository> create base`. It exits 0 and the checkpoint has no `tracked.log`.
- **Where:**
  - `checkpoint.py:213` → `    inside = git(["rev-parse", "--is-inside-work-tree"], cwd=project, ok=(0, 128))`
  - `checkpoint.py:214` → `    if inside.returncode != 0 or inside.stdout.strip() != b"true":`
- **Fixed means:** a genuine non-repository still uses the plain-folder rules, but any other failure to open the repository stops the command with git's own message. A test reproduces the ownership refusal and shows the tracked file is not silently dropped.

## Corrected in round 2 (2026-09-24, evening) — the re-review's new findings

- **NEW-5 (High) — `evidence.py` leaked values from files it recognized as secret** (an inline comment, a JSON `"password"` key, a `.env` that is a link, a folder that cannot be listed, a value under four characters). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry; tests `test_every_value_a_secret_file_holds_is_masked_however_it_is_written`, `test_a_number_or_a_yes_no_word_under_an_ordinary_name_stays_readable_and_is_named`, `test_a_folder_that_cannot_be_listed_or_is_a_link_stops_the_run_before_the_check` (tests/test_evidence.py). Left readable on purpose, and named in the summary line: a number or a yes/no word under a name that does not say secret.
- **NEW-6 (Medium) — a secret file replaced with the same size and modification time was called unchanged.** **CORRECTED / DELIVERED FOR RE-REVIEW** — a keyed fingerprint now (`.vibe-to-engineering/fingerprint.key`); test `test_a_secret_file_replaced_with_the_same_size_and_time_is_reported_changed_and_never_hashed_plainly` (tests/test_watched.py).
- **ENG-01 (Medium) — two files over the 1,000-line limit.** **DONE / DELIVERED FOR RE-REVIEW** — `checkpoint.py` split into `gitrun.py`, `nested.py`, `watched.py`, `treeview.py` and itself (810 lines); `tests/test_checkpoint.py` into `support.py`, `test_nested.py`, `test_watched.py`, `test_tree.py` and itself (688 lines); every moved definition and test method the same byte for byte (checked by parsing both sides).

## Corrected in round 3 (2026-09-24, night) — the round-2 re-review's reopened findings

- **NEW-5 (High) — recognized secret values still reached the evidence** (a JSON value with escapes, a YAML block value, a `.env` value quoted over two lines, a private key's body line, a UTF-16 file). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry; test `test_a_value_in_any_written_form_is_masked_and_a_secret_file_that_is_not_text_stops_the_run` (tests/test_evidence.py). Decided here, for the owner to keep or change: a secret file that is not text the tool can read — a binary key container (`.p12`, `.jks`…) or an encoding without a byte order mark — stops the run, naming the file, rather than being named and skipped; none of the owner's projects holds one today.
- **F03 (High) — the older-git fallback read a gitlink child's commit before guarding that child.** **CORRECTED / DELIVERED FOR RE-REVIEW** — `refuse_partial_clone()` runs before the read; test `test_a_partial_clone_nested_in_a_nested_repository_is_refused_before_its_commit_is_read_on_an_older_git` (tests/test_nested.py), with a `git` on the PATH that reports 2.43.0 and drops `GIT_NO_LAZY_FETCH` — an emulation of the older git, not a run of one: no git older than 2.46 is installed on this Mac.
- **NEW-6 (Medium) — an older checkpoint's record was compared as if it vouched for a secret file's contents.** **CORRECTED / DELIVERED FOR RE-REVIEW** — `unknown` now, never unchanged; test `test_an_older_checkpoint_that_cannot_vouch_for_a_secret_file_never_calls_it_unchanged` (tests/test_watched.py). The two older assertions that expected "no changes" from a modification-time record, or no report from a checkpoint that recorded nothing, were removed from `test_a_secret_file_replaced_with_the_same_size_and_time_is_reported_changed_and_never_hashed_plainly` and `test_an_ignored_file_whose_contents_changed_is_reported_though_no_checkpoint_holds_it`; the new test holds the contract they encoded the wrong way.

## 6. Try it on copies of real projects

> **Status (2026-09-24): TRIED on macOS** with the tool on branch `fix/f03-f06-f08-new1`, on copy-on-write clones (`cp -cR`) of four real projects — the originals were only read: an Electron app (7.3 GB), a desktop app with an ignored nested repository (32 GB), and two more (1.9 GB, 955 MB). The first try found **NEW-2**: `create` failed with "Argument list too long" on any project with many ignored files — fixed, see the CHANGELOG, test `test_a_project_whose_ignored_file_names_run_to_megabytes_is_saved`. After the fix, `create`, `verify`, `diff` and a `restore` dry run succeed on all four, with no refusal; the ignored nested repository is named and checked (F06). The old `tree` left out 31,645, 124,320, 24,652 and 18,953 ignored files, and that nested repository, without a word (RA-01). Not tried: a restore with `--apply` on a real project, and Linux and Windows.

The corrections refuse more than before, on purpose: `create` stops for an unreadable folder anywhere in the project (ignored folders too), any warning git prints while listing files, a nested repository with uncommitted work, and two names the tool cannot tell apart. Run `create`, `verify`, `diff` and `restore` on copies of two or three real projects and write down every refusal with its exact message. A refusal that protects nothing real is a candidate fix.

## 7. Linux and Windows

Only macOS has been tested. Run the suite on Linux and on Windows. Known Windows gaps (`skills/vibe-to-engineering/references/recovery.md`, section 4): `verify` accepts a link that comes back as a plain file, because links need Developer Mode, and junctions are treated as links.

## 8. A restore that brings back older ignore rules

If a phase changed `.gitignore`, restoring an earlier checkpoint can turn a file that is ignored now back into a project file. The restore leaves that file untouched and ends with "did not complete"; the state before it is saved. The re-review found this is not the old F01 destruction. Fixed means one of two things, to be decided: the restore predicts it and refuses before changing anything, or it stays a documented limit (`recovery.md`, section 3).

## 9. Tests for four safety checks

> **Status (2026-09-24): DONE / DELIVERED FOR RE-REVIEW** on branch `fix/f03-f06-f08-new1`. Tests `test_a_file_that_changes_while_it_is_being_saved_refuses_the_snapshot`, `test_a_file_edited_after_a_restore_was_verified_stops_it_before_anything_changes`, `test_an_ignored_file_lost_during_a_restore_is_reported` (the tool run in the test's own process, one step wrapped to change the project at the wrong moment) and `test_refuses_an_element_that_is_not_on_the_list_even_a_harmless_one`. Each fails when its check is removed from a copy of the tool.

Removing any of these four checks fails no test today: in `checkpoint.py`, the snapshot compared with the disk, the re-check just before a restore changes files, and the "nothing lost" check after a restore; in `render_pdf.py`, the element list. The re-review showed each can be tested directly, with no special hook: change a file between the snapshot and its comparison, edit a file between verification and the re-check, remove an ignored file after the restore writes, and use a harmless element that is not on the list (such as `<a>`). Turn those into tests.

## 10. Walk through the protocol once

The tests for STOP, RESTORE, CORRECT and RETRY MIGRATION, and for the ending with approved baseline failures, check the wording in `SKILL.md`, not what an agent does. Run the whole skill once with an agent on a small throwaway project, with one failing phase, one restore and a baseline that has a failing test, and check that the agent follows the text.

## 11. Speed on a large project

> **Measured (2026-09-24)** on the four clones of item 6 (macOS 27, Apple silicon, SSD): `create` 7.0 s, 16.2 s, 2.0 s, 1.3 s; `verify` 1.0 s, 2.4 s, 0.3 s, 0.2 s; `diff` 4.5 s, 8.4 s, 1.5 s, 1.0 s. Most of the time is spent fingerprinting the watched ignored files (RA-03): 6.6 GB on the 7.3 GB project, nearly all of it a backups folder. Not done yet: skip re-hashing a file whose size, times and inode match what the last checkpoint recorded.

Timed only with 20,000 synthetic ignored files (about 0.3 seconds for `create`). Time `create` and `restore` on a copy of a large real project.

## Closed

F01, F04, F05, F07, F09 and F10 were closed by the independent re-review of 2026-09-24 — F05 on macOS (FAT and network drives were not tried), F09 and F10 for their wording. The full re-review, with its evidence, is kept on the Mac: `Desktop/vibe-to-engineering-re-review-2026-09-24.md`.
