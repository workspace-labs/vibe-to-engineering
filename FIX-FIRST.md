# Fix first

## Current priority — 2026-09-29

Use [LASTUPDATE.md](LASTUPDATE.md) for the current status and remaining release checklist.
A1 and A2 are accepted; independent review verified R2-F2/F4/F6, and the owner has now
accepted the remaining F3-R1 fix following Kimi's independent re-review. **A3 is implemented:**
the tool never deletes — every run-owned scratch root is retained under
`~/.vibe-to-engineering/runs/` (mode 0700), confirmed by the R1 identity proof, its path recorded
in the evidence header, on stderr and — per the protocol — in the project ledger; deletion stays
the human's act. R2-F1 is closed by construction. The first A3 review (of 569c8f9) reopened it
for F1–F5 (a check tampering with the scratch base), and the re-review of that corrective
(9204241) reopened it again for N1–N5 (a swap window between identity check and chmod, an
exit-3 regression on a removed $TMPDIR, a letter-case route past the project-containment check,
an early refusal creating the base, a header claiming unconfirmed retention), and the third
review (of cc5b862) for P1–P5 (base levels opened by re-walking paths, a foreign folder
chmodded as home/, an unreadable own root misreported as a stranger, raw fstat failures, a
vacuous swap test), and the fourth review (of 87709ab) for Q1–Q2 (a by-path restore raced by
a real foreign directory, a root string resolved after creation). All four correctives are
implemented — the root's descriptor is now held open from creation to retention, identity and
mode judged on it alone, one descriptor chain from base to root to home/tmp, an honest
header — each with
fail-on-the-reviewed-commit regressions, and the fourth is **delivered for independent
re-review, not accepted**. Next after acceptance is **A4: macOS-only platform
refusal at the
execution boundary**, then the documentation sweep, the regression re-verification and the macOS
workflow exam. Whole-skill release and NEW-5 closure are still pending.

The entries below are historical findings and delivery records, including their then-current
test counts and review statuses. They are preserved as history, not a new order to redo accepted work.

What is still open in vibe-to-engineering 0.1.0, in the order to work on it. Each item says what is wrong, how to see it, where it is, and what "fixed" means. Take one item at a time and run the tests after each.

## Before you start

- **Run the tests** on the machine you are using, from the repository root: `python3 -m unittest discover -s tests -v` (`py -3` on Windows). Needs Python 3.8+ and git; the three tests that print a PDF also need a Chrome-family browser and are skipped without one, and the one that reads the printed text also needs `pdftotext`. On macOS all 179 pass (branch `fix/f03-f06-f08-new1`, NEW-5 stage 1 with final-review corrective R1, 2026-09-27).
- **Never point the skill at a real project.** Copy the project to a scratch folder and use the copy.
- **Where things stand:** the independent re-review (2026-09-24) of the corrections in `502d3c5` closed F01, F04, F05, F07, F09 and F10, and reopened four: F02, F03, F06 and F08 — items 1 to 4 below. It also confirmed NEW-1 (item 5). The round-2 re-review (2026-09-24, night) closed F06, F08, NEW-1 and ENG-01 and reopened F03, NEW-5 and NEW-6 — corrected in round 3, below. The round-3 re-review (2026-09-24, late night) kept those four closed and reopened NEW-5, F03 and NEW-6 again — corrected in round 4, below. The round-4 re-review (2026-09-25) closed NEW-6, kept F06, F08, NEW-1 and ENG-01 closed, and reopened NEW-5 and F03 — corrected in round 5, below. The round-5 re-review (2026-09-25) accepted F03 and reopened NEW-5 — corrected in round 6, below. The round-6 re-review (2026-09-25) confirmed the round-5 blockers closed and reopened NEW-5 for a variable a shell inherits — corrected in round 7, below. The round-7 re-review (2026-09-25) confirmed that correction and reopened NEW-5 for six findings (B1–B6) — corrected in round 8, below. The round-8 re-review (2026-09-26) confirmed B1–B3, B5 and B6 and reopened NEW-5 for B4 and a Node loader's keys (NODE-PRECEDENCE) — corrected in round 9, below. NEW-5's stage-1 architecture change — construction of the check's environment instead of inheritance, the governed `--env` contract, the supported-check registry and the closure standard, under seven owner decisions (the design contract of 2026-09-26) — is implemented and delivered for the final independent review (stage 1, below); NEW-5 stays open until that review decides. Line numbers below are for `502d3c5`; the quoted text of each line is the anchor if the numbers move.
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

