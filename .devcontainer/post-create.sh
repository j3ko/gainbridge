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

# Shared dev-team workflow (ADR 0015). Each client registers its own plugin;
# failure in one must not skip the other. The old Claude plugin is disabled in
# .claude/settings.json. Network failure must not prevent container creation;
# rerun the affected client's commands below later.
# Claude: register the marketplace and install the plugin at user scope, so one
# copy serves every repo and updates once; .claude/settings.json still enables it
# here. Project registration rewrites the tracked declaration and drops autoUpdate.
# Re-registering at user scope also drops existing user preferences, so only add
# the marketplace when it is absent. Installing again is a no-op. A failed
# listing/parsing step is nonfatal.
if ! { claude_marketplace_state=$(claude plugin marketplace list --json | python3 -c '
import json, sys
registered = any(item["name"] == "j3ko-agents" for item in json.load(sys.stdin))
print("registered" if registered else "missing")') \
    && { if [ "$claude_marketplace_state" = missing ]; then
      claude plugin marketplace add j3ko/agent-plugins --scope user
    fi; } \
    && claude plugin install dev-team@j3ko-agents --scope user; }; then
  echo "post-create: Claude dev-team plugin not installed; see docs/ci-notes.md" >&2
fi

# User-scope registration writes the marketplace into the user settings without
# autoUpdate, so Claude never refreshes it and the project's autoUpdate: true has
# no effect. There is no CLI flag for it: turn it on in the user settings, unless
# the entry is missing or already sets autoUpdate either way.
if ! python3 - "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json" <<'EOF'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    sys.exit(0)
settings = json.loads(path.read_text())
entry = settings.get("extraKnownMarketplaces", {}).get("j3ko-agents")
if isinstance(entry, dict) and "autoUpdate" not in entry:
    entry["autoUpdate"] = True
    path.write_text(json.dumps(settings, indent=2) + "\n")
EOF
then
  echo "post-create: could not turn on Claude auto-update for j3ko-agents; see docs/ci-notes.md" >&2
fi

if ! { codex plugin marketplace add j3ko/agent-plugins \
    && codex plugin add dev-team@j3ko-agents; }; then
  echo "post-create: Codex dev-team plugin not installed; see docs/ci-notes.md" >&2
fi

echo "post-create: In Codex CLI, review and trust the dev-team SessionStart hook in /hooks, then fully restart Codex."
echo "post-create: Fully restart again after the hook reports role changes. Updated plugin bundles may need renewed trust."
