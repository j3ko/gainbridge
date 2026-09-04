# 0007: release-please's changelog-path can't escape the package directory

Date: 2026-08-30

## Decision

Keep `CHANGELOG.md` at its default location, `backend/CHANGELOG.md` — don't set `changelog-path`
in `release-please-config.json` to relocate it to the repo root.

## Reasoning

Tried it: setting `changelog-path: "../CHANGELOG.md"` on the `backend` package and moving the file
to the repo root was tested as an explicit experiment, since other release-please users have hit
"illegal pathing characters" errors using the same `../` pattern for other config fields
(`extra-files` paths, chart-dependency paths in monorepos). It failed the same way here:
release-please's next run on `main` errored with `illegal pathing characters in path:
backend/../CHANGELOG.md`. This is a real, deliberate guard in release-please, not something
specific to this project's config — there's no supported way to point a package's changelog
outside its own directory.

## Consequence

`CHANGELOG.md` stays inside `backend/`, not at the repo root, for as long as this project uses
release-please's per-package `changelog-path`. Don't re-attempt this without a change in
release-please's own behavior.
