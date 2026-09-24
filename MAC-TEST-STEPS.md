# F02 — Mac test (do this at home)

**Why:** F02 and R1 were accepted as fixed and independently reviewed on Linux at commit `99e1a6a`. F02 stays open until the tests pass on your Mac. Nothing is merged, and the repository stays private. F03, F06, F08 and NEW-1 are still open.

This file is on the branch `f02-mac-test-steps`. The branch you test is a different one: `fix/f02-store-writes-outside`. The builder's full F02 handoff is next to this file: [F02-HANDOFF.md](F02-HANDOFF.md).

Run everything in Terminal as your normal user. Do not use `sudo`: as root, four of the tests skip themselves.

## 1. Check the tools

You need Python 3.8 or newer, and git:

```
python3 --version
git --version
```

## 2. Make a clean copy of the branch

This makes a new folder. Your normal copy of the project is not touched.

```
cd ~
git clone --branch fix/f02-store-writes-outside https://github.com/workspace-labs/vibe-to-engineering.git v2e-f02-mac-check
cd v2e-f02-mac-check
```

- If the folder already exists, git refuses. Use another name, such as `v2e-f02-mac-check-2`.
- If git asks for a password: the repository is private, so use a GitHub token. Or, with the GitHub CLI:
  `gh repo clone workspace-labs/vibe-to-engineering v2e-f02-mac-check -- --branch fix/f02-store-writes-outside`

## 3. Check the commit

```
git rev-parse HEAD
git status --short
```

The first must print exactly `99e1a6adf138c7a8e44d6d73d9cbb5784719ed16`. The second must print nothing.

**If either is different, stop.** Do not run the tests. Send that output to Claude.

## 4. Run the tests

Paste this whole block. It saves everything into one file, `~/v2e-f02-mac-results.txt`: the commit, the machine, whether the disk ignores letter case, every test result and the exit code. It takes about a minute. The last command prints a short summary.

```
{
  echo "== commit"; git rev-parse HEAD; git status --short
  echo "== machine"; sw_vers; uname -m; python3 --version; git --version
  python3 -c "import tempfile,os; d=tempfile.TemporaryDirectory(); open(os.path.join(d.name,'A'),'w').close(); print('temp disk:', 'ignores letter case' if os.path.exists(os.path.join(d.name,'a')) else 'tells letter cases apart'); d.cleanup()"
  echo "== tests"; python3 -m unittest discover -s tests -v
  echo "exit code: $?"
} > ~/v2e-f02-mac-results.txt 2>&1
grep -E "^(Ran |OK|FAILED)|exit code|\.\.\. (skipped|FAIL|ERROR)" ~/v2e-f02-mac-results.txt
```

## 5. Send the results to Claude

Paste the whole file `~/v2e-f02-mac-results.txt` into Claude, after the message below. The file has everything Claude needs:

- the commit and the machine;
- the `Ran … tests` line (there are 48 tests);
- the final line: `OK`, `OK (skipped=N)` or `FAILED (failures=…, errors=…)`;
- every skipped test with its reason, on its line after `skipped`;
- the full error text for any failure (below the `====` lines);
- `exit code: 0`, or another number.

If the file is too long to paste, send the summary lines from step 4 and every failure section in full.

Keep the `v2e-f02-mac-check` folder until Claude has looked at the results.

### What the skips mean

| Skip reason | Meaning |
|---|---|
| `this file system tells letter cases apart` | The disk tells upper- and lower-case letters apart. A normal Mac disk ignores letter case, so these 4 tests should run on the Mac. They matter most for this check. |
| `no Chrome-family browser installed` | No Chrome, Chromium, Edge or Brave was found in `/Applications` or `~/Applications`. These 2 tests are for the PDF renderer, not F02. |
| `needs POSIX file permissions and a normal user` | The tests were run as root. Run them again without `sudo`. |

## Message for Claude

Copy this, paste it into Claude, then paste the results file after it:

```text
I am the owner of the private repository github.com/workspace-labs/vibe-to-engineering.
Branch fix/f02-store-writes-outside at 99e1a6adf138c7a8e44d6d73d9cbb5784719ed16 fixes FIX-FIRST item 1 (F02) and Codex's finding R1.
I accepted F02 and R1 as fixed and independently reviewed on Linux at 99e1a6a. F02 stays open until the test suite passes on my Mac.
My Mac results are below: the file ~/v2e-f02-mac-results.txt, made with MAC-TEST-STEPS.md on the branch f02-mac-test-steps.
The builder's full F02 handoff is F02-HANDOFF.md on that same branch.

Assess the results. Check that HEAD was 99e1a6a with a clean working tree, and report the test count, failures, skips and skip reasons.
Do not say the Mac run passed unless the results show it.
If a test fails: fix only the relevant F02 issue on fix/f02-store-writes-outside and return it for Codex review with a corrective handoff.
If the suite passes: prepare the F02 closure handoff for my merge decision.
Do not merge. Do not make the repository public. F03, F06, F08 and NEW-1 remain open.
```

## After F02 is closed

This branch holds notes only; do not merge it. Delete it before the repository becomes public:

```
git push origin --delete f02-mac-test-steps
```
