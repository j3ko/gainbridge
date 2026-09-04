# 0008: Decouple the FastAPI app version from the installed package version

Date: 2026-08-30

## Decision

`FastAPI(title=..., ...)` in `backend/app/main.py` deliberately does not set `version=` from the
installed `app` package's version. The real running version is exposed separately, via
`GET /api/v1/utils/config/` (and surfaced in the frontend footer), not via the OpenAPI schema's
`info.version`.

## Reasoning

Wiring the FastAPI app's version to the package version made the OpenAPI schema change on every
release-please version bump, which in turn changed the generated frontend API client
(`scripts/generate-client.sh`) on every release — a diff with no functional change behind it,
purely because the version string moved.

## Consequence

The OpenAPI schema, and the generated frontend client, stay stable across release-please version
bumps. Anything that needs to know the actual running version (support requests, the UI footer)
must go through `GET /api/v1/utils/config/` rather than reading it off the OpenAPI schema.
