# Frontend

How screens behave as the product earns data, interaction and languages. Apply each part
at its **due at** trigger, never by scaffolding future responsibilities (§22). Accepted
project rules and framework conventions still win (§61).

## Contents

- §71 Data, state and screens
- §72 Quality: accessibility, security, performance, languages

## §71 Data, state and screens

**Due at:** the first screen with state or remote data; forms and writes earn their
specific handling when introduced.

- Separate server data, which is fetched, cached and can go stale, from screen state such
  as open menus and form drafts. Server data has one owner (§13), behind the **one API
  client** earned by the first call to a server in the layout map.
- Every view showing remote data handles four states: **loading, empty, error, success**.
  No endless spinner or blank screen; an error tells the person what they can do next.
- After a write, refresh or invalidate affected cached data. An optimistic update needs
  a rollback when the write fails.
- At the first form, validate in the browser for a good experience **and on the server
  for trust** (§68). Prevent double-submit.
- No secrets in frontend code or its build variables (§69).

## §72 Quality: accessibility, security, performance, languages

**Due at:** the first screen earns accessibility; data rendering, authentication,
public deployment, measured performance needs and languages earn the controls below.

- **Accessibility is due at the first screen.** Use semantic HTML. Every control works by
  keyboard with visible focus; inputs and icon buttons have labels. Text contrast meets
  WCAG 2.2 AA, and motion respects reduced-motion preferences. Check with an accessibility
  tool **and by keyboard**.
- When rendering data, never inject raw HTML unless it is sanitized against XSS. When
  authentication is introduced, prefer auth tokens in `httpOnly` cookies rather than
  `localStorage`; cookie-based sessions also need CSRF protection (§68).
- **A Content Security Policy is due at the first public deployment.**
- Measure before optimizing (§45): use bundle size and page-speed metrics such as Core
  Web Vitals. Split by route and size images once measurement shows a need; do not add
  speculative performance machinery to a tiny page.
- **When the second language is due**, keep user-facing text out of components in the
  project's localization resources.
- **When a right-to-left language such as Arabic is supported, even as the first language**,
  set `dir` on the document, use logical CSS properties (`margin-inline-start`, not
  `margin-left`), and check the mirrored layout on a real screen.
