# Frontend

How screens behave as the product earns data, interaction and languages. Apply each part
at its **due at** trigger, never by scaffolding future responsibilities (§22). Accepted
project rules and framework conventions still win (§61).

## Contents

- §71 Data, state and screens
- §72 Quality: accessibility, security, performance, languages, screen sizes

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
- Validate at the form so the person can correct mistakes, using browser or native
  controls as appropriate. Validate again wherever the write is accepted. A form backed
  by an API needs server-side validation (§68). A local-only form validates at its local
  write boundary and stays offline. Prevent double-submit on either platform.
- No secrets in frontend code or its build variables (§69).

## §72 Quality: accessibility, security, performance, languages, screen sizes

**Due at:** the first screen earns accessibility. For websites and web apps, screen sizes
are due at the first screen viewed in a web browser. Data rendering, authentication,
public deployment, measured performance needs and languages earn the controls below.

- **Accessibility is due at the first screen.** Label inputs and icon buttons, meet
  WCAG 2.2 AA text contrast and respect reduced-motion preferences. On the web, use
  semantic HTML and check every control with an accessibility tool and by keyboard
  with visible focus. On native screens, use platform accessibility roles and labels,
  then check focus order and operation with the platform's screen reader and input methods.
- When rendering HTML, never inject raw HTML unless it is sanitized against XSS. For
  browser authentication, prefer auth tokens in `httpOnly` cookies over `localStorage`.
  Cookie-based sessions also need CSRF protection (§68).
- **A Content Security Policy is due at the first public web deployment.**
- Measure before optimizing (§45). On the web, use bundle size and page-speed metrics
  such as Core Web Vitals. Split by route and size images once measurement shows a need.
  Do not add speculative performance machinery to a tiny page.
- **When the second language is due**, keep user-facing text out of components in the
  project's localization resources.
- **When a right-to-left language such as Arabic is supported, even as the first language**,
  check the mirrored layout on a real screen. Use the platform's layout direction. On
  the web, set `dir` on the document and use logical CSS properties such as `margin-inline-start`.
- **Screen sizes.** Build websites and web apps mobile-first. Make the narrow layout
  the base and add to it at wider widths. Set the viewport meta tag, prevent horizontal
  scrolling at phone width, and keep touch targets large enough to tap. Use the
  breakpoints in the project or its design system (§61). If neither sets them, use
  640, 768, 1024 and 1280 px.
  Before calling a website or web app done, check the rendered layout at phone (about
  390 px), tablet (768 px) and laptop (1280 px or wider) widths. Show the result at each
  width, for example with a screenshot at each size. For a fixed-screen product, such as
  an app for one known tablet or a desktop window, check its real device or window
  sizes instead of the three web widths.
