# RA-07 — see and check the plan where only Firefox is installed

## What is missing

`render_pdf.py` looks only for Chrome-family browsers: Chrome, Chromium, Edge, Brave and Playwright downloads (`render_pdf.py:124-150`). On a standard Ubuntu the default browser is **Firefox**, and it's the only one installed. The renderer finds nothing, so there's no PDF, and the agent has no tool from the skill to do the required visual check: `Look at the result — open it or render its pages as images — and make sure the CURRENT → MIGRATION → TARGET page is readable` (`SKILL.md:131`).

Related, already noted in the Linux test: on this Ubuntu, `apparmor_restrict_unprivileged_userns=1` blocks the sandbox of downloaded Chrome builds, so installing Puppeteer or Playwright Chrome doesn't help either.

## How it showed up

Test PC, Ubuntu 25.10, 2026-09-24. Firefox is at `/usr/bin/firefox` (snap); no Chrome-family browser has an AppArmor profile.

```
$ python3 render_pdf.py …/Engineering-Migration-Plan.html …/Engineering-Migration-Plan.pdf
render_pdf.py: error: no Chrome, Chromium, Edge or Brave browser was found. …
exit 3
```

The same Firefox rendered the plan correctly for a visual check:

```
firefox --headless --no-remote --profile <empty temp folder> --window-size 1300,5200 \
        --screenshot plan.png file:///…/Engineering-Migration-Plan.html
```

(`--no-remote` and a fresh profile are needed when the owner's Firefox is already open; without them it fails with "Firefox is already running, but is not responding".)

## Where

- `skills/vibe-to-engineering/scripts/render_pdf.py:124` → `def browser_candidates():`
- `render_pdf.py:154` → `def find_browser():`
- `SKILL.md:131` → `Look at the result — open it or render its pages as images — …`

## Added means

1. When no Chrome-family browser works, the renderer falls back to Firefox for a **visual check**: page screenshots made with a throwaway profile and `--no-remote`, and the same network blocking and no-script rules as the PDF path. It says plainly that the PDF was not made and the screenshots are for checking only.
2. The error message names what it *did* find ("Firefox found: used for a visual check; PDF needs a Chrome-family browser") and gives the exact fix for the platform, including the Ubuntu AppArmor case.
3. `SKILL.md:131` says what to do when only the visual check is possible: look at the screenshots, report "PDF: not made — <reason>", and give the HTML path.
4. Tests: the renderer picks Firefox when it's the only browser, uses a fresh profile, and leaves no profile behind. These are skipped when Firefox is absent.

## Ideas (not tried)

- Firefox has no dependable command-line print-to-PDF. If a PDF is required, investigate WebDriver BiDi `browsingContext.print` over Firefox's Remote Agent (`--remote-debugging-port`), using the standard library only.
- Snap Firefox can't read every path (snap confinement). Keep the screenshot and profile under the user's home folder, as was done here.
