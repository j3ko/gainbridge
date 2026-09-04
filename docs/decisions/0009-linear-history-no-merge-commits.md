# 0009: `main` requires linear history — land multi-branch work via cherry-pick

Date: 2026-09-04

## Decision

`main` has a GitHub repository rule forbidding merge commits ("This branch must not contain merge
commits"). When landing more than one already-reviewed branch onto `main` directly (e.g. several
Dependabot PRs at once), use `git cherry-pick` (or an equivalent rebase-based approach) commit by
commit, not `git merge --no-ff`. Resolve any `uv.lock`/`bun.lock` conflicts by taking either side
and regenerating (`uv lock` / `bun install`), never by hand-editing lockfile conflict markers,
since that content is fully derived from `pyproject.toml`/`package.json`.

## Reasoning

Discovered by hitting it: a direct `git push origin main` containing a merge commit was rejected
outright with `GH013: Repository rule violations found` / "This branch must not contain merge
commits". Redoing the same work as a linear sequence of cherry-picks (preserving each original
commit's author and message) succeeded and produced a history indistinguishable from what
GitHub's own "Rebase and merge" button would have produced.

## Consequence

Anyone (human or agent) landing multiple branches onto `main` outside the normal single-PR flow
needs to know upfront that merge commits will be rejected, rather than discovering it after doing
the work the other way. Cherry-picking preserves per-PR commit boundaries (useful when a PR itself
has more than one commit, e.g. a dependency bump plus a follow-up fix), unlike squashing everything
into one commit.
