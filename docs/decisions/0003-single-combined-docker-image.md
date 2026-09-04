# 0003: Single, multi-arch Docker image bundling frontend and backend

Date: 2026-08-27

## Decision

Publish one multi-arch (amd64/arm64) production image (`j3ko/gainbridge` on Docker Hub, root-level
`Dockerfile`) that bundles the built frontend into the backend: FastAPI serves the built SPA
directly (a static mount plus an SPA fallback route) when a `static/` directory is present next to
`app/`, which is a no-op for local dev and tests where it never exists. CircleCI builds and pushes
it, tagged `:edge` on every push to `main` and `:latest`/`:vX.Y.Z` on release.

Local development is unaffected — `compose.yml`/`compose.override.yml` still run the backend and
frontend as separate containers/dev servers, via the separate `backend/Dockerfile` and
`frontend/Dockerfile`.

## Reasoning

gainbridge is a personal self-hosted tool, not a multi-tenant service — running it shouldn't
require operating two containers plus a reverse proxy. A single image is simpler to `docker run`
(see the README's quick-start), while keeping the two-container setup for local dev preserves fast
iteration (rebuild/restart one service without touching the other).

## Consequence

Two separate build paths to keep working: the root `Dockerfile` (production, combined) and the
`backend/`/`frontend/` Dockerfiles (local dev, separate). A change to how the backend serves
requests (e.g. routing, static file handling) needs verifying under both. This replaced an earlier
self-hosted-runner + Traefik deploy flow (`deploy-staging.yml`, `deploy-production.yml`,
`compose.traefik.yml`), which was removed in the same change.
