# 0006: Evaluate source schedules in an auto-detected local timezone

Date: 2026-08-28

## Decision

A source's `schedule_cron` (e.g. `0 23 * * *`) is evaluated against a configured `TIMEZONE`
setting, not UTC, using `zoneinfo` so DST transitions are handled correctly; the computed next-run
is converted back to UTC for storage. `TIMEZONE` auto-detects (`_detect_timezone` in
`backend/app/core/config.py`) from, in order: the `TZ` env var, Debian-style `/etc/timezone`, and
the `/etc/localtime` symlink target — falling back to UTC only if none resolve. The configured
value is exposed via `GET /api/v1/utils/config/` and surfaced as a hint in the frontend's Schedule
Sync dialog.

## Reasoning

`croniter` was originally evaluating `schedule_cron` against a UTC datetime, so a cron meant as
"11 PM local time" actually fired at 23:00 UTC — a 4-hour offset for EDT users, matching a reported
bug (cron for 11 PM showing `Next: 7:00 PM` in Toronto). A fixed default of UTC would have needed
every deployer to set `TIMEZONE` by hand; auto-detecting it from the container's own system
timezone means mounting `/etc/localtime`/`/etc/timezone` from the host (already shown in the
README's `docker run` example) is enough on its own, and `TIMEZONE` only needs setting explicitly
to override that detection.

## Consequence

`tzdata` is now an explicit backend dependency, so `ZoneInfo` resolves reliably regardless of the
base image's OS tzdata. Schedule tests are pinned to `TIMEZONE=UTC` so they don't depend on the
deployer's `.env`. Any code that computes a schedule's next run must go through the configured
timezone rather than assuming UTC.
