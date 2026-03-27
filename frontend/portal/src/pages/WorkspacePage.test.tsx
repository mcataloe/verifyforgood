import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { createMockPortalSession } from "../app/portalSession";
import type { PortalEndpoints } from "../app/portalEndpoints";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { WorkspacePage } from "./WorkspacePage";

const endpoints: PortalEndpoints = {
  authLogin: "/v1/auth/login",
  authMe: "/v1/auth/me",
  authRegister: "/v1/auth/register",
  billingCheckout: "/v1/organization/billing/checkout-session",
  billingPlanChange: "/v1/organization/billing/plan-change",
  billingPortal: "/v1/organization/billing/portal-session",
  billingSubscription: "/v1/organization/billing/subscription",
  nonprofitFilings: "/v1/nonprofit/{ein}/filings",
  nonprofitLookup: "/v1/nonprofit/{ein}",
  nonprofitSearch: "/v1/nonprofits/search",
  organizationCreate: "/v1/organizations",
  oauthToken: "/v1/oauth/token",
  organizationSettings: "/v1/organization/settings",
};

describe("WorkspacePage", () => {
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

    renderWithOrganization(
      <WorkspacePage endpoints={endpoints} session={createMockPortalSession()} />,
      {
        apiClient: apiClient as unknown as PortalOrganizationContextValue["apiClient"],
        currentMembership: {
          role: "admin",
          status: "active",
          user_id: "user_verifyforgood_demo",
        },
        members: await refreshMembers(),
        refreshMembers,
        setMembers,
      },
    );

    expect(screen.getByRole("button", { name: "Invite user" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Role for member@example.org"), {
      target: { value: "admin" },
    });

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledOnce();
    });
    expect(setMembers).toHaveBeenCalled();
    expect(screen.getByText("Current user")).toBeTruthy();
  });

  it("keeps membership management read-only for non-admin members", async () => {
    renderWithOrganization(
      <WorkspacePage endpoints={endpoints} session={createMockPortalSession()} />,
      {
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
      },
    );

    expect(screen.queryByRole("button", { name: "Invite user" })).toBeNull();
    expect(screen.getByText("Read-only team view")).toBeTruthy();
    expect(screen.getByText("Current user")).toBeTruthy();
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
    members: [],
    membersStatus: "ready",
    refresh: vi.fn(async () => {}),
    refreshMembers: vi.fn(async () => []),
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
