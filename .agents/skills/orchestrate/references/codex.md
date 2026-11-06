# Codex adapter

Use custom agents `dev-team-implementer`, `dev-team-researcher` and `dev-team-reviewer`. Invoke this workflow with `$orchestrate` or select its installed plugin skill.

Custom role files must be installed into the project's `.codex/agents/` before delegation. A skills-only marketplace install does not register them. The agent-plugins repository's `scripts/install_codex.py --project /path/to/project` installs roles and this skill for CLI/IDE use. If the skill is already installed through the plugin marketplace, pass `--agents-only` to avoid duplicate discovery. Never install into a project unless the user authorized that configuration change.

Codex roles inherit the parent's model; the adapters set medium reasoning for implementation/research and high reasoning for review. They also inherit the parent's sandbox and approvals. A read-only role instruction does not create an enforced read-only sandbox.

For implementer and reviewer, create distinct git worktrees before spawning and pass each absolute worktree path in its handoff. Do not assume native subagent creation supplies Claude's `isolation: worktree` behavior. Require commands and edits to stay inside the assigned worktree. A worktree separates files but is not a security boundary.

If the host cannot assign a subagent's working directory reliably, use a separate Codex session launched in that worktree instead of parallel writes in the main checkout. Apply the project's private environment setup in each worktree and leave shared git hooks alone.
