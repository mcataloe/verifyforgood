import { render, screen } from "@testing-library/react";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { describe, expect, it } from "vitest";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { SubscriptionSummaryCard } from "./SubscriptionSummaryCard";
import type { PortalUsageBillingSnapshot } from "./portalUsageBilling";

const freePlan: PricingPlanMetadata = {
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
};

function createSnapshot(
  overrides: Partial<PortalUsageBillingSnapshot>,
): PortalUsageBillingSnapshot {
  return {
    billingStatus: "active",
    budgetStatus: {
      allowOverage: true,
      label: "Overage allowed beyond included usage",
      policySource: "backend_default",
    },
    effectiveAccessPlan: "free",
    notice: null,
    pendingChangeType: null,
    pendingDowngradeEffectiveAt: null,
    pendingDowngradePlan: null,
    plan: "free",
    renewalDate: "2026-04-01T00:00:00+00:00",
    source: "backend_subscription",
    trialEndsAt: null,
    trialStatus: null,
    usage: {
      limit: 250,
      periodLabel: "Current month",
      remaining: 190,
      source: "mock_plan_baseline",
      used: 60,
      usagePercent: 24,
    },
    ...overrides,
  };
}

describe("SubscriptionSummaryCard", () => {
  it("displays active subscriptions clearly", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SubscriptionSummaryCard
          currentPlan={freePlan}
          snapshot={createSnapshot({})}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("alert", { name: "Subscription is in good standing" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0);
    expect(screen.getByText("Apr 1, 2026")).toBeTruthy();
  });

  it("displays trial subscriptions clearly", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SubscriptionSummaryCard
          currentPlan={freePlan}
          snapshot={createSnapshot({
            billingStatus: "trialing",
            trialStatus: "active",
          })}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("alert", { name: "Trial access is active" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Trial").length).toBeGreaterThan(0);
    expect(screen.getByText(/no surprises/i)).toBeTruthy();
  });

  it("displays scheduled cancellation clearly", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SubscriptionSummaryCard
          currentPlan={freePlan}
          snapshot={createSnapshot({
            pendingChangeType: "cancellation_scheduled",
            pendingDowngradeEffectiveAt: "2026-04-01T00:00:00+00:00",
            pendingDowngradePlan: "free",
            plan: "growth",
          })}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("alert", { name: "Cancellation is scheduled" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Cancels soon").length).toBeGreaterThan(0);
  });

  it("displays past-due subscriptions clearly", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SubscriptionSummaryCard
          currentPlan={freePlan}
          snapshot={createSnapshot({
            billingStatus: "past_due",
          })}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("alert", { name: "Billing action needed" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Past due").length).toBeGreaterThan(0);
  });

  it("displays expired subscriptions clearly", () => {
    render(
      <VerifyForGoodMantineProvider defaultColorScheme="light">
        <SubscriptionSummaryCard
          currentPlan={freePlan}
          snapshot={createSnapshot({
            billingStatus: "expired",
            renewalDate: null,
          })}
        />
      </VerifyForGoodMantineProvider>,
    );

    expect(
      screen.getByRole("alert", { name: "Subscription expired" }),
    ).toBeTruthy();
    expect(screen.getAllByText("Expired").length).toBeGreaterThan(0);
    expect(screen.getByText("Not scheduled")).toBeTruthy();
  });
});
