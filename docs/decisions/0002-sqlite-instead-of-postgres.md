# 0002: SQLite instead of PostgreSQL

Date: 2026-08-06

## Decision

Use SQLite (via SQLModel) as gainbridge's database, not the PostgreSQL the
`tiangolo/full-stack-fastapi-template` ships with. The database file lives under a top-level
`data/` folder that's bind-mounted into the container by `compose.yml`, alongside the log file, so
it survives redeploys.

## Reasoning

gainbridge is a single-user tool with a small amount of state (sources, jobs, logs) and, since
0005, a single backend process — there's no concurrent-write load or multi-service access pattern
that would justify running and operating a separate Postgres container. A single SQLite file also
makes backup, inspection, and moving the app between hosts trivial: copy `data/gainbridge.db`.

## Consequence

No separate database container/service to configure, deploy, or keep in sync with the app version.
The tradeoff is SQLite's single-writer model, which is a non-issue given 0005's single-process
constraint but would need reconsidering if the app ever needed real concurrent write throughput.
