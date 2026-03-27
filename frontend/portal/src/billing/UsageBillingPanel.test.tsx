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
import type { PortalBillingInteractionsController } from "./usePortalBillingInteractions";
import type { PortalPricingPlansController } from "./usePortalPricingPlans";
import { UsageBillingPanel } from "./UsageBillingPanel";

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

function renderWithOrganization(
  controller: PortalUsageBillingController,
  plansController: PortalPricingPlansController,
) {
  const billingActionsController: PortalBillingInteractionsController = {
    cancelSubscription: vi.fn(async () => ({
      action: "cancel_subscription" as const,
      billingPeriodEnd: null,
      billingStatus: "active",
      changeType: "updated",
      currentPlanCode: "free",
      effectiveFrom: null,
      effectiveTo: null,
      kind: "subscription_updated" as const,
      pendingPlanCode: null,
      pendingPlanEffectiveAt: null,
      providerBoundary: "backend_managed" as const,
      reused: false,
    })),
    clearError: vi.fn(),
    createSubscription: vi.fn(async () => ({
      action: "create_subscription" as const,
      destinationUrl: "https://example.com/checkout",
      kind: "redirect" as const,
      providerBoundary: "backend_managed" as const,
      reused: false,
    })),
    error: null,
    isPending: false,
    updatePlan: vi.fn(async () => ({
      action: "update_plan" as const,
      billingPeriodEnd: null,
      billingStatus: "active",
      changeType: "updated",
      currentPlanCode: "pro",
      effectiveFrom: null,
      effectiveTo: null,
      kind: "subscription_updated" as const,
      pendingPlanCode: null,
      pendingPlanEffectiveAt: null,
      providerBoundary: "backend_managed" as const,
      reused: false,
    })),
  };

  const value: PortalOrganizationContextValue = {
    activeOrganization: createSessionPortalOrganization({
      account_id: "acct_portal_test",
      auth_method: "mock_browser_session",
      organization_context_status: "active",
      organization_name: "Portal Test Org",
      workspace_id: "ws_portal_test",
    }),
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    refresh: async () => {},
    setActiveOrganization: () => {},
    status: "ready",
  };

  render(
    <PortalOrganizationContext.Provider value={value}>
      <UsageBillingPanel
        billingActionsController={billingActionsController}
        controller={controller}
        endpoints={endpoints}
        plansController={plansController}
        session={createMockPortalSession()}
      />
    </PortalOrganizationContext.Provider>,
  );
}

