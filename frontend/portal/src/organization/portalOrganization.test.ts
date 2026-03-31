import { describe, expect, it, vi } from "vitest";
import {
  createPortalActiveOrganizationRecord,
  createPortalOrganizationClient,
  loadActivePortalOrganization,
  mapSettingsToPortalOrganization,
  readStoredActiveOrganization,
  resolveActivePortalOrganization,
  resolveAvailablePortalOrganizations,
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

  it("prefers backend organization profile metadata when loading active organization scope", async () => {
    const apiClient = {
      get: vi.fn(async () => ({
        account_id: "org_123",
        billing: {
          allowOverage: false,
          monthlyRequestCap: 900,
        },
        organization: {
          contactEmail: "ops@example.org",
          createdAt: "2026-03-20T00:00:00Z",
          displayName: "Backend Display Name",
          organizationId: "org_123",
          slug: "backend-display-name",
          updatedAt: "2026-03-21T00:00:00Z",
        },
        source: "stored",
        updated_at: "2026-03-21T00:00:00Z",
        workspace_id: "org_123",
      })),
    } as const;

    const organization = await loadActivePortalOrganization({
      apiClient: apiClient as never,
      session: {
        account_id: "org_123",
        auth_method: "portal_browser_session",
        organization_context_status: "active",
        organization_name: "Session Fallback Name",
        workspace_id: "org_123",
      },
    });

    expect(organization.organization_name).toBe("Backend Display Name");
    expect(organization.contact_email).toBe("ops@example.org");
    expect(organization.slug).toBe("backend-display-name");
    expect(organization.organization_id).toBe("org_123");
  });

  it("maps additive organization settings payloads into the shared portal organization model", () => {
    const organization = mapSettingsToPortalOrganization({
      session: {
        account_id: "org_123",
        auth_method: "portal_browser_session",
        organization_context_status: "active",
        organization_name: "Session Name",
        workspace_id: "org_123",
      },
      settings: {
        account_id: "org_123",
        organization: {
          contactEmail: "ops@example.org",
          createdAt: "2026-03-20T00:00:00Z",
          displayName: "Org Profile Name",
          organizationId: "org_123",
          slug: "org-profile-name",
          updatedAt: "2026-03-21T00:00:00Z",
        },
        source: "stored",
        updated_at: "2026-03-22T00:00:00Z",
        workspace_id: "org_123",
      },
    });

    expect(organization.organization_name).toBe("Org Profile Name");
    expect(organization.contact_email).toBe("ops@example.org");
    expect(organization.created_at).toBe("2026-03-20T00:00:00Z");
  });

  it("keeps backend organization context in the available list when /auth/me omits a separate list", () => {
    const organizationContext = createPortalActiveOrganizationRecord({
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
    });

    const resolved = resolveAvailablePortalOrganizations({
      availableOrganizations: [],
      organizationContext,
    });

    expect(resolved).toHaveLength(1);
    expect(resolved[0]?.organization_name).toBe("Verify For Good Org");
  });

  it("prefers a persisted selected organization when it still exists in the available list", () => {
    const organizationContext = createPortalActiveOrganizationRecord({
      account_id: "org_primary",
      membership: {
        role: "admin",
        status: "active",
        user_id: "user_123",
      },
      organization_id: "org_primary",
      organization_name: "Primary Org",
      slug: "primary-org",
      workspace_id: "org_primary",
    });
    const storedOrganization = createPortalActiveOrganizationRecord({
      account_id: "org_secondary",
      membership: {
        role: "user",
        status: "active",
        user_id: "user_123",
      },
      organization_id: "org_secondary",
      organization_name: "Secondary Org",
      slug: "secondary-org",
      workspace_id: "org_secondary",
    });

    const resolved = resolveActivePortalOrganization({
      availableOrganizations: [organizationContext, storedOrganization],
      organizationContext,
      storedOrganization,
    });

    expect(resolved?.organization_id).toBe("org_secondary");
    expect(resolved?.membership.role).toBe("user");
  });
});
