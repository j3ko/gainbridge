#!/usr/bin/env bash
# Runs once when the container is created (devcontainer.json's postCreateCommand).
set -euo pipefail

# The base image can lag behind security fixes to the trust stores. Debian's
# ca-certificates 20250419+deb13u1 and pip 26.2.2 (whose vendored certifi is 2026.10.19)
# drop "emSign ECC Root CA - G3", whose intermediates' private keys are guessable (the
# eMudhra/emSign incident, 2026-10). Both steps are no-ops once the image has caught up.
# The image's own Python by full path: the checkout's .venv survives rebuilds and can
# come first on PATH, and it has no pip.
PY=/usr/local/bin/python
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --only-upgrade ca-certificates
if ! "$PY" -c 'import sys
from importlib.metadata import version
sys.exit(tuple(map(int, version("pip").split(".")[:3])) < (26, 2, 2))'; then
  # By URL and hash, so the upgrade doesn't depend on the old pip's certifi.
  sudo "$PY" -m pip install -q --root-user-action=ignore \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
fi

# Codex CLI for terminal use; the VS Code extension bundles its own executable.
npm install -g @openai/codex

# Docker is Codex's isolation boundary (ADR 0015). Use container-local system
# defaults without editing the host-mounted ~/.codex config.
sudo install -d -m 0755 /etc/codex
sudo install -m 0644 .devcontainer/codex.toml /etc/codex/config.toml

# Playwright's Chromium build + its system deps, so browser-driven checks (Playwright tests,
# or an agent verifying the UI) don't need to install anything on demand.
# Pin the one-off CLI to frontend/package.json's @playwright/test: latest can point at an
# incomplete release (1.65.0 was published while its required playwright-core@1.65.0 was
# still unavailable). Bump the two together.
(cd frontend && bunx playwright@1.64.1 install --with-deps chromium)

# The prek pre-commit git hook, so lint/format/type checks actually block a bad
# `git commit`, not just a documented convention someone has to remember to run.
uv run --frozen prek install

# Shared dev-team workflow (ADR 0015). Claude needs its plugin registration;
# Codex's generated roles and orchestrate skill are already in the checkout.
# The old plugin is disabled for this project in .claude/settings.json.
# Network failure must not prevent container creation; rerun these commands later.
if ! { claude plugin marketplace add j3ko/agent-plugins --scope project \
    && claude plugin install dev-team@j3ko-agents --scope project; }; then
  echo "post-create: shared dev-team plugin not installed; see docs/ci-notes.md" >&2
fi
