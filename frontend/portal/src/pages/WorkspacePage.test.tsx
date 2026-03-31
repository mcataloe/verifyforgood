import { render, screen } from "@testing-library/react";
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
  organizationDeleteCurrent: "/v1/organizations/current",
  oauthToken: "/v1/oauth/token",
  organizationSettings: "/v1/organization/settings",
};

describe("WorkspacePage", () => {
  it("shows the dedicated nonprofit search surface without team-management sections", async () => {
    renderWithOrganization(
      <WorkspacePage endpoints={endpoints} session={createMockPortalSession()} />,
    );

    expect(
      screen.getByRole("heading", { name: "Nonprofit verification search" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Nonprofit search" }),
    ).toBeTruthy();
    expect(screen.getByText("admin access")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Invite user" })).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Organization details" }),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "Signed-in account" }),
    ).toBeNull();
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
