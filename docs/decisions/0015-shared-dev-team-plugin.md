# 0015: Shared dev-team workflow for Claude Code and Codex, isolated by the devcontainer

Date: 2026-11-06

## Decision

Replace the Claude-only `dev-team@j3ko` (from `j3ko/claude-plugins`, now archived) with
the shared workflow from `j3ko/agent-plugins`, marketplace `j3ko-agents`. Claude enables
`dev-team@j3ko-agents` and disables the old plugin at project scope in
`.claude/settings.json`; post-create installs it. Codex reads the generated roles in
`.codex/agents/dev-team-*.toml` and the `orchestrate` skill in
`.agents/skills/orchestrate/`, checked in unchanged from agent-plugins commit
`9dcadc8`. Refresh them with the upstream installer and review the diff; don't hand-edit them.

The devcontainer is Codex's isolation boundary. Post-create installs the Codex CLI and
`.devcontainer/codex.toml` as `/etc/codex/config.toml` (`sandbox_mode =
"danger-full-access"`, `approval_policy = "on-request"`), defaults for both the CLI and
the VS Code extension. The host's `~/.codex` is bind-mounted so Codex's config, auth and
sessions survive rebuilds, and the extension is declared pinned to
`openai.chatgpt@26.930.61225`. Playwright's one-off CLI in post-create is pinned to
`1.64.1`, the version `frontend/package.json` locks.

The owner's other devcontainers use the same setup, so they stay consistent. It amends ADR 0014's delegation line.

## Why

One maintained source for the workflow and its three roles, instead of diverging Claude
and Codex instructions. In the owner's devcontainers, Codex's bubblewrap sandbox can't
create namespaces (`EPERM` under Docker's AppArmor/seccomp confinement), and OpenAI supports a
dev container as the outer boundary when the inner sandbox can't run. Newer builds of the
Codex extension failed to start in the devcontainer on 2026-11-05; `26.930.61225` is the
last one verified working. Playwright's one-off CLI is pinned
because on 2026-11-05 npm served `playwright@1.65.0` while its exact dependency
`playwright-core@1.65.0` returned 404, so an unpinned `bunx playwright` failed post-create.

## Consequences

- Claude invokes `/dev-team:orchestrate`; Codex invokes `$orchestrate`.
- Codex can reach every file, mounted credential and network inside the container: for
  trusted repos only. User or session settings that select an inner sandbox override the
  defaults and can bring back the namespace failure.
- `~/.codex` must exist on the host before a fresh container opens.
- Raising a pin means verifying the new version in the devcontainer first.
- A `@playwright/test` bump also bumps post-create's pin.
- Restart clients or start a new chat after a rebuild or a refresh of the imported files.
