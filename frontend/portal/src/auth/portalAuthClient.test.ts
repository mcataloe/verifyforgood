import { describe, expect, it } from "vitest";
import { FRONTEND_ACCESS_ROLE } from "@charity-status/shared-types";
import { createMockPortalAuthClient } from "./portalAuthClient";

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

describe("portal auth client", () => {
  it("persists a mock session with canonical frontend roles", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    const client = createMockPortalAuthClient();

    const session = await client.signIn({
      email: "jamie.admin@example.org",
      method: "password",
      password: "top-secret",
    });
    const restored = await client.getSession();

    expect(session.roles).toEqual([FRONTEND_ACCESS_ROLE.customerAdmin]);
    expect(session.user.email).toBe("jamie.admin@example.org");
    expect(restored?.roles).toEqual([FRONTEND_ACCESS_ROLE.customerAdmin]);
    expect(restored?.user.email).toBe("jamie.admin@example.org");
  });

  it("rejects stored sessions with non-canonical role values", async () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    window.localStorage.setItem(
      "verifyforgood.portal.auth.session",
      JSON.stringify({
        account_id: "acct_invalid",
        auth_method: "mock_browser_session",
        organization_name: "Invalid Workspace",
        plan: "growth",
        roles: ["workspace_owner"],
        scopes: ["portal:access"],
        user: {
          display_name: "Invalid User",
          email: "invalid@example.org",
          subject_id: "user_invalid",
        },
        workspace_id: "ws_invalid",
      }),
    );
    const client = createMockPortalAuthClient();

    expect(await client.getSession()).toBeNull();
  });
});
