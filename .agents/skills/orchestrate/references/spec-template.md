# Hand-off spec template

Fill in every section. "None" is a valid answer; a missing section isn't. Give paths
relative to the repo root: the implementer works in its own worktree.

```markdown
## Goal
<One or two sentences: what this PR achieves and why. One concern only.>

## Read
- <decision record / brief / facts file the change touches, by path>
- (Nothing else. Don't read every decision record.)

## In scope
- `<path>`: <what changes>, at `<function>` / line <n> / `grep -n '<pattern>'`
- `<path to test file>`: <which tests to add>

## Out of scope
- `<path or area>`: <why it's out, if it isn't obvious>

## Decisions already made
- <the choice, and where it's recorded if it's durable>
- (Don't re-decide these. If one doesn't fit reality, stop and report.)

## Acceptance checks
- <behaviour that must hold, as a test name or a command and its expected output>
- A test for each fix or new behaviour that fails without it. Say how each test tells
  the new behaviour apart from what already held (existing validation, a default that
  happens to match), or it may pass without the change.
- The project's full check passes.

## Branch and PR
- Branch: `<type>/<short-description>`
- PR title: `<conventional-commit title>`
- Fix-up round on an existing PR? <no | yes: branch `<name>`, PR #<n>>
- Closes #<n> | none (the issue this PR finishes; the line reaches the PR body with the
  spec, and the tracker closes the issue on merge)
- Attribution: <the commit trailer and PR closing line this session uses, copied
  verbatim: the implementer may not see the session's own instructions>
```

## For a fix-up round

Keep it short: the PR number and branch, the findings to fix (each with file:line and
the failure scenario, copied from the review), and anything that's explicitly not to be
changed. No goal or background beyond that.
