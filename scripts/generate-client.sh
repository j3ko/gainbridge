#! /usr/bin/env bash

set -e
set -x

cd backend
uv run --frozen python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json
cd ..
mv openapi.json frontend/
bun run --filter frontend generate-client
bun run --filter frontend format
