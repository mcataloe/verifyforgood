import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@charity-status/shared-api";
import { createPortalApiKeyService } from "./apiKeys";

describe("portal api key service", () => {
  it("uses the org-scoped backend routes for list, create, and revoke", async () => {
    const get = vi.fn(async () => ({
      items: [
        {
          created_at: "2026-03-29T00:00:00Z",
          created_by_user_id: "user_admin",
          display_name: "Server integration",
          key_id: "key_existing",
          last_used_at: null,
          organization_id: "org_123",
          status: "active" as const,
        },
      ],
    }));
    const post = vi.fn(async () => ({
      api_key: {
        created_at: "2026-03-29T00:00:00Z",
        created_by_user_id: "user_admin",
        display_name: "Server integration",
        key_id: "key_existing",
        last_used_at: null,
        organization_id: "org_123",
        status: "active" as const,
      },
      secret: "csk_key_existing.secret",
    }));
    const deleteKey = vi.fn(async () => ({
      created_at: "2026-03-29T00:00:00Z",
      created_by_user_id: "user_admin",
      display_name: "Server integration",
      key_id: "key_existing",
      last_used_at: "2026-03-30T00:00:00Z",
      organization_id: "org_123",
      status: "revoked" as const,
    }));
    const service = createPortalApiKeyService({
      apiClient: {
        delete: deleteKey,
        get,
        patch: vi.fn(),
        post,
        put: vi.fn(),
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
      } as unknown as ApiClient,
    });

    const created = await service.createKey({
      display_name: "Server integration",
    });
    const listed = await service.listKeys();
    const revoked = await service.revokeKey("key_existing");

    expect(created.secret).toBe("csk_key_existing.secret");
    expect(created.api_key.display_name).toBe("Server integration");
    expect(listed.items).toHaveLength(1);
    expect(post).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "createCurrentOrganizationApiKey",
      }),
      {
        body: {
          display_name: "Server integration",
        },
      },
    );
    expect(revoked.status).toBe("revoked");
    expect(String((deleteKey.mock.calls as unknown[][])[0]?.[0])).toContain(
      "/organizations/current/api-keys/key_existing",
    );
  });
});
