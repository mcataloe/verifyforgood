import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
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
    <VerifyForGoodMantineProvider defaultColorScheme="light">
      <PortalOrganizationContext.Provider value={value}>
        <ApiKeyManager controller={controller} />
      </PortalOrganizationContext.Provider>
    </VerifyForGoodMantineProvider>,
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
      isUpdatingKeyId: null,
      items: [
        {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          description: "Primary production integration",
          display_name: "Existing key",
          key_id: "key_existing",
          last_used_at: null,
          organization_id: "org_123",
          status: "active" as const,
        },
      ],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      updateKey: vi.fn(async () => {}),
      visibleSecret: {
        key: {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          description: "New production key",
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

    const stackedRoot = document.querySelector(".portal-stacked-sections");
    expect(stackedRoot).toBeTruthy();
    expect(screen.queryByText("API Key Management")).toBeNull();
    expect(screen.getByText("Portal Test Org")).toBeTruthy();
    const secretInput = screen.getByLabelText(
      "Plaintext API key",
    ) as HTMLInputElement;
    expect(secretInput.value).not.toBe("");
    expect(secretInput.type).toBe("password");
    expect(screen.getByText("Existing key")).toBeTruthy();
    expect(screen.getByText("Primary production integration")).toBeTruthy();
    expect(screen.getByText("Never Used")).toBeTruthy();
    expect(screen.queryByText("ws_portal_test")).toBeNull();
    expect(screen.queryByText("acct_portal_test")).toBeNull();
    expect(screen.queryByText("key_existing")).toBeNull();

    const initialDividers =
      stackedRoot?.querySelectorAll(".portal-stacked-sections__divider") ?? [];
    expect(initialDividers).toHaveLength(2);

    const stackedPanels = stackedRoot?.querySelectorAll("section");
    expect(stackedPanels).toHaveLength(3);
    expect(stackedRoot?.children[0]).toBe(stackedPanels?.[0]);
    expect(stackedRoot?.children[1]).toBe(initialDividers[0]);
    expect(stackedRoot?.children[2]).toBe(stackedPanels?.[1]);
    expect(stackedRoot?.children[3]).toBe(initialDividers[1]);
    expect(stackedRoot?.children[4]).toBe(stackedPanels?.[2]);

    fireEvent.change(screen.getByRole("textbox", { name: "Display name" }), {
      target: { value: "New production key" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Description" }), {
      target: { value: "For the production worker." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Key" }));
    expect(state.createKey).toHaveBeenCalledWith({
      description: "For the production worker.",
      display_name: "New production key",
    });

    fireEvent.click(screen.getByRole("button", { name: "Reveal API key" }));
    expect(secretInput.type).toBe("text");
    expect(secretInput.value).toBe("csk_demo.secret");

    fireEvent.click(screen.getByRole("button", { name: "Copy key" }));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "csk_demo.secret",
    );
    expect(await screen.findByText("API key copied to clipboard.")).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "Dismiss notification" }),
    );
    await waitFor(() => {
      expect(screen.queryByText("API key copied to clipboard.")).toBeNull();
    });

    fireEvent.click(screen.getByRole("button", { name: "Hide API key" }));
    expect(secretInput.type).toBe("password");

    fireEvent.click(
      screen.getByRole("button", { name: "Edit key Existing key" }),
    );
    const editDialog = await screen.findByRole("dialog", { name: "Edit API Key" });
    fireEvent.change(within(editDialog).getByRole("textbox", { name: "Display name" }), {
      target: { value: "Renamed key" },
    });
    fireEvent.change(within(editDialog).getByRole("textbox", { name: "Description" }), {
      target: { value: "Updated description" },
    });
    fireEvent.click(within(editDialog).getByRole("button", { name: "Save" }));
    expect(state.updateKey).toHaveBeenCalledWith("key_existing", {
      description: "Updated description",
      display_name: "Renamed key",
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Edit API Key" })).toBeNull();
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Revoke key Existing key" }),
    );
    expect(state.revokeKey).not.toHaveBeenCalled();
    const revokeDialog = await screen.findByRole("dialog", { name: "Revoke API Key" });
    fireEvent.click(within(revokeDialog).getByRole("button", { name: "Revoke" }));
    expect(state.revokeKey).toHaveBeenCalledWith("key_existing");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(state.dismissSecret).toHaveBeenCalled();
  });

  it("removes the one-time secret section and its trailing separator when no secret is visible", () => {
    const state: PortalApiKeysState = {
      createKey: vi.fn(async () => {}),
      dismissSecret: vi.fn(),
      error: null,
      implementation: "backend",
      isCreating: false,
      isLoading: false,
      isRevokingKeyId: null,
      isUpdatingKeyId: null,
      items: [],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      updateKey: vi.fn(async () => {}),
      visibleSecret: null,
    };

    renderWithOrganization(state);

    const stackedRoot = document.querySelector(".portal-stacked-sections");
    expect(stackedRoot).toBeTruthy();
    expect(screen.queryByText("Copy Secret")).toBeNull();

    const dividers =
      stackedRoot?.querySelectorAll(".portal-stacked-sections__divider") ?? [];
    expect(dividers).toHaveLength(1);

    const stackedPanels = stackedRoot?.querySelectorAll("section");
    expect(stackedPanels).toHaveLength(2);
    expect(stackedRoot?.children[0]).toBe(stackedPanels?.[0]);
    expect(stackedRoot?.children[1]).toBe(dividers[0]);
    expect(stackedRoot?.children[2]).toBe(stackedPanels?.[1]);
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
      isUpdatingKeyId: null,
      items: [],
      refresh: vi.fn(async () => {}),
      revokeKey: vi.fn(async () => {}),
      updateKey: vi.fn(async () => {}),
      visibleSecret: {
        key: {
          created_at: "2026-03-21T00:00:00Z",
          created_by_user_id: "user_verifyforgood_demo",
          description: "New production key",
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
