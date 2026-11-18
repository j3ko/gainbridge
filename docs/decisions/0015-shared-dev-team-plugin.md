# 0015: Shared dev-team workflow for Claude Code and Codex, isolated by the devcontainer

Date: 2026-11-06

## Decision

Use the shared workflow from `j3ko/agent-plugins`, marketplace `j3ko-agents`.
Claude enables `dev-team@j3ko-agents` and disables the old `dev-team@j3ko` at project
scope in `.claude/settings.json`. The project marketplace declaration sets
`autoUpdate: true`. Post-create registers a missing Claude marketplace at user scope
and installs the plugin at user scope. Existing registrations are reused: Claude
2.1.319 marketplace registration rewrites the target declaration and drops its update
preference (verified 2026-11-09).
The plugin is installed once at user scope: a project-scope install keeps its own
copy and version per checkout, and those copies drifted apart. `.claude/settings.json`
still enables it here; installing again is a no-op.
User-scope registration leaves `autoUpdate` out of `~/.claude/settings.json`, so
the project's `autoUpdate: true` had no effect; post-create sets it on that user
entry unless the entry already sets it either way. Plugin auto-update runs in the
background up to 10 minutes after Claude starts and loads at the next start.

Migration: 2026-11-09. Codex CLI uses the plugin skill and personal roles managed by
its trusted `SessionStart` hook in `$CODEX_HOME/agents` (default `~/.codex/agents`).
The checked-in skill and role copies are removed to avoid duplicate skills and project
roles overriding updated personal roles. Sources are maintained upstream.

Post-create installs both clients independently with nonfatal failure handling. In
Codex CLI, open `/hooks`, select `SessionStart`, review the dev-team synchronization
command and trust it. Fully restart Codex to run the hook, then fully restart again
after it reports installed or updated roles. Updated plugin bundles can require
renewed trust. Provisioning never grants hook trust. Locally edited roles are preserved
and conflicts are reported for review. This migration targets the CLI; the pinned IDE
extension remains unchanged.

The devcontainer is Codex's isolation boundary. Post-create installs the Codex CLI and
`.devcontainer/codex.toml` as `/etc/codex/config.toml` (`sandbox_mode =
"danger-full-access"`, `approval_policy = "on-request"`), defaults for both the CLI and
the VS Code extension. The host's `~/.codex` is bind-mounted so Codex's config, auth and
sessions, plugin cache/data and personal roles survive rebuilds, and the extension is declared pinned to
`openai.chatgpt@26.930.61225`. Playwright's one-off CLI in post-create is pinned to
`1.64.1`, the version `frontend/package.json` locks.

It amends ADR 0014's delegation line.

## Why

One maintained source for the workflow and its three roles, instead of diverging Claude
and Codex instructions. Codex's bubblewrap sandbox was seen failing to create namespaces
in this kind of devcontainer (`EPERM` under Docker's AppArmor/seccomp confinement), and OpenAI supports a
dev container as the outer boundary when the inner sandbox can't run. Newer builds of the
Codex extension failed to start in the devcontainer on 2026-11-05; `26.930.61225` is the
last one verified working. Playwright's one-off CLI is pinned
because on 2026-11-05 npm served `playwright@1.65.0` while its exact dependency
`playwright-core@1.65.0` returned 404, so an unpinned `bunx playwright` failed post-create.

## Consequences

- Claude invokes `/dev-team:orchestrate`; Codex selects the installed plugin’s `orchestrate` skill.
- Claude marketplace updates are enabled for this project; Codex checks for plugin updates
  at startup. Role synchronization requires a trusted hook and a full restart to load changes.
- Codex can reach every file, mounted credential and network inside the container: for
  trusted repos only. User or session settings that select an inner sandbox override the
  defaults and can bring back the namespace failure.
- `initializeCommand` creates `~/.codex` and the other mount sources on a Linux/macOS
  host, so a fresh machine starts without preparing them by hand.
- Raising a pin means verifying the new version in the devcontainer first.
- A `@playwright/test` bump also bumps post-create's pin.
- Existing containers can install the Codex plugin with `codex plugin marketplace add
  j3ko/agent-plugins` and `codex plugin add dev-team@j3ko-agents`, without rebuilding.
  Review hook trust and fully restart as described above.
- Restart clients after a rebuild; fully restart Codex after hook-reported role changes.
