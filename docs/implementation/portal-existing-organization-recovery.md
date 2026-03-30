# Portal Existing Organization Recovery

## Summary

Portal session restore now treats backend organization context as the source of truth.

## Current Behavior

- `GET /v1/auth/me` returns the authenticated user and optional `organization_context`.
- When `organization_context` is present, the portal restores an active organization session immediately and skips onboarding.
- When `organization_context` is absent, the portal clears stale browser-local active-organization storage and keeps the session in the pending onboarding state.

## Temporary Default-Organization Policy

- If a user has multiple active organization memberships, the backend chooses the default organization by newest membership `updated_at`.
- If timestamps are equal, the backend falls back to the lexicographically smallest `organization_id`.
- This policy is temporary until explicit organization selection and switching is implemented in the portal.