## Corrected in round 4 (2026-09-25) — the round-3 re-review's reopened findings

- **NEW-5 (High) — recognized secret values still leaked** (a YAML flow list, a YAML block header with a comment, TOML `"""…"""` values and their `\u` escapes, a YAML `''` apostrophe, a key body read as a name). **CORRECTED / DELIVERED FOR RE-REVIEW** — one reader per format (`secretformats.py`) and every form of a value (`secretforms.py`); see the CHANGELOG entry. Tests: `test_a_value_is_masked_completely_in_every_format_the_tool_reads_or_the_file_stops_the_run`, `test_a_value_inside_another_value_or_a_bare_token_line_is_masked_and_never_named`, `test_a_setting_token_part_or_standard_reading_of_a_value_is_masked_and_never_named`, `test_masking_one_value_never_hides_another_and_each_reading_the_checkers_found_is_masked` (tests/test_evidence.py). Decided here, for the owner to keep or change: a number found inside a value whose name says nothing secret stays a readable setting (`SESSION_BLOB=horseBattery=1984` leaves `1984` readable; so does the port in `http://localhost:8000`), as the settings rule reads a number there; a secret file in a format the tool does not read (a document, source code) is masked as written, line by line, not decoded — refusing such files instead is the stricter choice.
- **F03 (High) — a sparse index was expanded, and written into, before the refusal.** **CORRECTED / DELIVERED FOR RE-REVIEW** — `gitrun.py` reads git's index itself and refuses a sparse index before git runs anything that reads it, in a nested repository and in the project's own; tests `test_a_nested_repository_with_a_sparse_index_is_refused_before_git_writes_or_fetches_anything`, `test_a_project_whose_own_git_keeps_a_sparse_index_is_refused_before_git_writes_anything`, `test_a_sparse_checkout_without_a_sparse_index_is_still_inspected` (tests/test_nested.py). The older git is still emulated: none older than 2.46 is installed on this Mac.
- **NEW-6 (Medium) — two old checkpoints compared as unchanged.** **CORRECTED / DELIVERED FOR RE-REVIEW** — a checkpoint without content records is read through its list of ignored files; tests `test_two_checkpoints_from_an_older_tool_are_never_called_unchanged_in_either_direction` and `test_a_file_inside_a_folder_an_older_tool_listed_as_one_entry_is_never_called_unchanged` (tests/test_watched.py), which recreate the old tools' genuine checkpoints byte for byte.

## Corrected in round 5 (2026-09-25) — the round-4 re-review's reopened findings

- **NEW-5 (High) — readings the collector did not make still leaked** (a YAML binary tag through a `%TAG` handle, `!e!binary` and `!binary`; a `.env` value with arithmetic inside `"…"`, hexadecimal arithmetic, and `${#NAME}`). **CORRECTED / DELIVERED FOR RE-REVIEW** — tags resolved through the document's handles, the shell's reading worked out or the file refused; see the CHANGELOG entry. Tests: `test_a_yaml_tag_or_a_shell_expansion_is_read_as_its_reader_reads_it_or_the_file_stops_the_run` (tests/test_evidence_readings.py, a new file that keeps tests/test_evidence.py under the 1,000-line limit) and `test_a_padded_token_a_fragment_parameter_and_a_json_list_in_env_each_stay_masked` (tests/test_evidence.py). Decided here, for the owner to keep or change: a `.env` value whose shell reading only a shell can make — a command's output, `$$` (a Docker-style `$$` escape included) and the other special parameters only the running shell knows — now stops the run instead of being masked as written; inside `'…'` nothing is expanded, so such a value still reads there.
- **F03 (Medium) — a split index's shared index file had its time rewritten.** **CORRECTED / DELIVERED FOR RE-REVIEW** — refused before git reads it, like a sparse index; test `test_a_split_index_is_refused_before_git_reads_it_nested_ignored_or_the_projects_own` (tests/test_nested.py).

