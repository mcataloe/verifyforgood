import { describe, expect, it, vi } from "vitest";
import { apiEndpoints } from "@charity-status/shared-api";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import { createPortalApiClient } from "./portalApiClient";
import { createMockPortalSession } from "./portalSession";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
} as const;

function buildEnvelope<TData>(data: TData) {
  return {
    api_release: "2026-03-20",
    api_version: "v1",
    data,
    deprecation: {
      recommended_version: null,
      status: "active",
      sunset_date: null,
    },
    errors: [],
    meta: {},
    plan: "basic",
    request_id: "req_portal_client",
  };
}

describe("portal shared api integration", () => {
  it("consumes the shared api client with organization-scoped headers", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify(buildEnvelope({ mode: "self-serve" })), {
          headers: {
            "Content-Type": "application/json",
          },
          status: 200,
        }),
    ) as unknown as typeof fetch;
    const session = createMockPortalSession();
    const client = createPortalApiClient({
      accessToken: "portal_token",
      fetchImpl,
      organization: createSessionPortalOrganization(session),
      runtimeConfig,
      session,
    });

    const data = await client.get<{ mode: string }>(
      apiEndpoints.organization.settings,
    );

    expect(data).toEqual({
      mode: "self-serve",
    });
    expect(fetchImpl).toHaveBeenCalledWith(
      "https://api.verifyforgood.test/v1/organization/settings",
      expect.objectContaining({
        headers: expect.any(Headers),
        method: "GET",
      }),
    );

    const fetchMock = vi.mocked(fetchImpl);
    const [, requestInit] = fetchMock.mock.calls[0] ?? [];
    const headers = requestInit?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer portal_token");
    expect(headers.get("X-Portal-Account-Id")).toBe(session.account_id);
    expect(headers.get("X-Portal-Workspace-Id")).toBe(session.workspace_id);
  });
});
