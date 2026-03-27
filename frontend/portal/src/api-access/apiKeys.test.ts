import { describe, expect, it } from "vitest";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import {
  createMockPortalApiKeyService,
  defaultPortalApiKeyScopes,
} from "./apiKeys";

function createStorageMock(): Storage {
  const store = new Map<string, string>();

  return {
    clear() {
      store.clear();
    },
    getItem(key) {
      return store.get(key) ?? null;
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
    removeItem(key) {
      store.delete(key);
    },
    setItem(key, value) {
      store.set(key, value);
    },
  };
}

describe("portal api key service", () => {
  it("creates, lists, and revokes keys without persisting plaintext secrets", async () => {
    const storage = createStorageMock();
    const organization = createSessionPortalOrganization({
      account_id: "acct_portal_test",
      auth_method: "mock_browser_session",
      organization_context_status: "active",
      organization_name: "Portal Test Org",
      workspace_id: "ws_portal_test",
    });
    const service = createMockPortalApiKeyService({
      organization,
      storage,
    });

    const created = await service.createKey({
      label: "Server integration",
      scopes: defaultPortalApiKeyScopes(),
    });
    const listed = await service.listKeys();

    expect(created.secret.startsWith("csk_")).toBe(true);
    expect(created.api_key.label).toBe("Server integration");
    expect(listed.items).toHaveLength(1);
    expect(JSON.stringify(listed.items)).not.toContain(created.secret);

    const revoked = await service.revokeKey(created.api_key.key_id);
    expect(revoked.status).toBe("revoked");

    const refreshed = await service.listKeys();
    expect(refreshed.items[0]?.status).toBe("revoked");
  });
});
