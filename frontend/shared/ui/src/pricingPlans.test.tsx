import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { PricingPlanGrid, ThemeRoot } from "./index";

const growthPlan: PricingPlanMetadata = {
  plan_code: "growth",
  display_name: "Growth",
  included_usage: {
    monthly_requests: 10000,
    batch_items: 100,
    requests_per_minute: 120,
  },
  per_request_pricing: {
    amount_usd_micros: 3000,
    currency_code: "USD",
    unit: "request",
  },
  feature_availability: {
    verification: true,
    risk_flags: true,
    financial_trends: true,
    benchmarking: true,
    state_registry: false,
    monitoring: false,
    batch_verification: true,
    organization_settings: false,
  },
};

describe("pricing plan components", () => {
  it("renders backend-driven plan metadata and state badges", () => {
    render(
      <ThemeRoot>
        <PricingPlanGrid
          items={[
            {
              highlighted: true,
              isCurrent: true,
              isEffective: true,
              plan: growthPlan,
            },
          ]}
        />
      </ThemeRoot>,
    );

    expect(screen.getByRole("heading", { name: "Growth" })).toBeTruthy();
    expect(screen.getByText("10,000")).toBeTruthy();
    expect(screen.getByText("$0.003")).toBeTruthy();
    expect(screen.getByText("Current billing plan")).toBeTruthy();
    expect(screen.getByText("Effective access")).toBeTruthy();
    expect(screen.getByText("Batch verification")).toBeTruthy();
    expect(screen.getByText("State registry")).toBeTruthy();
  });
});
