# Claude Code adapter

Use plugin-scoped agents `dev-team:implementer`, `dev-team:researcher` and `dev-team:reviewer`. Their native metadata supplies worktree isolation for implementer/reviewer and excludes direct editing tools for researcher.

Load this workflow as `/dev-team:orchestrate`. The adapter defaults to Sonnet for implementation/research and Opus for review. A mechanical task may use a Haiku override when available and appropriate; do not substitute a model the host cannot access.

Pass only the spec and relevant project context. Worktree isolation starts from the project's default branch, so each agent must check out the branch named in its handoff. A fix-up targets the existing PR branch.

Editing-tool exclusions do not make shell commands read-only. Keep the researcher's no-write instructions and the actual session permissions in force.
