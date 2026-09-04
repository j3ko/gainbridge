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
