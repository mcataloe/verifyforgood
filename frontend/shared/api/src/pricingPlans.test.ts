import { describe, expect, it, vi } from "vitest";
import type { PricingPlanCatalogResponse } from "@charity-status/shared-types";
import { apiEndpoints } from "./endpoints";
import type { ApiClient } from "./request";
import { loadPricingPlanCatalog } from "./pricingPlans";

describe("shared pricing plan catalog loader", () => {
  it("loads the public plan catalog through the shared endpoint catalog", async () => {
    const response: PricingPlanCatalogResponse = {
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
      ],
    };
    const get = vi.fn(async (target: unknown) => {
      expect(target).toBe(apiEndpoints.public.plans);
      return response;
    });

    const apiClient: Pick<ApiClient, "get"> = {
      get: get as ApiClient["get"],
    };

    await expect(loadPricingPlanCatalog(apiClient)).resolves.toEqual(response);
  });
});
