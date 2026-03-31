# Portal Existing Organization Recovery

## Summary

Portal session restore now treats backend organization context as the source of truth.

## Current Behavior

- `GET /v1/auth/me` returns the authenticated user and optional `organization_context`.
- `GET /v1/auth/me` now also returns `available_organizations` for active memberships.
- When `organization_context` is present, the portal restores an active organization session immediately and skips onboarding.
- When `organization_context` is absent, the portal clears stale browser-local active-organization storage and keeps the session in the pending onboarding state.

## Selected Organization Precedence

- The backend still resolves `organization_context` as the default active organization.
- If browser-local active-organization storage matches one of the returned `available_organizations`, the portal restores that explicit user selection instead of the backend default.
- If the stored selection is stale or unavailable, the portal falls back to the backend `organization_context`.

## Temporary Default-Organization Policy

- If a user has multiple active organization memberships, the backend chooses the default organization by newest membership `updated_at`.
- If timestamps are equal, the backend falls back to the lexicographically smallest `organization_id`.
- This policy is temporary until explicit organization selection and switching is implemented in the portal.
