import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it, vi } from "vitest";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "./usePortalOrganization";
import { TeamManagementPanel } from "./TeamManagementPanel";

function resolveMockPath(path: unknown) {
  if (typeof path === "string") {
    return path;
  }
  if (typeof path === "object" && path !== null && "path" in path) {
    return String((path as { path?: unknown }).path ?? "");
  }
  return String(path);
}

describe("TeamManagementPanel", () => {
  it("renders invitation lifecycle rows and requires confirmation before removal", async () => {
    const deleteMember = vi.fn(async () => ({
      organization_id: "acct_portal_test",
      removed_member_id: "user_member",
    }));
    const get = vi.fn(async (path: unknown) => {
      if (resolveMockPath(path).includes("/invitations")) {
        return {
          items: [
            {
              accepted_at: "2026-03-28T00:00:00Z",
              created_at: "2026-03-27T00:00:00Z",
              email: "accepted@example.org",
              expires_at: "2026-04-03T00:00:00Z",
              invitation_id: "invite_accepted",
              invited_by_user_id: "user_admin",
              role: "user",
              status: "accepted",
            },
            {
              accepted_at: null,
              created_at: "2026-03-29T00:00:00Z",
              email: "pending@example.org",
              expires_at: "2026-04-05T00:00:00Z",
              invitation_id: "invite_pending",
              invited_by_user_id: "user_admin",
              role: "admin",
              status: "pending",
            },
          ],
        };
      }
      return { items: [] };
    });

    renderWithOrganization({
      apiClient: {
        delete: deleteMember,
        get,
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
          email: "newinvite@example.org",
          invitation_id: "invite_new",
          organization_id: "acct_portal_test",
          role: "user",
          status: "pending",
          token: "invtok_123",
        })),
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
        put: vi.fn(),
      } as unknown as PortalOrganizationContextValue["apiClient"],
      members: [
        {
          created_at: "2026-03-27T00:00:00Z",
          email: "jamie.admin@example.org",
          full_name: "Jamie Admin",
          role: "admin",
          status: "active",
          updated_at: "2026-03-27T00:00:00Z",
          user_id: "user_admin",
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
      ],
      refreshMembers: vi.fn(async () => []),
      setMembers: vi.fn(),
    });

    expect(screen.getByRole("heading", { name: "Invitations" })).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByText("accepted@example.org")).toBeTruthy();
      expect(screen.getByText("pending@example.org")).toBeTruthy();
    });
    expect(screen.getByText("accepted")).toBeTruthy();
    expect(screen.getByText("pending")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.getByRole("button", { name: "Confirm remove" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Confirm remove" }));

    await waitFor(() => {
      expect(deleteMember).toHaveBeenCalledOnce();
    });
  });

  it("keeps mutation controls hidden for non-admin members", async () => {
    renderWithOrganization({
      apiClient: {
        delete: vi.fn(),
        get: vi.fn(async (path: unknown) =>
          resolveMockPath(path).includes("/invitations")
            ? { items: [] }
            : { items: [] },
        ),
        patch: vi.fn(),
        post: vi.fn(),
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
        put: vi.fn(),
      } as unknown as PortalOrganizationContextValue["apiClient"],
      currentMembership: {
        role: "user",
        status: "active",
        user_id: "user_admin",
      },
      members: [
        {
          created_at: "2026-03-27T00:00:00Z",
          email: "member@example.org",
          full_name: "Member User",
          role: "user",
          status: "active",
          updated_at: "2026-03-27T00:00:00Z",
          user_id: "user_admin",
        },
      ],
      refreshMembers: vi.fn(async () => []),
    });

    expect(screen.getByText("Read-only team view")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Invite user" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  });

  it("shows newly created invitations in the invitation table after refresh", async () => {
    let invitationItems: Array<Record<string, string | null>> = [];
    const get = vi.fn(async (path: unknown) => {
      if (resolveMockPath(path).includes("/invitations")) {
        return { items: invitationItems };
      }
      return { items: [] };
    });
    const post = vi.fn(async () => {
      invitationItems = [
        {
          accepted_at: null,
          created_at: "2026-03-29T00:00:00Z",
          email: "newinvite@example.org",
          expires_at: "2026-04-05T00:00:00Z",
          invitation_id: "invite_new",
          invited_by_user_id: "user_admin",
          role: "user",
          status: "pending",
        },
      ];
      return {
        email: "newinvite@example.org",
        invitation_id: "invite_new",
        organization_id: "acct_portal_test",
        role: "user",
        status: "pending",
        token: "invtok_123",
      };
    });

    renderWithOrganization({
      apiClient: {
        delete: vi.fn(),
        get,
        patch: vi.fn(),
        post,
        requestData: vi.fn(),
        requestEnvelope: vi.fn(),
        put: vi.fn(),
      } as unknown as PortalOrganizationContextValue["apiClient"],
      refreshMembers: vi.fn(async () => []),
    });

    fireEvent.change(screen.getByLabelText("Invite email"), {
      target: { value: "newinvite@example.org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite user" }));

    await waitFor(() => {
      expect(screen.getByText("newinvite@example.org")).toBeTruthy();
    });
    expect(screen.getByText("Invitation created")).toBeTruthy();
  });
});

function renderWithOrganization(
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
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
      status: "active",
      user_id: "user_admin",
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
        <TeamManagementPanel />
      </VerifyForGoodMantineProvider>
    </PortalOrganizationContext.Provider>,
  );
}