## Corrected in round 6 (2026-09-25) — the round-5 re-review's reopened NEW-5

- **NEW-5 (High) — four more readings reached the evidence** (a YAML file read as a template's text past a binary tag; `${#NAME}` measured with another reader's value; builtin options dropping the value they assign; arithmetic past 64 bits). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry. Tests: `test_a_yaml_file_is_read_as_a_template_s_text_only_for_template_syntax_and_never_past_a_decoding_tag` and `test_a_shell_value_is_read_with_the_shell_s_own_variables_or_the_file_stops_the_run` (tests/test_evidence_readings.py). Decided here, for the owner to keep or change: a `.env` line using `&&`, `||`, `|`, `( )`, a here-document, `eval` or another command that sets variables its own way, a builtin option other than `--`, a reference in a command's words, or arithmetic past 64 bits now stops the run.
- **F03** — accepted by the round-5 re-review; not touched in round 6.

## Corrected in round 7 (2026-09-25) — the round-6 re-review's reopened NEW-5

- **NEW-5 (High) — a `.env` value a shell builds from outside the file reached the evidence** (`DB_PASSWORD=${SECRET:-safe-fallback}` with `SECRET` inherited). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry. Tests: `test_a_value_the_shell_takes_from_outside_the_file_stops_the_run_and_a_part_it_skips_does_not` and `test_a_value_the_file_does_not_decide_stops_the_run_and_the_shell_reads_every_line_as_written` (tests/test_evidence_readings.py); eight existing cases that relied on a name the file never sets now set it themselves, or moved to the refused cases (listed in the round-7 handoff). Decided here, for the owner to keep or change: a `.env` value built from `HOME`, `USER`, `PATH` or any other variable the file does not set — `~/…` included — now stops the run, as do the other refusals in the CHANGELOG entry. Open for the owner and the reviewer: python-dotenv fills `${NAME}` from the environment inside single quotes too, and `load_dotenv()` lets the environment win even for a name the file sets; this round follows the shell, as asked.
- **F03** — accepted by the round-5 re-review; not touched in rounds 6 or 7.

## Corrected in round 8 (2026-09-26) — the round-7 re-review's reopened NEW-5

- **NEW-5 (High) — six ways a `.env` reading and the real reader still parted** (B1 an inherited function changing a value the file set; B2 a byte order mark; B3 JSON text standing in for a refused shell reading; B4 a construct refused in a part the shell skips; B5 `~name`; B6 python-dotenv reading the environment). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry and the round-8 handoff. Tests: six new methods in tests/test_evidence_readings.py, one per finding, and `test_a_name_the_env_flag_gives_the_check_never_stops_the_run` (tests/test_evidence.py); the existing cases the new refusals now catch set their values again, take `HOME` out of the check's environment, or moved to the new methods (listed in the round-8 handoff). Decided by the owner (2026-09-25): python-dotenv is refused, never modelled; a part the shell provably skips is never refused for what it holds; `~name` is refused. The cost, stated before the decision: a `.env` name the check's environment already holds (`HOME`, `PATH`, a name a CI exports) now stops the run, and so does an unquoted value with a space unless the file sets it again.
- **F03** — accepted by the round-5 re-review; not touched in rounds 6, 7 or 8.

## Corrected in round 9 (2026-09-26) — the round-8 re-review's reopened NEW-5

