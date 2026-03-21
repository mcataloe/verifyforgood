import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import { createMockPortalSession } from "../app/portalSession";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalUsageBillingController } from "./usePortalUsageBilling";
import { UsageBillingPanel } from "./UsageBillingPanel";

const endpoints: PortalEndpoints = {
  billingCheckout: "/v1/organization/billing/checkout-session",
  billingPlanChange: "/v1/organization/billing/plan-change",
  billingPortal: "/v1/organization/billing/portal-session",
  billingSubscription: "/v1/organization/billing/subscription",
  nonprofitFilings: "/v1/nonprofit/{ein}/filings",
  nonprofitLookup: "/v1/nonprofit/{ein}",
  nonprofitSearch: "/v1/nonprofits/search",
  oauthToken: "/v1/oauth/token",
  organizationSettings: "/v1/organization/settings",
};

function renderWithOrganization(controller: PortalUsageBillingController) {
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
  };

  render(
    <PortalOrganizationContext.Provider value={value}>
      <UsageBillingPanel
        controller={controller}
        endpoints={endpoints}
        session={createMockPortalSession()}
      />
    </PortalOrganizationContext.Provider>,
  );
}

describe("UsageBillingPanel", () => {
  it("renders request usage and billing state clearly", () => {
    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: false,
          label: "Hard stop enabled at the monthly request limit",
          policySource: "organization_settings",
        },
        effectiveAccessPlan: "growth",
        notice: "Subscription state comes from the backend.",
        pendingDowngradeEffectiveAt: "2026-04-01T00:00:00+00:00",
        pendingDowngradePlan: "starter",
        plan: "pro",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 100000,
          periodLabel: "Current month",
          remaining: 81000,
          source: "mock_plan_baseline",
          used: 19000,
          usagePercent: 19,
        },
      },
    };

    renderWithOrganization(controller);

    expect(
      screen.getByRole("heading", { name: "Usage and billing state" }),
    ).toBeTruthy();
    expect(screen.getByText("19,000 / 100,000")).toBeTruthy();
    expect(
      screen.getByText("Hard stop enabled at the monthly request limit"),
    ).toBeTruthy();
    expect(
      screen.getByText("/v1/organization/billing/subscription"),
    ).toBeTruthy();
    expect(screen.getByText("starter")).toBeTruthy();
  });

  it("renders an error state and supports retry", () => {
    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: "Billing summary failed.",
      isLoading: false,
      reload,
      snapshot: null,
    };

    renderWithOrganization(controller);

    fireEvent.click(
      screen.getByRole("button", { name: "Retry billing summary" }),
    );

    expect(screen.getByText("Billing summary failed.")).toBeTruthy();
    expect(reload).toHaveBeenCalled();
  });
});
