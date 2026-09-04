# 0004: Apply Alembic migrations from the app's own startup lifespan

Date: 2026-08-27

## Decision

`app/main.py`'s `lifespan` handler calls `run_migrations()`
(`backend/app/core/migrations.py`), which applies a legacy-DB stamp and then `alembic upgrade
head`, before the app starts serving requests. This runs regardless of how the process is
launched — Docker, `compose.override.yml`'s dev command, the VS Code debugger
(`.vscode/launch.json`, which invokes `uvicorn` directly), or a bare `fastapi dev` — so a fresh or
stale SQLite file is always brought up to date first.

The upgrade runs under an `flock` on a `.migrations.lock` file next to the DB, so that if the app
is ever run with multiple workers again, one worker migrates while the rest block, then proceed
once it's a no-op.

## Reasoning

An earlier fix wired `scripts/prestart.sh` (`alembic upgrade head`) into the Docker `CMD` and
`compose.override.yml`'s command, but that only covered those two launch paths — the VS Code debug
config launched `uvicorn` directly and hit the same "no such table" failure prestart was meant to
prevent. SQLite silently creates an empty file on first connection, so the failure isn't "can't
connect," it's a 500 on every request touching a table. Chasing every possible launch method
individually (two Dockerfiles, compose override, `launch.json`, and any future one) wasn't
sustainable — making the app self-sufficient closes all of them at once.

## Consequence

Migrations apply automatically on every startup path, with no separate step to remember before
running against a fresh `data/` directory. `scripts/prestart.sh` is no longer required for the app
to migrate itself, but stays for CI's explicit "Migrate DB" step. The cost is `run_migrations()`
running on every `uvicorn --reload` restart, a no-op once the DB is current, and Alembic + `flock`
becoming an implicit dependency of app startup rather than of deploy tooling.
