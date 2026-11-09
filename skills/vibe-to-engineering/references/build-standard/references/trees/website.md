# Example tree — content website

A static or content-driven site (marketing site, blog, docs site). These are snapshots of one
project as it grows, worked examples of the *due at* rule in the layout map — **never a template
to scaffold**. Create only what the product has already earned (§22). A site that stops at
stage 1 is finished, not unfinished. If the framework has its own settled structure, the
framework wins (§61).

## Stage 1 — day one

```
mysite/
  README.md
  CHANGELOG.md
  .gitignore
  docs/scope.md
  src/
    index.html            the first page
  tests/
```

Everything on one page stays in one file. No folders for futures.

## Stage 2 — the second page and the first shared piece

```
  src/
    index.html
    about.html            earned by: the second page
    layouts/              earned by: the first markup two pages share
    styles/               earned by: the first style not owned by one page
    assets/               earned by: the first image or font
  docs/architecture/boundaries.md   earned by: past the kit — where things live, chosen once
  a credits file          earned by: the first font or borrowed code, with each licence
```

## Stage 3 — build, content at scale, release

```
  src/
    content/              earned by: the first content collection too big for hand-written pages
  scripts/build/          earned by: the first build command a person runs
  docs/deployment/        earned by: the first release
  the CI folder           earned by: the first check that should run without being asked
  LICENSE                 earned by: distribution requires an explicit licence — the owner chooses
  CONTRIBUTING.md, issue templates   earned by: a public contribution or reporting workflow needs them
```

A content website never grows `domain/`, `services/` or `state/`. The moment it needs a server
or shared client state, it has become a webapp — switch to [webapp.md](webapp.md).
