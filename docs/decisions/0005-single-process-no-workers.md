# 0005: Run the backend single-process

Date: 2026-08-27

## Decision

Drop the `--workers 4` flag inherited from the original template's Dockerfile. The backend runs as
a single `fastapi run` process in every environment (production image, local dev, VS Code debug).

## Reasoning

`--workers 4` was tuned for a Postgres-backed multi-tenant API and doesn't fit gainbridge:
SQLite (0002) is a single-writer database, this is a single-user self-hosted tool with no real
concurrent-request load, and sync jobs already get in-process concurrency for free via a
`ThreadPoolExecutor` (`app/services/jobs.py`). Multiple worker processes only introduced bugs: a
migration race (fixed by 0004's file lock, kept as a safety net), Alembic disabling the app logger,
and — still latent until this fix — `_scheduler_loop()` running independently in every worker with
`create_job()`'s `skip_if_running` check being a plain check-then-insert with no locking, meaning
two workers could both see a source as due and both start the same scheduled sync at once.

## Consequence

No multi-process concurrency bugs to guard against for the default configuration; the migration
lock in `core/migrations.py` remains only as a safety net. If gainbridge ever needs to scale beyond
one process, the scheduler's check-then-insert race in `create_job()` would need real locking
first, not just re-adding `--workers`.
