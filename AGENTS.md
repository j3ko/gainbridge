# Project conventions

Gainbridge keeps ReplayGain/loudness tags in sync between Plex/Jellyfin and the actual audio
files. It's a personal, self-hosted tool for one user's library — favor simplicity over generality.

## Stack

- Backend: FastAPI, SQLModel, SQLite, Alembic.
- Frontend: React/TypeScript, Vite, TanStack Query/Router, Tailwind CSS, shadcn/ui.
- Based on `tiangolo/full-stack-fastapi-template`, with the multi-user auth and Postgres it ships
  with removed (see `docs/decisions/0001` and `0002`).
- Local dev: Docker Compose, backend on port 9210 / frontend on port 9220 (see `development.md`).
- Production: a single multi-arch Docker image bundling frontend and backend, built by CircleCI
  and published to Docker Hub (see `docs/decisions/0003`).

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `chore:`, etc.) for every commit.
- This project uses `release-please`, which depends on this format to generate
  `backend/CHANGELOG.md` and version bumps automatically. Never hand-edit that CHANGELOG. It must
  stay inside `backend/` — see `docs/decisions/0007` for why relocating it doesn't work.
- Commits should be atomic and the message should explain *why*, not just what changed.

## Git workflow

- `main` has a GitHub rule requiring linear history — a pushed merge commit is rejected outright
  (`GH013: Repository rule violations found`, "This branch must not contain merge commits"). To
  land more than one already-reviewed branch directly (e.g. several Dependabot PRs at once), use
  `git cherry-pick` commit-by-commit, not `git merge --no-ff` (see `docs/decisions/0009`).
- `uv.lock` and `bun.lock` are fully derived from `pyproject.toml`/`package.json`. If a
  cherry-pick/merge conflicts in one, don't hand-resolve the conflict markers — take either side
  (`git checkout --ours <lockfile>`) and regenerate (`uv lock` / `bun install`), then verify
  (`uv run pytest`, `uv run mypy app`, `bun run build`) before committing.

## Decision records

- Any real design/architecture decision (removing a template feature, a concurrency or migration
  fix, a CI/config choice that failed and was reverted, etc.) gets a short ADR in
  `docs/decisions/NNNN-title.md`.
- Keep ADRs short — one page, dated, states the decision and the reasoning, not a debate log.
- Existing ADRs in `docs/decisions/` are a good source of "why is it built this way" before
  changing something that looks like it could be simplified.

## CI/CD

- GitHub Actions (`.github/workflows/`) runs tests, linting, and PR automation on every push/PR.
- CircleCI (`.circleci/config.yml`) builds and publishes the multi-arch production image to Docker
  Hub — see `docs/decisions/0003`.
- The FastAPI app's version is deliberately not wired to the OpenAPI schema (`docs/decisions/0008`)
  — don't reintroduce that coupling.
- Dependabot never regenerates the frontend client. A `fastapi`/`pydantic` bump can change the
  OpenAPI schema without anyone running `scripts/generate-client.sh`; the committed
  `frontend/src/client/*.gen.ts` goes stale, and only the `generate-frontend-sdk` pre-commit hook
  catches it, as a CI failure. Regenerate and commit the client alongside such bumps.
- `frontend/tests/` has no spec suite yet, so `playwright.yml` only runs on `workflow_dispatch`,
  not push/PR (same reasoning, and the same fix, as a sibling project). Playwright's "no tests
  found" behavior differs by invocation: run unsharded, it exits 1 (hard error); run sharded
  (`--shard=N/M`, what CI actually used to use), it exits 0 silently. A local repro that doesn't
  match CI's exact shard invocation can look like it explains a failure when it doesn't.
- A local `docker compose build` that finishes in ~1s with every layer `CACHED` right after a
  lockfile change is stale, not fixed — rebuild with `--no-cache` before trusting a "this passes
  locally" result.
- TypeScript 7 stops auto-including `@types/node`'s globals for files outside `src/` (e.g.
  `playwright.config.ts`), breaking `tsc`/`bun run build` with "Cannot find name 'process'". Fix
  is `"types": ["node"]` in `frontend/tsconfig.json` (not yet on `main` as of this writing — see
  the open typescript-7 Dependabot PR).
- Dependabot auto-closes a PR once it detects the target version is already satisfied on `main`,
  but only if the branch's `mergeable_state` is fully `clean` — not just clear of `dirty`. If a PR
  is stuck `dirty` (a real conflict) after its content already landed some other way, merge `main`
  back into the PR branch and push to collapse it to a zero-diff no-op. But if it's still stuck at
  `unstable` afterwards, that means some other status check on the PR is failing and blocking
  Dependabot's own auto-close even though the diff is empty — check for that before assuming a
  manual close is the only option (see `docs/decisions/0010` for one concrete cause).
- `pr-title-labeler` (`.github/workflows/labeler.yml`) skips based on whether the PR's *branch*
  starts with `dependabot/`, not on who pushed the triggering commit (`docs/decisions/0010`) —
  keying it off the actor instead left a PR's `mergeable_state` stuck `unstable` forever once a
  human pushed a follow-up commit to it, which in turn blocked Dependabot's auto-close. If any
  other dependabot-adjacent workflow condition gets added later, key it off the branch the same
  way, not the actor.
- No `gh` CLI or GitHub API token is available in the agent sandbox, only SSH git access
  (clone/fetch/push). Reads against the public REST API work unauthenticated
  (`curl api.github.com/...`); anything needing auth (closing/merging PRs via API, downloading raw
  Action job logs) doesn't.

## Concurrency

- The backend runs single-process by default (`docs/decisions/0005`) and self-migrates from its
  own startup lifespan (`docs/decisions/0004`). Don't reintroduce `--workers N` without also
  fixing the scheduler's check-then-insert race described in `docs/decisions/0005`.

## Scope

- This is a personal-use tool, not a commercial product — favor simplicity over generality unless
  a feature is something that's actually been asked for.
- No user accounts, login, or multi-tenancy (`docs/decisions/0001`).

## Agent skills

- `.claude/skills/` and `.agents/skills/` hold per-topic skills, some hand-authored (e.g. `run`)
  and some managed symlinks into skills bundled by installed packages (e.g. `sqlmodel`), installed
  via the `library-skills` tool. Run `uvx library-skills --claude` after adding/upgrading a backend
  dependency to pick up any new package-provided skills; see `.claude/skills/library-skills/`.
