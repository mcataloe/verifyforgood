import { describe, expect, it, vi } from "vitest";
import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import { createMockPortalSession } from "../app/portalSession";
import { createPortalUsageBillingService } from "./portalUsageBilling";

describe("portal usage billing service", () => {
  it("returns a mock snapshot for local demo sessions", async () => {
    const session = createMockPortalSession();
    const get = vi.fn(async (target: Parameters<ApiClient["get"]>[0]) => {
      expect(target).toBe(apiEndpoints.public.plans);
      return {
        plans: [
          {
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
          {
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
        ],
      };
    });
    const service = createPortalUsageBillingService({
      get,
    } as unknown as ApiClient);

    const snapshot = await service.loadSnapshot({
      organization: createSessionPortalOrganization({
        account_id: session.account_id,
        auth_method: session.auth_method,
        organization_name: session.organization_name,
        workspace_id: session.workspace_id,
      }),
      session,
    });

    expect(snapshot.source).toBe("session_mock");
    expect(snapshot.plan).toBe("growth");
    expect(snapshot.usage.limit).toBe(10000);
    expect(snapshot.budgetStatus.allowOverage).toBe(true);
  });

  it("loads backend subscription visibility for browser sessions", async () => {
    const session = {
      ...createMockPortalSession(),
      auth_method: "portal_browser_session" as const,
      billing_status: "active" as const,
      plan: "free",
    };
    const get = vi.fn(async (target: Parameters<ApiClient["get"]>[0]) => {
      if (target === apiEndpoints.public.plans) {
        return {
          plans: [
            {
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
            {
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
            {
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
            {
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
          ],
        };
      }
      expect(target).toBe(apiEndpoints.billing.subscription);
      return {
        billing_status: "active",
        effective_access_plan: "growth",
        pending_downgrade: {
          effective_at: "2026-04-01T00:00:00+00:00",
          plan: "starter",
        },
        plan: "pro",
        renewal_date: "2026-04-01T00:00:00+00:00",
        trial: {
          active: false,
          ends_at: null,
          status: null,
        },
      };
    });
    const service = createPortalUsageBillingService({
      get,
    } as unknown as ApiClient);

    const snapshot = await service.loadSnapshot({
      organization: {
        account_id: session.account_id,
        billing_allow_overage: false,
        organization_name: session.organization_name,
        scope_source: "backend_settings",
        settings_source: "stored",
        updated_at: null,
        workspace_id: session.workspace_id,
      },
      session,
    });

    expect(snapshot.source).toBe("backend_subscription");
    expect(snapshot.plan).toBe("pro");
    expect(snapshot.effectiveAccessPlan).toBe("growth");
    expect(snapshot.pendingDowngradePlan).toBe("starter");
    expect(snapshot.usage.limit).toBe(10000);
    expect(snapshot.budgetStatus.allowOverage).toBe(false);
  });
});
