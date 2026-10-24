# CI, Dependabot and tooling notes

Read when a task touches `.github/workflows/`, `.circleci/`, a Dependabot PR, a lockfile, or
a Docker build. Lessons that became decisions are ADRs (0007, 0009–0012); these are the
smaller ones. Add a note here when you hit a new problem.

## Pipelines

- **GitHub Actions** (`.github/workflows/`) runs tests, linting and PR automation on every
  push/PR. **CircleCI** (`.circleci/config.yml`) builds and publishes the multi-arch
  production image to Docker Hub (ADR 0003).
- **`guard-dependencies.yml`** auto-closes a PR touching `pyproject.toml`, `uv.lock`,
  `package.json` or `bun.lock` unless it comes from a collaborator or Dependabot.

## Dependabot

- **It never regenerates the frontend client.** A `fastapi`/`pydantic` bump can change the
  OpenAPI schema without anyone running `scripts/generate-client.sh`; the committed
  `frontend/src/client/*.gen.ts` goes stale, and only the `generate-frontend-sdk`
  pre-commit hook catches it, as a CI failure. Regenerate and commit the client alongside
  such bumps.
- **Auto-close needs `mergeable_state` fully `clean`.** Dependabot closes a PR once the
  target version is already on `main`, but not while it's `dirty` or `unstable`. If it's
  `dirty` after its content landed another way, merge `main` back into the PR branch and
  push, collapsing it to a zero-diff no-op. If it's still `unstable` afterwards, another
  status check is failing — find it before closing by hand (ADR 0010 is one cause).
- **Several Dependabot PRs at once** land by cherry-pick, never a merge commit (ADR 0009).

## Builds and tests

- **Playwright:** `frontend/tests/` has no spec suite yet, so `playwright.yml` only runs on
  `workflow_dispatch`. "No tests found" exits 1 unsharded but 0 sharded
  (`--shard=N/M`): a local repro that doesn't match CI's exact invocation can look like it
  explains a failure when it doesn't.
- **A `docker compose build` that finishes in ~1s, all `CACHED`, right after a lockfile
  change is stale,** not fixed. Rebuild with `--no-cache` before trusting "passes locally".
- **TypeScript 7** stops auto-including `@types/node`'s globals for files outside `src/`
  (e.g. `playwright.config.ts`), breaking `tsc` with "Cannot find name 'process'". The fix,
  `"types": ["node"]` in `frontend/tsconfig.json`, is already on `main`; keep it.

## Auth

- The devcontainer bind-mounts the host's `~/.config/gh`, so `gh` is authenticated with the
  host's own login; no token touches the repo. Anything needing auth (closing or merging
  PRs, raw Action job logs) goes through `gh`, not unauthenticated `curl api.github.com`.
