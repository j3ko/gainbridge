# Decision records: the index

One line per ADR: what it decided, and when to read it in full. Read this index at the
start of every session; read an ADR itself when the task touches what it decides, when
a hand-off or an issue names it, or before changing something it explains. Keep this
index current: a new ADR or amendment adds or edits its line in the same PR.

| ADR | Decision | Read in full when |
|---|---|---|
| [0001](0001-single-user-no-auth.md) | Single user, no login, no `User` model; the template's auth removed | anything touching access control or exposing the app beyond a private network |
| [0002](0002-sqlite-instead-of-postgres.md) | SQLite under `data/`, not Postgres | changing the database, or anything needing concurrent writes |
| [0003](0003-single-combined-docker-image.md) | One multi-arch production image (root `Dockerfile`) serving the built SPA; separate dev containers | the Dockerfiles, static/SPA serving, CircleCI publishing |
| [0004](0004-self-migrate-on-startup.md) | Alembic migrations run from the app's lifespan, under an `flock` | migrations, startup, a new launch path |
| [0005](0005-single-process-no-workers.md) | One backend process; the scheduler's check-then-insert isn't safe across workers | concurrency, `--workers`, the scheduler or `create_job()` |
| [0006](0006-timezone-aware-schedules.md) | Cron schedules evaluated in an auto-detected local `TIMEZONE`, stored as UTC | schedules, next-run computation, timezone config |
| [0007](0007-changelog-path-cannot-escape-package-dir.md) | `CHANGELOG.md` stays in `backend/`; release-please rejects `../` paths | release-please config |
| [0008](0008-app-version-decoupled-from-package-version.md) | FastAPI's `version=` isn't the package version; the running version comes from `/utils/config/` | the app version, OpenAPI `info`, the footer |
| [0009](0009-linear-history-no-merge-commits.md) | `main` rejects merge commits; land several branches by cherry-pick; regenerate lockfiles, don't hand-resolve | landing branches outside a single PR, lockfile conflicts |
| [0010](0010-pr-title-labeler-keys-off-branch-not-actor.md) | `pr-title-labeler` skips on a `dependabot/` branch, not the actor | `labeler.yml`, a Dependabot PR stuck `unstable` |
| [0011](0011-frozen-uv-run-in-ci.md) | Every `uv run`/`uv sync` in CI and hooks passes `--frozen` | adding a `uv` call to CI, a hook or a script |
| [0012](0012-pin-actions-and-scope-permissions.md) | Actions pinned to SHAs with `# vX.Y.Z`, `permissions: {}`, timeouts, no persisted credentials; zizmor enforces | any change under `.github/workflows/` |
| [0013](0013-plex-track-gain-from-loudness.md) | Plex track gain = `-18 - loudness`; the stream's `gain` is the album gain | Plex loudness extraction, gain values |
| [0014](0014-open-work-in-github-issues.md) | Open work is GitHub issues labelled `next`/`owner`/`check`/`proposal`/`bug`; the session reads this index, not every ADR | how work is tracked or handed off |