describe("UsageBillingPanel", () => {
  it("renders request usage and billing state clearly", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-21T12:00:00-05:00"));

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
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [
        {
          highlighted: false,
          isCurrent: false,
          isEffective: false,
          isPending: false,
          plan: {
            display_name: "Free",
            feature_availability: {
              batch_verification: false,
              benchmarking: false,
              financial_trends: false,
              monitoring: false,
              organization_settings: false,
              risk_flags: false,
              state_registry: false,
              verification: true,
            },
            included_usage: {
              batch_items: 0,
              monthly_requests: 250,
              requests_per_minute: 10,
            },
            per_request_pricing: {
              amount_usd_micros: 5000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "free",
          },
        },
        {
          highlighted: true,
          isCurrent: false,
          isEffective: true,
          isPending: false,
          plan: {
            display_name: "Growth",
            feature_availability: {
              batch_verification: true,
              benchmarking: true,
              financial_trends: true,
              monitoring: false,
              organization_settings: false,
              risk_flags: true,
              state_registry: false,
              verification: true,
            },
            included_usage: {
              batch_items: 100,
              monthly_requests: 10000,
              requests_per_minute: 120,
            },
            per_request_pricing: {
              amount_usd_micros: 3000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "growth",
          },
        },
        {
          highlighted: true,
          isCurrent: true,
          isEffective: false,
          isPending: false,
          plan: {
            display_name: "Pro",
            feature_availability: {
              batch_verification: true,
              benchmarking: true,
              financial_trends: true,
              monitoring: true,
              organization_settings: true,
              risk_flags: true,
              state_registry: true,
              verification: true,
            },
            included_usage: {
              batch_items: 1000,
              monthly_requests: 100000,
              requests_per_minute: 600,
            },
            per_request_pricing: {
              amount_usd_micros: 2000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "pro",
          },
        },
        {
          highlighted: true,
          isCurrent: false,
          isEffective: false,
          isPending: true,
          plan: {
            display_name: "Starter",
            feature_availability: {
              batch_verification: false,
              benchmarking: false,
              financial_trends: false,
              monitoring: false,
              organization_settings: false,
              risk_flags: true,
              state_registry: false,
              verification: true,
            },
            included_usage: {
              batch_items: 0,
              monthly_requests: 1000,
              requests_per_minute: 30,
            },
            per_request_pricing: {
              amount_usd_micros: 4000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "starter",
          },
        },
      ],
      reload,
    };

    renderWithOrganization(controller, plansController);

    expect(
      screen.getByRole("heading", { name: "Usage and billing state" }),
    ).toBeTruthy();
    expect(screen.getByText("19,000 / 100,000")).toBeTruthy();
    expect(
      screen.getByText("Hard stop enabled at the monthly request limit"),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        name: "Usage compared with this plan's included quota",
      }),
    ).toBeTruthy();
    expect(screen.getByText("10,000 requests")).toBeTruthy();
    expect(screen.getByText("905 requests / day")).toBeTruthy();
    expect(screen.getByText("About 28,048 requests")).toBeTruthy();
    expect(
      screen.getByText(
        /At this pace, usage would likely exceed the included quota by about 18,048 requests/i,
      ),
    ).toBeTruthy();
    expect(screen.getByText(/\$0\.003 per extra request/i)).toBeTruthy();
    expect(
      screen.getByText("/v1/organization/billing/checkout-session"),
    ).toBeTruthy();
    expect(screen.getAllByText("starter").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Plan catalog" })).toBeTruthy();
    expect(screen.getByText("Current billing plan")).toBeTruthy();
    expect(screen.getAllByText("Effective access").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pending downgrade").length).toBeGreaterThan(0);
    expect(screen.getByText(/createSubscription/i)).toBeTruthy();
    expect(screen.getByText(/cancelSubscription/i)).toBeTruthy();

    vi.useRealTimers();
  });

  it("renders an error state and supports retry", () => {
    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: "Billing summary failed.",
      isLoading: false,
      reload,
      snapshot: null,
    };
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [],
      reload,
    };

    renderWithOrganization(controller, plansController);

    fireEvent.click(
      screen.getByRole("button", { name: "Retry billing summary" }),
    );

    expect(screen.getByText("Billing summary failed.")).toBeTruthy();
    expect(reload).toHaveBeenCalled();
  });

  it("shows trial onboarding state clearly for free-tier accounts", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2099-03-29T00:00:00+00:00"));

    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "trialing",
        budgetStatus: {
          allowOverage: false,
          label: "Hard stop enabled at the monthly request limit",
          policySource: "organization_settings",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "free",
        renewalDate: null,
        source: "backend_subscription",
        trialEndsAt: "2099-04-01T00:00:00+00:00",
        trialStatus: "active",
        usage: {
          limit: 10000,
          periodLabel: "Current month",
          remaining: 6900,
          source: "mock_plan_baseline",
          used: 3100,
          usagePercent: 31,
        },
      },
    };
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [
        {
          highlighted: true,
          isCurrent: true,
          isEffective: false,
          isPending: false,
          plan: {
            display_name: "Free",
            feature_availability: {
              batch_verification: false,
              benchmarking: false,
              financial_trends: false,
              monitoring: false,
              organization_settings: false,
              risk_flags: false,
              state_registry: false,
              verification: true,
            },
            included_usage: {
              batch_items: 0,
              monthly_requests: 250,
              requests_per_minute: 10,
            },
            per_request_pricing: {
              amount_usd_micros: 5000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "free",
          },
        },
        {
          highlighted: true,
          isCurrent: false,
          isEffective: true,
          isPending: false,
          plan: {
            display_name: "Growth",
            feature_availability: {
              batch_verification: true,
              benchmarking: true,
              financial_trends: true,
              monitoring: false,
              organization_settings: false,
              risk_flags: true,
              state_registry: false,
              verification: true,
            },
            included_usage: {
              batch_items: 100,
              monthly_requests: 10000,
              requests_per_minute: 120,
            },
            per_request_pricing: {
              amount_usd_micros: 3000,
              currency_code: "USD",
              unit: "request",
            },
            plan_code: "growth",
          },
        },
      ],
      reload,
    };

    renderWithOrganization(controller, plansController);

    expect(
      screen.getByRole("heading", { name: "Trial in progress" }),
    ).toBeTruthy();
    expect(screen.getByText("3 days left")).toBeTruthy();
    expect(screen.getByText("6,900 requests")).toBeTruthy();
    expect(
      screen.getByText(
        "There is no automatic paid conversion tied to this trial.",
      ),
    ).toBeTruthy();

    vi.useRealTimers();
  });
});
