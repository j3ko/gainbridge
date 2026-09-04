# 0012: Pin GitHub Actions to commit SHAs, scope permissions, and run zizmor

Date: 2026-09-04

## Decision

Every third-party action referenced in `.github/workflows/` is pinned to a full commit SHA with a
`# vX.Y.Z` comment (e.g. `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`), not
a floating tag like `@v7`. Every workflow declares `permissions: {}` at the top level and grants
only what each job actually needs. Every job sets `timeout-minutes`. Every `actions/checkout` sets
`persist-credentials: false` unless a later step in the same job genuinely needs the checked-out
credential (see `pre-commit.yml`'s own-repo checkout, annotated inline). A dedicated
`zizmor.yml` workflow runs [zizmor](https://docs.zizmor.sh), a GitHub Actions-specific security
linter, on every push/PR to keep this enforced going forward.

## Reasoning

A floating major-version tag (`@v7`) can be repointed by the action's maintainer - or a compromised
maintainer account - to different code at any time, with no signal in this repo's history. A
pinned SHA can't be silently swapped. The other changes (minimal `permissions:`, `timeout-minutes`,
`persist-credentials: false`) follow the same principle: don't grant a workflow step more access or
runtime than it needs, since any one of them running attacker-controlled code (a compromised
action, a malicious PR in a `pull_request_target` context) has a correspondingly smaller blast
radius.

Noticed by comparing against a sibling project, which already does all of this consistently -
zizmor is almost certainly why: it flags exactly these patterns, so once it's running, drifting
back into unpinned/over-privileged workflows gets caught immediately instead of accumulating.

## Consequence

Bumping an action's version now means updating both the SHA and the version comment (`zizmor
--fix` can update the `persist-credentials` and similar auto-fixable findings automatically, but
not SHA pins without a `GH_TOKEN` to resolve tags - the SHAs in this repo were resolved by hand
against each action's actual current tag). `zizmor.yml` will fail a PR that introduces a new
unpinned action or an overly broad `permissions:` block, so this doesn't require remembering to do
it by convention alone.
