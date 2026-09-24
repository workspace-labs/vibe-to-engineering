# Fix first

What is still open in vibe-to-engineering 0.1.0, in the order to work on it. Each item says what is wrong, how to see it, and what "fixed" means. Take one item at a time and run the tests after each.

## Before you start

- **Run the tests** on the machine you are using, from the repository root: `python3 -m unittest discover -s tests -v` (`py -3` on Windows). Needs Python 3.8+ and git; the two PDF render tests also need a Chrome-family browser and are skipped without one. On macOS all 45 pass.
- **Never point the skill at a real project.** Copy the project to a scratch folder and use the copy.
- **Where things stand:** the ten findings (F01–F10) from the independent review of `135cb96` are corrected in `502d3c5` and waiting for a re-review.

## 1. The re-review

The re-review of `502d3c5` has not happened yet. Whatever it says still does not hold comes first: add each finding here, with its ID, above item 2.

## 2. A repository git refuses to open is treated as a plain folder

- **What:** when git refuses a repository — for example "detected dubious ownership", when the folder belongs to another user — `is_git_project()` in `skills/vibe-to-engineering/scripts/checkpoint.py` reads that as "not a git project" and silently switches to the plain-folder rules. A tracked file that matches an ignore rule is then left out of every checkpoint.
- **See it:** make a repository with `build/` in `.gitignore` and a force-added `build/keep.txt`, then run `GIT_TEST_ASSUME_DIFFERENT_OWNER=1 python3 skills/vibe-to-engineering/scripts/checkpoint.py --project <that repository> tree --current`. `build/keep.txt` is missing.
- **Fixed means:** any `git rev-parse` failure other than "not a git repository" stops the command with git's own message, and a new test in `tests/test_checkpoint.py` fails without the fix and passes with it.

## 3. Try it on copies of real projects

The corrections refuse more than before, on purpose. `create` stops for an unreadable folder anywhere in the project (ignored folders too), any warning git prints while listing files, a nested repository with uncommitted work, and two names the tool cannot tell apart. Run `create`, `verify`, `diff` and `restore` on copies of two or three real projects and write down every refusal with its exact message. A refusal that protects nothing real is a candidate fix.

## 4. Linux and Windows

Only macOS has been tested. Run the suite on Linux and on Windows. Known Windows gaps (`skills/vibe-to-engineering/references/recovery.md`, section 4): `verify` accepts a link that comes back as a plain file, because links need Developer Mode, and junctions are treated as links.

## 5. A restore that brings back older ignore rules

If a phase changed `.gitignore`, restoring an earlier checkpoint can turn a file that is ignored now back into a project file. The restore leaves that file untouched and ends with "did not complete"; the state before it is saved. Fixed means one of two things, to be decided: the restore predicts it and refuses before changing anything, or it stays a documented limit (`recovery.md`, section 3).

## 6. Four checks without a test of their own

These checks guard against problems no test can cause on demand, so removing one would not fail any test: in `checkpoint.py`, the snapshot compared with the disk, the re-check just before a restore changes files, and the "nothing lost" check after a restore; in `render_pdf.py`, the element list. Each needs a way to change the project in the middle of a command, such as a test-only hook.

## 7. Walk through the protocol once

The tests for STOP, RESTORE, CORRECT and RETRY MIGRATION, and for the ending with approved baseline failures, check the wording in `SKILL.md`, not what an agent does. Run the whole skill once with an agent on a small throwaway project, with one failing phase, one restore and a baseline that has a failing test, and check that the agent follows the text.

## 8. Speed on a large project

Timed only with 20,000 synthetic ignored files (about 0.3 seconds for `create`). Time `create` and `restore` on a copy of a large real project.
