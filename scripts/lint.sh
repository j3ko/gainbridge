#! /usr/bin/env bash

# Exit in case of error
set -e
set -x

bun run --filter frontend typecheck
bun run --filter frontend check

cd backend
uv run bash scripts/lint.sh
