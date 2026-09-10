# 0011: Always run `uv` frozen in CI, not just in the ruff pre-commit hooks

Date: 2026-09-04

## Decision

Every `uv run`/`uv sync` invocation in a GitHub Actions workflow passes `--frozen` — never a
plain, unfrozen `uv run`/`uv sync`. This was already true for `.pre-commit-config.yaml`'s
`local-ruff-check`/`local-ruff-format` hooks and `scripts/generate-client.sh`; this decision
extends it to `test-backend.yml`, `pre-commit.yml`'s own `uv sync --all-packages`, and
`playwright.yml`.

## Reasoning

`uv.lock` records the local `app` package's own version, mirrored from `backend/pyproject.toml`.
`release-please`'s version-bump commits change that version in `pyproject.toml` but don't
necessarily touch `uv.lock` in the same commit. Any *unfrozen* `uv run`/`uv sync` invocation, on
noticing that drift, silently re-locks `uv.lock` to fix it as a side effect of just trying to run
the requested command — before running anything else.

This bit twice already, for the exact same underlying reason:

- `scripts/generate-client.sh`'s `uv run python -c '...'` picked up the same silent
  re-lock, so it was frozen first.
- `local-ruff-check`/`local-ruff-format` in `.pre-commit-config.yaml` were still unfrozen, so
  PR #25's version bump (0.1.1 → 0.2.0, merged without a working `uv.lock` sync mechanism)
  reintroduced the exact failure through a different hook: `prek` saw `uv.lock`'s incidental
  modification and reported it as a hook failure, even though ruff itself found nothing wrong.

Any other CI step that runs `uv` without `--frozen` is one release-please version bump away from
hitting the same false failure.

## Consequence

`uv sync`/`uv run` is never used unfrozen in CI. If a real dependency change ever needs `uv.lock`
regenerated in CI (which should be rare - normally that happens locally, committed, and reviewed),
that has to be an explicit, separate step - not an implicit side effect of running some other
command.
