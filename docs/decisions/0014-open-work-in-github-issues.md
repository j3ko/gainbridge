# 0014: Open work in GitHub issues; read the ADR index, not every ADR

Date: 2026-10-24

## Decision

Decided by the owner on 2026-10-24, following the sibling project polymarket-trader.

- **Open work is a GitHub issue,** one per item, with one or more of five labels:
  - `next`: work to pick up, in progress or next;
  - `owner`: waits on the owner (a settings action, a release, or a decision);
  - `check`: a look-again on or after a date, then close;
  - `proposal`: proposed, not decided; the owner accepts it (it becomes `next`) or closes it;
  - `bug`: a known defect, not yet fixed.

  An issue's body holds what's left and where its inputs are, enough to pick it up cold,
  and is edited when the plan changes. Comments record progress and findings.
- **A PR that finishes an issue says `Closes #N` in its body.** Something noticed beyond
  a task's scope becomes a `proposal` issue rather than being folded in.
- **Done means closed.** The record of finished work is its PR plus the doc that owns that
  kind of thing (an ADR, `docs/ci-notes.md`), not the issue's comments.
- **A session starts** by reading `docs/decisions/README.md` (one line per ADR) and the
  one-line list of open issues, then reads in full only the ADRs and issues its task
  touches. Agent-facing detail that only matters for some tasks (CI and Dependabot
  gotchas) lives in `docs/ci-notes.md`, read when the task touches that area.
- Work is split with the `dev-team` plugin's agents, enabled in `.claude/settings.json`;
  `CLAUDE.md`'s "Delegation contract" is what they read.

## Why

`CLAUDE.md` had grown to carry every CI lesson inline, and every session read every ADR,
so each session and each subagent paid for context most tasks never use. An index scales
as ADRs accumulate and gives the main session a cheap way to choose which ones a spec
names. Issues keep open work next to its history and close themselves on merge, without a
status file to rewrite.

There's no `docs/running.md`, runbooks or wiki: gainbridge has one deploy shape (the
README's `docker run`), and the owner chose not to add them until they're needed.
