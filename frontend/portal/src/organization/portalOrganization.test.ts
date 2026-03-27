import { describe, expect, it, vi } from "vitest";
import {
  createPortalActiveOrganizationRecord,
  createPortalOrganizationClient,
  readStoredActiveOrganization,
  writeStoredActiveOrganization,
} from "./portalOrganization";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
} as const;

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

function buildEnvelope<TData>(data: TData, errors: Array<{ code: string; message: string }> = []) {
  return {
    api_release: "2026-03-27",
    api_version: "v1",
    data,
    deprecation: {
      recommended_version: null,
      status: "active",
      sunset_date: null,
    },
    errors,
    meta: {},
    plan: "public",
    request_id: "req_portal_org_test",
  };
}

describe("portal organization client", () => {
  it("submits a typed POST /organizations request and returns the bootstrap response", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("https://api.verifyforgood.test/v1/organizations");
      expect(init?.method).toBe("POST");
      expect(init?.body).toBe(
        JSON.stringify({
          name: "Verify For Good Org",
          slug: "verify-for-good-org",
        }),
      );

      return new Response(
        JSON.stringify(
          buildEnvelope({
            account_id: "org_123",
            membership: {
              role: "admin",
              status: "active",
              user_id: "user_123",
            },
            organization_id: "org_123",
            organization_name: "Verify For Good Org",
            slug: "verify-for-good-org",
            workspace_id: "org_123",
          }),
        ),
        {
          headers: { "Content-Type": "application/json" },
          status: 201,
        },
      );
    }) as typeof fetch;
    const client = createPortalOrganizationClient({
      accessToken: "portal_token",
      fetchImpl,
      runtimeConfig,
    });

    const response = await client.createOrganization({
      name: "Verify For Good Org",
      slug: "verify-for-good-org",
    });

    expect(response.organization_name).toBe("Verify For Good Org");
    expect(response.membership.role).toBe("admin");
    const [, requestInit] = vi.mocked(fetchImpl).mock.calls[0] ?? [];
    const headers = requestInit?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer portal_token");
  });

  it("persists the active organization record for future session hydration", () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });

    writeStoredActiveOrganization(
      createPortalActiveOrganizationRecord({
        account_id: "org_123",
        membership: {
          role: "admin",
          status: "active",
          user_id: "user_123",
        },
        organization_id: "org_123",
        organization_name: "Verify For Good Org",
        slug: "verify-for-good-org",
        workspace_id: "org_123",
      }),
    );

    expect(readStoredActiveOrganization()).toMatchObject({
      account_id: "org_123",
      organization_name: "Verify For Good Org",
      workspace_id: "org_123",
    });
  });
});
