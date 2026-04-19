import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "@charity-status/shared-api";
import { createPortalApiKeyService } from "./apiKeys";

describe("portal api key service", () => {
  it("uses the org-scoped backend routes for list, create, update, and revoke", async () => {
    const get = vi.fn(async () => ({
      items: [
        {
          created_at: "2026-03-29T00:00:00Z",
          created_by_user_id: "user_admin",
          description: "Production integration",
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
        description: "Production integration",
        display_name: "Server integration",
        key_id: "key_existing",
        last_used_at: null,
        organization_id: "org_123",
        status: "active" as const,
      },
      secret: "csk_key_existing.secret",
    }));
    const patch = vi.fn(async () => ({
      created_at: "2026-03-29T00:00:00Z",
      created_by_user_id: "user_admin",
      description: "Updated description",
      display_name: "Renamed integration",
      key_id: "key_existing",
      last_used_at: null,
      organization_id: "org_123",
      status: "active" as const,
    }));
    const deleteKey = vi.fn(async () => ({
      created_at: "2026-03-29T00:00:00Z",
      created_by_user_id: "user_admin",
      description: "Production integration",
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
        patch,
        post,
        put: vi.fn(),
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
      } as unknown as ApiClient,
    });

    const created = await service.createKey({
      description: "Production integration",
      display_name: "Server integration",
    });
    const listed = await service.listKeys();
    const updated = await service.updateKey("key_existing", {
      description: "Updated description",
      display_name: "Renamed integration",
    });
    const revoked = await service.revokeKey("key_existing");

    expect(created.secret).toBe("csk_key_existing.secret");
    expect(created.api_key.display_name).toBe("Server integration");
    expect(created.api_key.description).toBe("Production integration");
    expect(listed.items).toHaveLength(1);
    expect(post).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "createCurrentOrganizationApiKey",
      }),
      {
        body: {
          description: "Production integration",
          display_name: "Server integration",
        },
      },
    );
    expect(updated.display_name).toBe("Renamed integration");
    expect(updated.description).toBe("Updated description");
    expect(patch).toHaveBeenCalledWith(
      expect.stringContaining("/organizations/current/api-keys/key_existing"),
      {
        body: {
          description: "Updated description",
          display_name: "Renamed integration",
        },
      },
    );
    expect(revoked.status).toBe("revoked");
    expect(String((deleteKey.mock.calls as unknown[][])[0]?.[0])).toContain(
      "/organizations/current/api-keys/key_existing",
    );
  });
});
