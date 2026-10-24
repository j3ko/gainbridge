#!/usr/bin/env bash
# Runs once when the container is created (devcontainer.json's postCreateCommand).
set -euo pipefail

# The base image can lag behind security fixes to the trust stores. Debian's
# ca-certificates 20250419+deb13u1 and pip 26.2.2 (whose vendored certifi is 2026.10.19)
# drop "emSign ECC Root CA - G3", whose intermediates' private keys are guessable (the
# eMudhra/emSign incident, 2026-10). Both steps are no-ops once the image has caught up.
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --only-upgrade ca-certificates
if ! python -c 'import sys
from importlib.metadata import version
sys.exit(tuple(map(int, version("pip").split(".")[:3])) < (26, 2, 2))'; then
  # By URL and hash, so the upgrade doesn't depend on the old pip's certifi.
  sudo python -m pip install -q --root-user-action=ignore \
    "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
fi

# Install Playwright's Chromium build + its system deps once, so browser-driven checks
# (e.g. Playwright tests, or an agent verifying the UI) don't need to install anything
# on demand. Then install the prek git hook so lint/format is enforced on every commit
# automatically, rather than depending on a developer running `uv run prek install` by
# hand (see development.md).
(cd frontend && bunx playwright install --with-deps chromium)
uv run --frozen prek install
