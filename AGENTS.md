# Project conventions

Gainbridge keeps ReplayGain/loudness tags in sync between Plex/Jellyfin and the actual audio
files. It's a personal, self-hosted tool for one user's library, not a product — favor
simplicity over generality unless a feature has actually been asked for. No user accounts,
login or multi-tenancy (ADR 0001).

## Read first

At the start of every session, read the ADR index, `docs/decisions/README.md` (one line per
ADR: what it decided, and when to read it in full), and the open issues, one line each
(ADR 0014):

```sh
gh issue list --limit 50 --json number,labels,title --jq '.[] | "\(.number)\t\([.labels[].name] | join(","))\t\(.title)"'
```

Then read in full only the ADRs and issues (`gh issue view <n> --comments`) the task touches,
or that a hand-off names. Before changing something that looks like it could be simplified,
check whether an ADR explains why it is the way it is. A subagent reads this file too, but
only the ADRs its spec names, not the index.

Read on demand, not up front:

- `docs/ci-notes.md` — when touching `.github/`, `.circleci/`, a Dependabot PR, a lockfile
  or a Docker build.
- `development.md` — local dev setup, Docker Compose, ports (backend 9210, frontend 9220).
- The `run` skill — to launch the app or verify a change end to end in a browser.

## Working with the owner

- **Open PRs; don't merge them** unless asked explicitly. Never commit or push without being
  asked.
- **Keep to the scope that was asked for.** Anything worth adding beyond it becomes a
  `proposal` issue and a line in the PR description or reply; don't fold it in quietly.
- **Repo settings are the owner's call:** rulesets, merge styles, secrets, labels, Docker
  Hub and CircleCI. `gh api` can change most of them, but ask first.

## How work is split

The main session keeps design, ADR decisions and the discussion with the owner, and
delegates detail through the **dev-team** plugin (`dev-team@j3ko`, from `j3ko/claude-plugins`,
enabled in `.claude/settings.json`). Load `/dev-team:orchestrate` before delegating. The
agents: `dev-team:implementer` (one spec, own worktree, opens the PR; `model: haiku` for a
mechanical job), `dev-team:researcher` (read-only: Plex/Jellyfin APIs, library docs), and
`dev-team:reviewer` (reviews every PR that changes code, scripts or CI; docs-only and
config-only PRs skip it). A durable decision goes into an ADR first, not just the spec.

## Delegation contract

Read by the dev-team implementer, researcher and reviewer agents. Where this and an agent's
own instructions disagree, this wins.

### Docs
- Decision records: `docs/decisions/`, index at `docs/decisions/README.md`. Read only the
  ones a spec names.
- CI, Dependabot and tooling gotchas: `docs/ci-notes.md`, when the task touches those.
- Open work: GitHub issues (ADR 0014); a spec quotes what a subagent needs from one.

### Commands
- Worktree setup: `uv sync --frozen -q` for backend work; `bun install --frozen-lockfile`
  for frontend work; nothing for docs-only work.
- Backend check (what CI runs), from `backend/`: `uv run --frozen mypy app`, then
  `uv run --frozen bash scripts/prestart.sh && uv run --frozen bash scripts/tests-start.sh`
  (coverage must stay ≥ 90%).
- Frontend check, from `frontend/`: `bun run check` and `bun run build`.
- One test file, from `backend/`: `uv run --frozen pytest tests/<path> -q`
- Commit hook: prek runs ruff, ruff format, biome and the client-generation check on every
  commit. Ruff and biome fix files in place: re-stage after a blocked commit. Never
  `--no-verify`; never `prek install` from a worktree (the hook in the shared `.git/hooks`
  would then point at that worktree's `.venv`).
- API change: run `bash scripts/generate-client.sh` and commit `frontend/src/client/*.gen.ts`
  with it.

### Git and PRs
- Default branch: `main`. Linear history only, squash merges; a merge commit is rejected
  (ADR 0009). Branch from `origin/main` as `<type>/<short-description>`.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/) (`feat`, `fix`,
  `docs`, `refactor`, `test`, `chore`, `ci`, ...), atomic, the body says *why*. GPG-signed
  through the forwarded agent; if signing fails, stop and report.
- PR tool: `gh`. Open a PR: `gh pr create --base main --title "<conventional title>" --body "..."`
- PR diff: `gh pr diff <n>`. PR checks: `gh pr checks <n>`
- PR title: a Conventional Commit — the squash merge makes it the commit release-please reads.
  A PR finishing an issue says `Closes #N` in its body.

### Never (owner-only)
- Merging PRs, cutting releases, pushing images, changing repo/CircleCI/Docker Hub settings
  or secrets.
- Generated files, never hand-edited: `backend/CHANGELOG.md` (release-please; it stays in
  `backend/`, ADR 0007), versions in `pyproject.toml`, `.release-please-manifest.json`,
  `uv.lock`/`bun.lock` (take either side and run `uv lock`/`bun install`), and
  `frontend/src/client/*.gen.ts` (regenerate instead).

### Research
- Read-only: public docs and the Plex/Jellyfin API documentation. Never write to a real
  Plex/Jellyfin server or the owner's music files.

### Review checks
- Every `uv run`/`uv sync` in CI, hooks and scripts passes `--frozen` (ADR 0011).
- Workflow actions pinned to full SHAs with a `# vX.Y.Z` comment, minimal `permissions:`,
  `timeout-minutes`, `persist-credentials: false` (ADR 0012).
- A dependabot-related workflow condition keys off the head branch, not the actor (ADR 0010).
- No `--workers N` or multi-process assumptions (ADR 0005); schedule math goes through the
  configured `TIMEZONE`, not UTC (ADR 0006).
- The FastAPI app's `version=` stays unset (ADR 0008).
- A request-handling change works under both the combined root `Dockerfile` and the dev
  containers (ADR 0003).

## Stack

- Backend: FastAPI, SQLModel, SQLite (ADR 0002), Alembic, self-migrating on startup (ADR 0004).
- Frontend: React/TypeScript, Vite, TanStack Query/Router, Tailwind CSS, shadcn/ui, biome.
- Based on `tiangolo/full-stack-fastapi-template`, minus its auth and Postgres.
- Production: one multi-arch Docker image, built by CircleCI, published to Docker Hub (ADR 0003).
- Skills in `.claude/skills/`, some managed by `library-skills`: run `uvx library-skills --claude`
  after adding or upgrading a backend dependency.

## Decision records

Any real design or architecture decision (removing a template feature, a concurrency or
migration fix, a CI choice that failed and was reverted) gets an ADR:
`docs/decisions/NNNN-title.md`, one page, dated, the decision and the reasoning, not a debate
log. Its line in `docs/decisions/README.md` is added, or edited for an amendment, in the same PR.
