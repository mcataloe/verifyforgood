import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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
      organization_name: "Portal Test Org",
      workspace_id: "ws_portal_test",
    }),
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    refresh: async () => {},
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
  it("creates and revokes API keys with one-time secret visibility", async () => {
    const state: PortalApiKeysState = {
      createKey: vi.fn(async () => {}),
      dismissSecret: vi.fn(),
      error: null,
      implementation: "mock_local_control_plane_gap",
      isCreating: false,
      isLoading: false,
      isRevokingKeyId: null,
      items: [
        {
          account_id: "acct_portal_test",
          created_at: "2026-03-21T00:00:00Z",
          key_id: "key_existing",
          key_prefix: "csk_existing",
          label: "Existing key",
          last_used_at: null,
          scopes: ["verify:read"],
          status: "active" as const,
          workspace_id: "ws_portal_test",
        },
      ],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      scopesPlaceholder: "verify:read",
      visibleSecret: {
        key: {
          account_id: "acct_portal_test",
          created_at: "2026-03-21T00:00:00Z",
          key_id: "key_new",
          key_prefix: "csk_new",
          label: "New key",
          last_used_at: null,
          scopes: ["verify:read"],
          status: "active" as const,
          workspace_id: "ws_portal_test",
        },
        secret: "csk_demo.secret",
      },
    };

    renderWithOrganization(state);

    expect(screen.getByText("Portal Test Org")).toBeTruthy();
    expect(screen.getByText("csk_demo.secret")).toBeTruthy();
    expect(screen.getByText("Existing key")).toBeTruthy();

    fireEvent.change(screen.getByRole("textbox", { name: "Key label" }), {
      target: { value: "New production key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create API key" }));
    expect(state.createKey).toHaveBeenCalledWith({
      label: "New production key",
      scopes: ["verify:read"],
    });

    fireEvent.click(screen.getByRole("button", { name: "Revoke key" }));
    expect(state.revokeKey).toHaveBeenCalledWith("key_existing");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss secret" }));
    expect(state.dismissSecret).toHaveBeenCalled();
  });
});
