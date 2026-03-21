# Shared API Package

`@charity-status/shared-api` is the single frontend integration layer for backend HTTP calls.

It centralizes:

- API base URL and version handling
- endpoint descriptors for shared backend routes
- JSON request and response handling
- normalized API error shaping
- header composition, including future auth token injection

## What Belongs Here

- backend route definitions that are reused across frontend surfaces
- generic request helpers that understand the backend response envelope
- transport-level error normalization
- shared request conventions for `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`

## What Stays App-Local

- portal workflow decisions and billing UX
- marketing-specific form behavior or lead routing
- docs-site content structure and examples
- feature-specific data mappers that are only used by one surface

This package should not become an endpoint-by-endpoint business SDK or a junk drawer for app logic.

## Core Exports

- `createApiClient(...)`
  - creates a reusable client with runtime config, optional custom `fetch`, and optional `headersProvider`
- `requestEnvelope(...)`
  - returns the full backend envelope when callers need `request_id`, `meta`, `plan`, or `deprecation`
- `requestData(...)`
  - returns the unwrapped `data` payload for normal app usage
- `get`, `post`, `put`, `patch`, `delete`
  - convenience helpers built on the same request pipeline
- `apiEndpoints`
  - shared endpoint catalog grouped by domain
- `buildApiUrl(...)`
  - builds absolute or relative endpoint URLs for display, docs, or navigation cases

## Future Auth Integration

The client accepts an async `headersProvider` callback. That is the intended integration point for future browser session or token injection.

Apps should inject auth headers through that boundary rather than hardcoding authorization logic into each request call.

## Usage Examples

Simple `GET` with unwrapped data:

```ts
import { apiEndpoints, createApiClient } from "@charity-status/shared-api";

const client = createApiClient({
  runtimeConfig,
});

const organizationSettings = await client.get(
  apiEndpoints.organization.settings,
);
```

Typed `POST` using the shared request pipeline:

```ts
import { apiEndpoints, post } from "@charity-status/shared-api";

const tokenResponse = await post<
  { access_token: string },
  { client_id: string; grant_type: string }
>(apiEndpoints.auth.oauthToken, {
  body: {
    client_id: "local-dev",
    grant_type: "client_credentials",
  },
  runtimeConfig,
});
```

URL-only endpoint consumption for docs or UI hints:

```ts
import { apiEndpoints, buildApiUrl } from "@charity-status/shared-api";

const nonprofitLookupUrl = buildApiUrl(
  apiEndpoints.nonprofits.lookup,
  runtimeConfig,
);
```

## Error Handling

Failures are normalized into `ApiRequestError`, which includes:

- `status`
- `code`
- `message`
- `requestId`
- `details`
- `meta`
- `envelope`
- `payload`
- `rawBody`

This keeps frontend error handling consistent whether the backend responds with the standard envelope, a partial JSON error payload, or a non-JSON failure.
