import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
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
  options?: {
    billingActionsController?: PortalBillingInteractionsController;
    focus?: "billing" | "usage";
    managementMode?: "manage" | "visibility";
    membershipRole?: "admin" | "user";
  },
) {
  const billingActionsController: PortalBillingInteractionsController =
    options?.billingActionsController ?? {
    cancelSubscription: vi.fn(async () => ({
      action: "cancel_subscription" as const,
      billingPeriodEnd: null,
      billingStatus: "active",
      changeType: "cancellation_scheduled",
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
    currentMembership: {
      role: options?.membershipRole ?? "admin",
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
  };

  render(
    <VerifyForGoodMantineProvider defaultColorScheme="light">
      <PortalOrganizationContext.Provider value={value}>
        <UsageBillingPanel
          billingActionsController={billingActionsController}
          controller={controller}
          endpoints={endpoints}
          focus={options?.focus ?? "billing"}
          managementMode={options?.managementMode ?? "manage"}
          plansController={plansController}
          session={createMockPortalSession()}
        />
      </PortalOrganizationContext.Provider>
    </VerifyForGoodMantineProvider>,
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
        pendingChangeType: "downgrade_scheduled",
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
      screen.queryByRole("heading", { name: "Usage and billing state" }),
    ).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Current subscription" }),
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
    expect(screen.getByRole("heading", { name: "Manage plans" })).toBeTruthy();
    expect(screen.getByText("Current billing plan")).toBeTruthy();
    expect(screen.getAllByText("Effective access").length).toBeGreaterThan(0);
    expect(screen.getByText("Scheduled downgrade")).toBeTruthy();
    expect(
      screen.getAllByRole("button", { name: "Schedule downgrade" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("button", { name: "Keep this plan" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Cancel at period end" }),
    ).toBeTruthy();

    vi.useRealTimers();
  });

  it("supports a usage-first emphasis on the shared usage-billing route", () => {
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
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 10000,
          metrics: [
            {
              lastUpdated: "2026-03-28T00:00:00Z",
              metricType: "api_requests",
              requestCount: 800,
            },
            {
              lastUpdated: "2026-03-28T00:00:00Z",
              metricType: "search_requests",
              requestCount: 120,
            },
          ],
          periodLabel: "Current month",
          remaining: 9200,
          source: "backend_usage_summary",
          totals: {
            apiRequests: 800,
            enrichmentRequests: 0,
            filingLookupRequests: 0,
            nonprofitLookupRequests: 400,
            searchRequests: 120,
          },
          used: 800,
          usagePercent: 8,
        },
      },
    };
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [],
      reload,
    };

    renderWithOrganization(controller, plansController, {
      focus: "usage",
    });

    expect(screen.getByRole("heading", { name: "Usage overview" })).toBeTruthy();
    expect(screen.getByText("800 / 10,000")).toBeTruthy();
    expect(screen.getByText("API requests")).toBeTruthy();
    expect(screen.getByText("Nonprofit lookups")).toBeTruthy();
    expect(screen.getByText("Usage metrics recorded this month")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Subscription is in good standing" }),
    ).toBeTruthy();
  });

  it("renders a read-only billing visibility mode without payment actions", () => {
    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        billingCycleEnd: "2026-04-01T00:00:00+00:00",
        billingCycleStart: "2026-03-01T00:00:00+00:00",
        budgetStatus: {
          allowOverage: false,
          label: "Hard stop enabled at the monthly request limit",
          policySource: "organization_settings",
        },
        effectiveAccessPlan: "growth",
        effectiveAccessPlanDisplayName: "Growth",
        enabledCapabilities: ["verification", "financial_trends", "risk_flags"],
        featureFlags: [
          {
            enabled: true,
            flagKey: "enable_advanced_reporting",
            label: "Advanced reporting",
            overrideEnabled: null,
            planDefault: true,
          },
        ],
        includedLimits: {
          batchItems: 100,
          monthlyRequests: 10000,
          requestsPerMinute: 120,
        },
        notice: null,
        pendingChangeType: "downgrade_scheduled",
        pendingDowngradeEffectiveAt: "2026-04-01T00:00:00+00:00",
        pendingDowngradePlan: "starter",
        plan: "growth",
        planDisplayName: "Growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        subscriptionStatus: "active",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 10000,
          periodLabel: "Current month",
          remaining: 9200,
          source: "mock_plan_baseline",
          used: 800,
          usagePercent: 8,
        },
      },
    };
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [],
      reload,
    };

    renderWithOrganization(controller, plansController, {
      managementMode: "visibility",
    });

    expect(
      screen.getByRole("heading", { name: "Subscription visibility" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Included limits" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Enabled capabilities" }),
    ).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Manage plans" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Open billing portal" }),
    ).toBeNull();
    expect(screen.getByText("Advanced reporting")).toBeTruthy();
  });

  it("renders a clean empty state when no usage metrics are available yet", () => {
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
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
        usage: {
          limit: 10000,
          metrics: [],
          periodLabel: "March 2026",
          remaining: 10000,
          source: "backend_usage_summary",
          totals: {
            apiRequests: 0,
            enrichmentRequests: 0,
            filingLookupRequests: 0,
            nonprofitLookupRequests: 0,
            searchRequests: 0,
          },
          used: 0,
          usagePercent: 0,
        },
      },
    };
    const plansController: PortalPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [],
      reload,
    };

    renderWithOrganization(controller, plansController, {
      focus: "usage",
    });

    expect(
      screen.getByText(
        /No tracked usage has been recorded for this organization in the current period yet./i,
      ),
    ).toBeTruthy();
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
        pendingChangeType: null,
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

  it("hides billing mutation controls for non-admin membership", () => {
    const reload = vi.fn(async () => {});
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: true,
          label: "Overage allowed beyond included usage",
          policySource: "backend_default",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
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
          isEffective: true,
          isPending: false,
          pendingLabel: "Pending downgrade",
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

    renderWithOrganization(controller, plansController, {
      membershipRole: "user",
    });

    expect(
      screen.getByText(/Billing controls are limited to organization admins/i),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Current plan" })).toBeNull();
    expect(
      (
        screen.getByRole("button", { name: "Open billing portal" }) as
          | HTMLButtonElement
          | null
      )?.disabled,
    ).toBe(true);
  });

  it("supports scheduling cancellation and refreshing visible subscription state", async () => {
    const reload = vi.fn(async () => {});
    const cancelSubscription = vi.fn(async () => ({
      action: "cancel_subscription" as const,
      billingPeriodEnd: "2026-04-01T00:00:00+00:00",
      billingStatus: "active",
      changeType: "cancellation_scheduled",
      currentPlanCode: "growth",
      effectiveFrom: "2026-03-01T00:00:00+00:00",
      effectiveTo: null,
      kind: "subscription_updated" as const,
      pendingPlanCode: "free",
      pendingPlanEffectiveAt: "2026-04-01T00:00:00+00:00",
      providerBoundary: "backend_managed" as const,
      reused: false,
    }));
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: true,
          label: "Overage allowed beyond included usage",
          policySource: "backend_default",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
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
          isEffective: true,
          isPending: false,
          pendingLabel: "Pending downgrade",
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
          highlighted: false,
          isCurrent: false,
          isEffective: false,
          isPending: false,
          pendingLabel: "Pending downgrade",
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
      ],
      reload,
    };
    const billingActionsController: PortalBillingInteractionsController = {
      cancelSubscription,
      clearError: vi.fn(),
      createSubscription: vi.fn(),
      error: null,
      isPending: false,
      updatePlan: vi.fn(),
    };

    renderWithOrganization(controller, plansController, {
      billingActionsController,
    });

    fireEvent.click(screen.getByRole("button", { name: "Cancel at period end" }));

    await waitFor(() => {
      expect(cancelSubscription).toHaveBeenCalled();
    });
    expect(
      screen.getByText(/Cancellation is scheduled for the end of the current billing period/i),
    ).toBeTruthy();
    expect(screen.getByText("Cancellation at period end")).toBeTruthy();
    expect(reload).toHaveBeenCalled();
  });

  it("supports resuming from a pending cancellation", async () => {
    const reload = vi.fn(async () => {});
    const updatePlan = vi.fn(async () => ({
      action: "update_plan" as const,
      billingPeriodEnd: "2026-04-01T00:00:00+00:00",
      billingStatus: "active",
      changeType: "pending_change_cleared",
      currentPlanCode: "growth",
      effectiveFrom: "2026-03-01T00:00:00+00:00",
      effectiveTo: null,
      kind: "subscription_updated" as const,
      pendingPlanCode: null,
      pendingPlanEffectiveAt: null,
      providerBoundary: "backend_managed" as const,
      reused: false,
    }));
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: true,
          label: "Overage allowed beyond included usage",
          policySource: "backend_default",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: "cancellation_scheduled",
        pendingDowngradeEffectiveAt: "2026-04-01T00:00:00+00:00",
        pendingDowngradePlan: "free",
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
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
          isEffective: true,
          isPending: false,
          pendingLabel: "Pending cancellation",
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
          isCurrent: false,
          isEffective: false,
          isPending: true,
          pendingLabel: "Pending cancellation",
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
      ],
      reload,
    };
    const billingActionsController: PortalBillingInteractionsController = {
      cancelSubscription: vi.fn(),
      clearError: vi.fn(),
      createSubscription: vi.fn(),
      error: null,
      isPending: false,
      updatePlan,
    };

    renderWithOrganization(controller, plansController, {
      billingActionsController,
    });

    fireEvent.click(screen.getByRole("button", { name: "Keep this plan" }));

    await waitFor(() => {
      expect(updatePlan).toHaveBeenCalledWith({ planCode: "growth" });
    });
    expect(
      screen.getByText(/The pending billing change was cleared/i),
    ).toBeTruthy();
  });

  it("opens the backend billing portal for invoices and provider tools", async () => {
    const reload = vi.fn(async () => {});
    const cancelSubscription = vi.fn(async () => ({
      action: "cancel_subscription" as const,
      destinationUrl: "https://billing.example.test/portal",
      kind: "redirect" as const,
      providerBoundary: "backend_managed" as const,
      reused: false,
    }));
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, assign, href: "https://example.com/billing" },
    });
    const controller: PortalUsageBillingController = {
      error: null,
      isLoading: false,
      reload,
      snapshot: {
        billingStatus: "active",
        budgetStatus: {
          allowOverage: true,
          label: "Overage allowed beyond included usage",
          policySource: "backend_default",
        },
        effectiveAccessPlan: "growth",
        notice: null,
        pendingChangeType: null,
        pendingDowngradeEffectiveAt: null,
        pendingDowngradePlan: null,
        plan: "growth",
        renewalDate: "2026-04-01T00:00:00+00:00",
        source: "backend_subscription",
        trialEndsAt: null,
        trialStatus: null,
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
      plans: [],
      reload,
    };
    const billingActionsController: PortalBillingInteractionsController = {
      cancelSubscription,
      clearError: vi.fn(),
      createSubscription: vi.fn(),
      error: null,
      isPending: false,
      updatePlan: vi.fn(),
    };

    renderWithOrganization(controller, plansController, {
      billingActionsController,
    });

    fireEvent.click(screen.getByRole("button", { name: "Open billing portal" }));

    await waitFor(() => {
      expect(cancelSubscription).toHaveBeenCalledWith({
        returnUrl: "https://example.com/billing",
        strategy: "backend_billing_portal",
      });
    });
    expect(assign).toHaveBeenCalledWith("https://billing.example.test/portal");
  });
});