- **NEW-5 (High) — a part the shell skips still refused, and a Node loader's key** (B4: a quote, a backslash, or a quoted or escaped command's output in a part of a `${ … }` the shell skips; NODE-PRECEDENCE: `'DB_PASSWORD'=from-file` and keys like it, which Node's own loader reads, keeping an inherited value). **CORRECTED / DELIVERED FOR RE-REVIEW** — see the CHANGELOG entry and the round-9 handoff. Tests: `test_valid_syntax_in_a_part_the_shell_skips_is_masked_and_stops_the_run_where_the_shell_reads_it`, `test_a_name_followed_by_anything_but_an_operator_stops_the_run_where_the_shell_reads_it`, `test_a_quote_the_shell_never_finds_closed_stops_the_run`, `test_a_key_a_node_loader_reads_that_the_environment_already_holds_stops_the_run` and `test_each_key_the_real_node_keeps_an_inherited_value_for_stops_the_run` (tests/test_evidence_readings.py; the last runs the local Node, and without it is skipped as NOT VERIFIED unless `V2E_REQUIRE_NODE` is set); two round-8 B4 cases this corrects moved from refused to masked, and round 3's R14 case moved from tests/test_evidence.py to a refusal. Decided by the owner (2026-09-26): the wider set of Node keys, bounded by the loaders' own sources; and two builder-discovered leaks corrected with B4 — a bad substitution (`${A${B}}`) and a quote the shell never finds closed. A third builder-discovered leak — a backslash before a raw DEL or `\x01` byte bash keeps a byte of its own for (`test_a_backslash_before_a_byte_bash_keeps_its_escape_byte_for_stops_the_run`) — is corrected the same way, pending the owner's ruling.
- **F03** — accepted by the round-5 re-review; not touched in rounds 6 to 9.

## Corrected in stage 1 (2026-09-27) — the NEW-5 architecture change, under the owner's design contract

- **NEW-5 (High) — the check inherited its environment; it is now constructed.** **IMPLEMENTED / DELIVERED FOR THE FINAL INDEPENDENT REVIEW** — see the CHANGELOG entry and the acceptance record (skills/vibe-to-engineering/references/stage1-acceptance.md). Built in five slices, each accepted at its own gate: the constructed-environment module (`childenv.py`: synthesized profile, run-owned scratch root retained after the run — A3: the tool never deletes — `--with-path` validation, the prohibited-name set, `--env` validation); the launch-path rewire (one constructed mapping for analysis and launch, declared names only in the header, the documented `python3 -I` invocation); the precedence and reader obligations (round 9's `--env` exclusion superseded, the declared winner masked rather than refused, `.env.vault` refused, npm dotenv v0.4–1.2 interpolation worked out or refused); the supported-check registry and revalidation gate (`references/supported-checks.md`; python, sh and node, identified by the resolved executable); and the acceptance suite (tests/test_stage1_acceptance.py: paired adversarial runs, prohibited-name admission attempts, refusal-means-no-launch, real sh and Node exercises, seeded property runs). Plus, between gates 4 and 5, the owner's Windows corrective: environment-name rules fold case and `SystemRoot` is derived from the OS — proven structurally; native Windows verification is pending and Windows is not claimed supported. Decided by the owner (2026-09-26/27, recorded in the design contract): the seven decisions D1–D7, the macOS `__CF_USER_TEXT_ENCODING` pin, the runner-identity interpretation of a supported check, and the guarantee boundary — the guarantee begins at the constructed environment of the launched child; wrapper startup and the check's own behavior after launch are outside it; no sandbox is claimed. **Not closed**: NEW-5 closes only when the final independent review confirms the boundary contract holds, per the closure standard (D7). **Final-review corrective R1 (2026-09-27)**: the first final review found eight blocking findings (five High, three Medium) — cleanup deleting whatever stood at a scratch-root path; short, numeric and embedded declared values reaching the evidence; diagnostics echoing a declared value inside another argument; a --with-path name splitting into extra PATH entries; the runner gate trusting a name judged against the wrong folder; a post-launch cleanup failure reported as a refusal; shell readings still refused under the inheritance-era rule although the constructed environment decides them; and two reader profiles without live real-reader evidence. Each is corrected at its underlying invariant, with regression tests that fail against the reviewed candidate (tests/test_final_review_r1.py) and live evidence for the last profile gap (references/stage1-acceptance.md) — delivered for the R2 review, which has not yet been requested.
- **F03** — accepted by the round-5 re-review; preserved untouched through stage 1 (its seal held: the same +76/−14 diff on its four files at every gate).

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
