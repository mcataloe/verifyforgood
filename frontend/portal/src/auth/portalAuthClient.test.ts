import { describe, expect, it, vi } from "vitest";
import { createPortalAuthClient } from "./portalAuthClient";

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
    request_id: "req_portal_auth_test",
  };
}

describe("portal auth client", () => {
  it("registers, stores the token, and hydrates the current user through /auth/me", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v1/auth/register")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              access_token: "token_register",
              token_type: "Bearer",
              user: {
                email: "person@example.com",
                full_name: "Portal Person",
                user_id: "user_portal_person",
              },
            }),
          ),
          { headers: { "Content-Type": "application/json" }, status: 201 },
        );
      }
      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              user: {
                email: "person@example.com",
                full_name: "Portal Person",
                user_id: "user_portal_person",
              },
            }),
          ),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      }

      return new Response("Not Found", { status: 404 });
    }) as typeof fetch;
    const client = createPortalAuthClient({
      fetchImpl,
      runtimeConfig,
    });

    const state = await client.register({
      email: "person@example.com",
      full_name: "Portal Person",
      password: "top-secret-password",
    });

    expect(state.accessToken).toBe("token_register");
    expect(state.session.user.email).toBe("person@example.com");
    expect(state.session.user.display_name).toBe("Portal Person");
    expect(state.session.account_id).toBe("acct_portal_pending");
    expect(window.localStorage.getItem("verifyforgood.portal.auth.session")).toContain(
      "token_register",
    );
  });

  it("logs in, stores the token, and can restore the session from local storage", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v1/auth/login")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              access_token: "token_login",
              token_type: "Bearer",
              user: {
                email: "person@example.com",
                full_name: "Portal Person",
                user_id: "user_portal_person",
              },
            }),
          ),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      }
      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              user: {
                email: "person@example.com",
                full_name: "Portal Person",
                user_id: "user_portal_person",
              },
            }),
          ),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      }

      return new Response("Not Found", { status: 404 });
    }) as typeof fetch;
    const client = createPortalAuthClient({
      fetchImpl,
      runtimeConfig,
    });

    const loggedIn = await client.login({
      email: "person@example.com",
      password: "top-secret-password",
    });
    const restored = await client.getSession();

    expect(loggedIn.session.user.email).toBe("person@example.com");
    expect(restored?.accessToken).toBe("token_login");
    expect(restored?.session.user.subject_id).toBe("user_portal_person");
    expect(restored?.session.roles).toEqual(["customer_admin"]);
    expect(restored?.session.organization_context_status).toBe("pending");
  });

  it("hydrates a stored active organization into the restored session", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    window.localStorage.setItem(
      "verifyforgood.portal.auth.session",
      JSON.stringify({
        access_token: "token_login",
        token_type: "Bearer",
        user: {
          email: "person@example.com",
          full_name: "Portal Person",
          user_id: "user_portal_person",
        },
      }),
    );
    window.localStorage.setItem(
      "verifyforgood.portal.organization.active",
      JSON.stringify({
        account_id: "org_123",
        membership: {
          role: "admin",
          status: "active",
          user_id: "user_portal_person",
        },
        organization_id: "org_123",
        organization_name: "Verify For Good Org",
        slug: "verify-for-good-org",
        workspace_id: "org_123",
      }),
    );
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope({
              user: {
                email: "person@example.com",
                full_name: "Portal Person",
                user_id: "user_portal_person",
              },
            }),
          ),
          { headers: { "Content-Type": "application/json" }, status: 200 },
        );
      }

      return new Response("Not Found", { status: 404 });
    }) as typeof fetch;
    const client = createPortalAuthClient({
      fetchImpl,
      runtimeConfig,
    });

    const restored = await client.getSession();

    expect(restored?.session.organization_context_status).toBe("active");
    expect(restored?.session.organization_name).toBe("Verify For Good Org");
    expect(restored?.session.account_id).toBe("org_123");
    expect(restored?.session.workspace_id).toBe("org_123");
  });

  it("clears invalid stored tokens when /auth/me returns unauthorized", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    window.localStorage.setItem(
      "verifyforgood.portal.auth.session",
      JSON.stringify({
        access_token: "expired_token",
        token_type: "Bearer",
        user: {
          email: "person@example.com",
          full_name: "Portal Person",
          user_id: "user_portal_person",
        },
      }),
    );
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/v1/auth/me")) {
        return new Response(
          JSON.stringify(
            buildEnvelope(
              {},
              [{ code: "unauthorized", message: "Authentication is required" }],
            ),
          ),
          { headers: { "Content-Type": "application/json" }, status: 401 },
        );
      }

      return new Response("Not Found", { status: 404 });
    }) as typeof fetch;
    const client = createPortalAuthClient({
      fetchImpl,
      runtimeConfig,
    });

    const restored = await client.getSession();

    expect(restored).toBeNull();
    expect(window.localStorage.getItem("verifyforgood.portal.auth.session")).toBeNull();
  });

  it("removes persisted auth state on sign out", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    window.localStorage.setItem(
      "verifyforgood.portal.auth.session",
      JSON.stringify({
        access_token: "persisted_token",
        token_type: "Bearer",
        user: {
          email: "person@example.com",
          full_name: "Portal Person",
          user_id: "user_portal_person",
        },
      }),
    );
    const client = createPortalAuthClient({
      fetchImpl: vi.fn(async () => new Response("Not Found", { status: 404 })) as typeof fetch,
      runtimeConfig,
    });

    await client.signOut();

    expect(window.localStorage.getItem("verifyforgood.portal.auth.session")).toBeNull();
  });
});
