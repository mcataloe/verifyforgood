import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PricingPlanCatalogResponse } from "@charity-status/shared-types";
import { ApiRequestError } from "@charity-status/shared-api";
import {
  useMarketingPricingPlans,
  type MarketingPricingPlansController,
} from "./useMarketingPricingPlans";

const runtimeConfig = {
  apiBaseUrl: "https://dev.charitystatusapi.com",
  apiVersion: "v1",
  environment: "development",
} as const;

function HookHarness({
  apiClient,
  runtime = runtimeConfig,
}: {
  apiClient: { get: () => Promise<PricingPlanCatalogResponse> };
  runtime?: typeof runtimeConfig;
}) {
  const controller = useMarketingPricingPlans(runtime, apiClient);

  return <HookState controller={controller} />;
}

function HookState({
  controller,
}: {
  controller: MarketingPricingPlansController;
}) {
  return (
    <div>
      <span data-testid="loading">
        {controller.isLoading ? "loading" : "idle"}
      </span>
      <span data-testid="error">{controller.error ?? ""}</span>
      <span data-testid="count">{String(controller.plans.length)}</span>
      <button type="button" onClick={() => void controller.reload()}>
        reload
      </button>
    </div>
  );
}

describe("useMarketingPricingPlans", () => {
  it("loads plans through the shared public catalog client", async () => {
    const apiClient = {
      get: vi.fn(async () => ({
        plans: [
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
        ],
      })),
    };

    render(<HookHarness apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("idle");
    });

    expect(screen.getByTestId("count").textContent).toBe("1");
    expect(screen.getByTestId("error").textContent).toBe("");
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  it("keeps a stable error state and logs diagnostics in development", async () => {
    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => undefined);
    const apiClient = {
      get: vi.fn(async () => {
        throw new ApiRequestError("Not found", {
          code: "not_found",
          details: null,
          envelope: null,
          meta: null,
          payload: null,
          rawBody: null,
          requestId: "req_marketing_404",
          status: 404,
        });
      }),
    };

    render(<HookHarness apiClient={apiClient} />);

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("idle");
    });

    expect(screen.getByTestId("error").textContent).toBe(
      "The pricing catalog could not be loaded.",
    );
    expect(screen.getByTestId("count").textContent).toBe("0");
    expect(consoleError).toHaveBeenCalledWith(
      "Marketing pricing catalog request failed",
      expect.objectContaining({
        hint: expect.stringContaining("GET /v1/plans"),
        requestId: "req_marketing_404",
        status: 404,
        targetUrl: "https://dev.charitystatusapi.com/v1/plans",
      }),
    );

    consoleError.mockRestore();
  });
});
