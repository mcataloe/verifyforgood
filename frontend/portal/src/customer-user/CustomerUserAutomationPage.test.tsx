import { fireEvent, render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { CustomerUserAutomationPage } from "./CustomerUserAutomationPage";

describe("CustomerUserAutomationPage", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: createStorageMock(),
    });
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn(async () => {}),
      },
    });
  });

  it("renders the general automation pane with only the hard-stop control", () => {
    renderWithOrganization(
      <CustomerUserAutomationPage
        pane="automation-general"
        session={createMockPortalSession({ roles: ["customer_user"] })}
      />,
    );

    expect(screen.getByText("Enable hard-stop enforcement")).toBeTruthy();
    expect(screen.queryByLabelText("API key name")).toBeNull();
    expect(screen.queryByLabelText("OAuth client name")).toBeNull();
  });

  it("creates masked API keys and confirms deletion in a modal", async () => {
    const { container } = renderWithOrganization(
      <CustomerUserAutomationPage
        pane="automation-api"
        session={createMockPortalSession({ roles: ["customer_user"] })}
      />,
    );

    fireEvent.change(screen.getByLabelText("API key name"), {
      target: { value: "Primary automation key" },
    });
    fireEvent.change(screen.getByLabelText("API key expiration date"), {
      target: { value: "2026-12-31" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add API key" }));

    expect(
      await screen.findByRole("heading", { name: "Primary automation key" }),
    ).toBeTruthy();
    expect(screen.getByText(/^\*+$/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Reveal API key" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copy API key" })).toBeTruthy();
    expect(container.querySelector(".portal-credential-card")).toBeNull();
    expect(container.querySelector(".portal-credential-entry")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Delete API key" }));

    expect(document.body.getAttribute("data-scroll-locked")).toBe("1");
  });

  it("creates OAuth clients with masked client_id and client_secret fields", async () => {
    const { container } = renderWithOrganization(
      <CustomerUserAutomationPage
        pane="automation-oauth"
        session={createMockPortalSession({ roles: ["customer_user"] })}
      />,
    );

    fireEvent.change(screen.getByLabelText("OAuth client name"), {
      target: { value: "Background sync client" },
    });
    fireEvent.change(screen.getByLabelText("OAuth client expiration date"), {
      target: { value: "2026-12-31" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add OAuth client" }));

    expect(
      await screen.findByRole("heading", { name: "Background sync client" }),
    ).toBeTruthy();
    expect(screen.getByText("Client ID")).toBeTruthy();
    expect(screen.getByText("Client secret")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Reveal OAuth credentials" }),
    ).toBeTruthy();
    expect(container.querySelector(".portal-credential-card")).toBeNull();
    expect(container.querySelector(".portal-credential-entry")).toBeTruthy();
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
    apiClient: {
      delete: vi.fn(),
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      requestData: vi.fn(),
      requestEnvelope: vi.fn(),
      put: vi.fn(async () => ({})),
    } as never,
    currentMembership: {
      role: "user",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: vi.fn(async () => {}),
    refreshMembers: vi.fn(async () => []),
    selectionStatus: "active",
    setMembers: vi.fn(),
    setActiveOrganization: vi.fn(),
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
