import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { CustomerUserProfilePage } from "./CustomerUserProfilePage";

describe("CustomerUserProfilePage", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
  });

  it("renders profile fields, account context, and appearance controls", () => {
    renderWithOrganization(
      <CustomerUserProfilePage
        environment="test"
        session={createMockPortalSession({ roles: ["customer_user"] })}
      />,
    );

    expect(screen.getByRole("heading", { name: "Profile" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Personal information" }),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Account context" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Appearance" })).toBeTruthy();
    expect(screen.getByLabelText("First Name")).toBeTruthy();
    expect(screen.getByLabelText("Last Name")).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Pronouns")).toBeTruthy();
    expect(screen.getByLabelText("Avatar upload")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Auto" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Light" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dark" })).toBeTruthy();
    expect(screen.getByText("Portal Test Org")).toBeTruthy();
    expect(screen.getByText("test")).toBeTruthy();
    expect(screen.getByText("User")).toBeTruthy();
    expect(screen.queryByText("Profile details")).toBeNull();
  });

  it("persists appearance selection through the shared color-scheme storage key", () => {
    renderWithOrganization(
      <CustomerUserProfilePage
        environment="test"
        session={createMockPortalSession({ roles: ["customer_user"] })}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Dark" }));

    expect(window.localStorage.getItem("verifyforgood-color-scheme")).toBe(
      "dark",
    );
  });
});

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

function renderWithOrganization(element: ReactNode) {
  const value: PortalOrganizationContextValue = {
    activeOrganization: {
      account_id: "acct_portal_test",
      billing_allow_overage: false,
      billing_monthly_request_cap: 800,
      organization_name: "Portal Test Org",
      scope_source: "backend_settings",
      settings_source: "stored",
      updated_at: "2026-03-21T00:00:00Z",
      workspace_id: "ws_portal_test",
    },
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "user",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: async () => {},
    refreshMembers: async () => [],
    selectionStatus: "active",
    setMembers: () => {},
    setActiveOrganization: () => {},
    status: "ready",
  };

  return render(
    <PortalOrganizationContext.Provider value={value}>
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        {element}
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
