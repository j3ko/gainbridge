# 0001: Single-user, no authentication

Date: 2026-08-06

## Decision

Run gainbridge as a single-user tool with no login, no `User` model, and no JWT auth. The
`tiangolo/full-stack-fastapi-template` this project is based on ships multi-user auth (JWT
login/signup, password recovery, an admin-managed `User` model, an `Item` demo resource); all of
it was removed, along with the frontend's `Admin`/`UserSettings`/`AuthLayout` components and the
`useAuth` hook.

## Reasoning

gainbridge syncs ReplayGain tags for one person's music library, run locally or on a private
network the owner already controls. The template's auth exists for a multi-tenant SaaS shape this
project doesn't have — every login screen, JWT secret, and password-reset flow would be surface
area protecting against a threat model (other users) that doesn't apply here.

## Consequence

The app has zero access control — anyone who can reach its port can use it. Acceptable behind a
private network or `localhost`; would need revisiting (e.g. auth at the reverse-proxy level) before
ever exposing it beyond that. Because the inherited `User`/`Item` models and their Alembic
migration history were never released, they were squashed into a single initial migration matching
the current `Source`/`Job` schema rather than kept as dead history.
