import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { TeamPage } from "./TeamPage";

describe("TeamPage", () => {
  it("shows admin team controls and updates visible rows after role changes", async () => {
    const refreshMembers = vi.fn(async () => [
      {
        created_at: "2026-03-27T00:00:00Z",
        email: "jamie.admin@example.org",
        full_name: "Jamie Admin",
        role: "admin",
        status: "active",
        updated_at: "2026-03-27T00:00:00Z",
        user_id: "user_verifyforgood_demo",
      },
      {
        created_at: "2026-03-27T00:00:00Z",
        email: "member@example.org",
        full_name: "Member User",
        role: "user",
        status: "active",
        updated_at: "2026-03-27T00:00:00Z",
        user_id: "user_member",
      },
    ]);
    const setMembers = vi.fn();
    const apiClient = {
      delete: vi.fn(async () => ({
        organization_id: "acct_portal_test",
        removed_member_id: "user_member",
      })),
      get: vi.fn(async () => ({ items: [] })),
      patch: vi.fn(async () => ({
        created_at: "2026-03-27T00:00:00Z",
        email: "member@example.org",
        full_name: "Member User",
        role: "admin",
        status: "active",
        updated_at: "2026-03-28T00:00:00Z",
        user_id: "user_member",
      })),
      post: vi.fn(async () => ({
        email: "invitee@example.org",
        invitation_id: "invite_123",
        organization_id: "acct_portal_test",
        role: "user",
        status: "pending",
        token: "invtok_123",
      })),
      requestData: vi.fn(),
      requestEnvelope: vi.fn(),
      put: vi.fn(),
    };

    renderWithOrganization(<TeamPage session={createMockPortalSession()} />, {
      apiClient: apiClient as unknown as PortalOrganizationContextValue["apiClient"],
      currentMembership: {
        role: "admin",
        status: "active",
        user_id: "user_verifyforgood_demo",
      },
      members: await refreshMembers(),
      refreshMembers,
      setMembers,
    });

    expect(screen.getByRole("heading", { name: "Team access" })).toBeTruthy();
    expect(screen.getByText("admin access")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Invite user" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Organization details" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Signed-in account" }),
    ).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Role for member@example.org"), {
      target: { value: "admin" },
    });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledOnce();
    });
    expect(setMembers).toHaveBeenCalled();
    expect(screen.getByText("Current user")).toBeTruthy();
  });

  it("keeps membership management read-only for non-admin members", () => {
    renderWithOrganization(<TeamPage session={createMockPortalSession()} />, {
      currentMembership: {
        role: "user",
        status: "active",
        user_id: "user_verifyforgood_demo",
      },
      members: [
        {
          created_at: "2026-03-27T00:00:00Z",
          email: "jamie.admin@example.org",
          full_name: "Jamie Admin",
          role: "user",
          status: "active",
          updated_at: "2026-03-27T00:00:00Z",
          user_id: "user_verifyforgood_demo",
        },
      ],
    });

    expect(screen.getByRole("heading", { name: "Team access" })).toBeTruthy();
    expect(screen.getByText("user access")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Invite user" })).toBeNull();
    expect(screen.getByText("Read-only team view")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Signed-in account" }),
    ).toBeTruthy();
  });
});

function renderWithOrganization(
  element: ReactNode,
  overrides: Partial<PortalOrganizationContextValue> = {},
) {
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
      del: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
    } as unknown as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: vi.fn(async () => {}),
    refreshMembers: vi.fn(async () => []),
    selectionStatus: "active",
    setActiveOrganization: vi.fn(),
    setMembers: vi.fn(),
    status: "ready",
    ...overrides,
  };

  return render(
    <PortalOrganizationContext.Provider value={value}>
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        {element}
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
