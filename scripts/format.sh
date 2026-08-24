#! /usr/bin/env bash

# Exit in case of error
set -e
set -x

bun run --filter frontend format

cd backend
uv run bash scripts/format.sh
