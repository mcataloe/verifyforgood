import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemeRoot } from "@charity-status/shared-ui";
import type { MarketingPricingPlansController } from "../pricing/useMarketingPricingPlans";
import { PricingPage } from "./PricingPage";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
} as const;

describe("PricingPage", () => {
  it("renders backend-driven plan cards", () => {
    const controller: MarketingPricingPlansController = {
      error: null,
      isLoading: false,
      plans: [
        {
          plan_code: "free",
          display_name: "Free",
          included_usage: {
            monthly_requests: 250,
            batch_items: 0,
            requests_per_minute: 10,
          },
          per_request_pricing: {
            amount_usd_micros: 5000,
            currency_code: "USD",
            unit: "request",
          },
          feature_availability: {
            verification: true,
            risk_flags: false,
            financial_trends: false,
            benchmarking: false,
            state_registry: false,
            monitoring: false,
            batch_verification: false,
            organization_settings: false,
          },
        },
        {
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
        },
        {
          plan_code: "pro",
          display_name: "Pro",
          included_usage: {
            monthly_requests: 100000,
            batch_items: 1000,
            requests_per_minute: 600,
          },
          per_request_pricing: {
            amount_usd_micros: 2000,
            currency_code: "USD",
            unit: "request",
          },
          feature_availability: {
            verification: true,
            risk_flags: true,
            financial_trends: true,
            benchmarking: true,
            state_registry: true,
            monitoring: true,
            batch_verification: true,
            organization_settings: true,
          },
        },
        {
          plan_code: "enterprise",
          display_name: "Enterprise",
          included_usage: {
            monthly_requests: 1000000,
            batch_items: 5000,
            requests_per_minute: 5000,
          },
          per_request_pricing: {
            amount_usd_micros: 1000,
            currency_code: "USD",
            unit: "request",
          },
          feature_availability: {
            verification: true,
            risk_flags: true,
            financial_trends: true,
            benchmarking: true,
            state_registry: true,
            monitoring: true,
            batch_verification: true,
            organization_settings: true,
          },
        },
      ],
      reload: vi.fn(async () => {}),
    };

    render(
      <ThemeRoot>
        <PricingPage controller={controller} runtimeConfig={runtimeConfig} />
      </ThemeRoot>,
    );

    expect(screen.getByRole("heading", { name: "Free" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Growth" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Pro" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Enterprise" })).toBeTruthy();
    expect(screen.getAllByText("Batch verification").length).toBeGreaterThan(0);
  });

  it("shows a retry state when the plan catalog fails", () => {
    const reload = vi.fn(async () => {});
    const errorMessage = "The pricing catalog could not be loaded.";
    const controller: MarketingPricingPlansController = {
      error: errorMessage,
      isLoading: false,
      plans: [],
      reload,
    };

    render(
      <ThemeRoot>
        <PricingPage controller={controller} runtimeConfig={runtimeConfig} />
      </ThemeRoot>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Retry loading pricing" }),
    );

    expect(screen.getByText(errorMessage)).toBeTruthy();
    expect(reload).toHaveBeenCalled();
  });
});
