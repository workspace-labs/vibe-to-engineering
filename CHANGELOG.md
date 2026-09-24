# Changelog

## [Unreleased]

- F02: store commands could still change a file outside the store. The store check now stops at any store folder it cannot read, and refuses any store file that is also another file's name (a hard link), apart from the three files the tool replaces whole; git runs on the store with its reference log switched off. Tests cover both routes, with hard links in reference logs, deep references, `packed-refs` and objects.

## [0.1.0] - 2026-09-23

- First version. The vibe-to-engineering protocol — inspect, diagnose, design the target, plan with a PDF, human approval, verified backup, one approved phase at a time with checkpoints, failure investigation, final review — with its engineering standard, the migration plan template and PDF renderer, and the checkpoint tool with its platform-independent recovery contract and conformance tests. Validated on macOS only.
