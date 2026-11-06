---
name: orchestrate
description: Coordinate scoped software implementation, verified research and independent PR review using dev-team agents. Use when delegating project work or running its implementation and review loop.
---

# Coordinate the dev team

Keep design decisions and the conversation with the owner in the main session. Delegate bounded detail to an implementer, researcher or reviewer. Handle small mechanical edits directly; a fresh agent is not free.

Before delegating, read the project's instructions and delegation contract. Use its exact setup, check, signing, tracker and PR commands. Read only the decisions and issues the task touches. Existing user authorization carries forward; do not add a new approval gate where the user already authorized the work.

Read the reference for the host you are actually using:

- [Claude Code](references/claude.md): role names, worktree isolation and model overrides.
- [Codex](references/codex.md): role installation, explicit worktree assignment and inherited permissions.

## Handoffs

Settle material design choices before implementation and record durable choices where the project keeps decisions. Give each agent one concern. Use the [spec template](references/spec-template.md) for implementation: exact files, relevant decisions, scope, acceptance checks, branch, PR title and issue.

Use the researcher to verify external facts before relying on them. It reports evidence and proposed documentation wording without making edits or external writes.

Before launching an implementer, establish that the authorized workflow can commit, sign where required, push and open a PR. If a necessary permission is missing, keep the concrete work reviewable and report what needs authorization. Do not start a second agent as a way around a refusal.

## Review loop

1. The implementer opens or updates its scoped PR and reports. Check CI in the main session.
2. Obtain an independent reviewer for code, scripts or CI changes. Docs-only and config-only changes can skip review unless the project requires it.
3. Give the reviewer the PR, branch/head and spec. It uses a separate worktree, runs required checks and reports verified findings.
4. Send actionable findings back as a small fix-up spec on the same PR branch. Fix a few mechanical edits directly when that is cheaper. Re-review when the fix changes logic.
5. Hand the PR to the owner with validation, relevant findings and remaining owner-only actions. Never merge without explicit authorization.

If publication is blocked, leave the required PR review pending. Local inspection may continue, but it does not replace review of the published PR head.

When an agent reports blocked, inspect the exact refusal and leave its worktree available. Do not retry the blocked action under another tool or permission mode. Continue unaffected work. Missing design decisions go back to the owner; routine implementation details stay with the implementer.

## Cost and scope

- Parallelize independent work only after assigning non-overlapping files and worktrees. Do not delegate during planning/discussion unless it is requested or required by the applicable project workflow.
- Keep handoffs, source reads and reports concise. Before resuming an agent, inspect its existing work; a small remaining edit can be completed directly.
- Apply authorization and owner-only restrictions to every agent. Tool availability and credentials do not authorize external messages, settings changes or deployments.
- Put out-of-scope ideas in the project's proposal tracker when it has one. Keep project-specific commands and policies in its own instructions, not this shared plugin.
