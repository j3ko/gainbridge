# CI, Dependabot and tooling notes

Read when a task touches `.github/workflows/`, `.circleci/`, `.devcontainer/`, a Dependabot PR,
a lockfile, or a Docker build. Lessons that became decisions are ADRs (0007, 0009–0012); these are the
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

## Devcontainer

- The host's `~/.claude`, `~/.codex` and `~/.config/gh` are bind-mounted; each must exist on the host or the container
  fails to start. Create `~/.codex` on the host before opening a fresh devcontainer if
  it is missing; Codex's config, authentication and sessions then survive rebuilds.
- VS Code installs `openai.chatgpt@26.930.61225` alongside the other extensions. It matches the working
  version on 2026-11-05; newer builds failed to start in the devcontainer. Keep the
  explicit version until a replacement has been verified here. Rebuild the container
  to apply extension and mount changes.
- `post-create.sh` patches `ca-certificates` and pip before anything else (the emSign
  incident, 2026-10); both steps are no-ops once the base image catches up.
- Playwright's one-off CLI is pinned to `1.64.1` in `post-create.sh`, the same version as
  `@playwright/test` in `frontend/package.json` and `frontend/Dockerfile.playwright`'s
  image. On 2026-11-05, npm served `playwright@1.65.0` while its exact dependency
  `playwright-core@1.65.0` returned 404, so an unpinned `bunx` failed during post-create.
  A Dependabot bump of `@playwright/test` must bump this pin too.
- The shared `run` skill lives in `.agents/skills/run`; `.claude/skills/run` links to
  it so both Codex and Claude Code use the same instructions.
- **Codex uses Docker isolation (ADR 0015).** `post-create.sh` installs
  `.devcontainer/codex.toml` as `/etc/codex/config.toml`, container-wide defaults for
  the CLI and the IDE: `danger-full-access`, with `on-request` approvals. User/project
  settings and explicit session overrides take precedence. Restart clients and start a
  new chat after applying it in an existing container; saved chats can keep their
  previous permissions.
- **Shared dev-team (ADR 0015):** post-create installs Claude's `dev-team@j3ko-agents`
  from `j3ko/agent-plugins`; the old `dev-team@j3ko` is disabled for this project. Codex
  reads the committed `.codex/agents/dev-team-*.toml` and `.agents/skills/orchestrate/`
  without a marketplace install. To update that snapshot, clone agent-plugins, check out
  the intended revision, run
  `python3 scripts/install_codex.py --project /workspaces/gainbridge --replace` from that checkout,
  and review the generated diff. Update Claude's plugin in the same change.
