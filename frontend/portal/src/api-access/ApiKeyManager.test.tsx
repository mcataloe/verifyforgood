import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { ApiKeyManager } from "./ApiKeyManager";
import type { PortalApiKeysState } from "./usePortalApiKeys";

function renderWithOrganization(
  controller: PortalApiKeysState,
  overrides?: Partial<PortalOrganizationContextValue>,
) {
  const value: PortalOrganizationContextValue = {
    activeOrganization: createSessionPortalOrganization({
      account_id: "acct_portal_test",
      auth_method: "mock_browser_session",
      organization_context_status: "active",
      organization_name: "Portal Test Org",
      workspace_id: "ws_portal_test",
    }),
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
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
    ...overrides,
  };

  render(
    <PortalOrganizationContext.Provider value={value}>
      <ApiKeyManager controller={controller} />
    </PortalOrganizationContext.Provider>,
  );
}

describe("ApiKeyManager", () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async () => {}),
      },
    });
  });

  it("creates, copies, and revokes API keys with one-time secret visibility", async () => {
    const state: PortalApiKeysState = {
      createKey: vi.fn(async () => {}),
      dismissSecret: vi.fn(),
      error: null,
      implementation: "backend",
      isCreating: false,
      isLoading: false,
      isRevokingKeyId: null,
      items: [
        {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          display_name: "Existing key",
          key_id: "key_existing",
          last_used_at: null,
          organization_id: "org_123",
          status: "active" as const,
        },
      ],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      visibleSecret: {
        key: {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          display_name: "New key",
          key_id: "key_new",
          last_used_at: null,
          organization_id: "org_123",
          status: "active" as const,
        },
        secret: "csk_demo.secret",
      },
    };

    renderWithOrganization(state);

    expect(screen.getByText("Portal Test Org")).toBeTruthy();
    expect(screen.getByDisplayValue("csk_demo.secret")).toBeTruthy();
    expect(screen.getByText("Existing key")).toBeTruthy();
    expect(screen.getByText("Never used")).toBeTruthy();

    fireEvent.change(screen.getByRole("textbox", { name: "Display name" }), {
      target: { value: "New production key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create API key" }));
    expect(state.createKey).toHaveBeenCalledWith({
      display_name: "New production key",
    });

    fireEvent.click(screen.getByRole("button", { name: "Copy key" }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "csk_demo.secret",
    );

    fireEvent.click(screen.getByRole("button", { name: "Revoke key" }));
    expect(state.revokeKey).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm revoke" }));
    expect(state.revokeKey).toHaveBeenCalledWith("key_existing");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss secret" }));
    expect(state.dismissSecret).toHaveBeenCalled();
  });

  it("shows a manual-copy fallback message when clipboard access fails", async () => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async () => {
          throw new Error("denied");
        }),
      },
    });

    const state: PortalApiKeysState = {
      createKey: vi.fn(async () => {}),
      dismissSecret: vi.fn(),
      error: null,
      implementation: "backend",
      isCreating: false,
      isLoading: false,
      isRevokingKeyId: null,
      items: [],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      visibleSecret: {
        key: {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          display_name: "New key",
          key_id: "key_new",
          last_used_at: null,
          organization_id: "org_123",
          status: "active" as const,
        },
        secret: "csk_demo.secret",
      },
    };

    renderWithOrganization(state);

    fireEvent.click(screen.getByRole("button", { name: "Copy key" }));
    expect(
      await screen.findByText(
        "Copy failed. Copy the API key manually before dismissing it.",
      ),
    ).toBeTruthy();
  });
});
