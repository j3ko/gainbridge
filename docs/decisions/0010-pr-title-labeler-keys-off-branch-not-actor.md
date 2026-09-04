# 0010: `pr-title-labeler` must key off the PR's branch, not the pushing actor

Date: 2026-09-04

## Decision

`.github/workflows/labeler.yml`'s `pr-title-labeler` job skips based on whether the PR's head
branch starts with `dependabot/`, not on `github.actor` of the triggering push:

```yaml
if: ${{ !startsWith(github.head_ref, 'dependabot/') && ... }}
```

## Reasoning

The job originally skipped via `github.actor != 'dependabot[bot]'`. That works for dependabot's own
commits, but breaks the moment anyone else pushes a follow-up commit to a `dependabot/*` branch
(e.g. a human fixing something CI caught, like regenerating a stale frontend client after a
`fastapi` bump). The actor for that push is the human, not `dependabot[bot]`, so the condition
flips to true and the job runs - and fails, since the PR's *title* is still dependabot's own
non-Conventional-Commits one (`⬆ bump ...`), unrelated to who pushed the latest commit.

Found via PR #60: after landing its content on `main` and merging `main` back into the PR branch
to clear a lockfile conflict, the PR sat at `changed_files: 0` (a provably empty diff) but never
auto-closed the way every other superseded Dependabot PR in the same batch did. GitHub's
`mergeable_state` was `unstable`, not `clean`, entirely because of this one failing check -
Dependabot's own auto-close-when-superseded logic doesn't fire on a PR that isn't fully clean, even
when the diff itself is empty.

## Consequence

A human pushing a follow-up commit to a `dependabot/*` branch no longer leaves the PR stuck
`unstable`. This only fixes the branch-identity check itself - if a PR's `mergeable_state` ever
gets stuck as `unstable` (not `dirty`) for some other reason after its content is already on
`main`, don't assume clearing a merge conflict alone is enough; check for a lingering failed
status check first, since that alone can block Dependabot's auto-close.
