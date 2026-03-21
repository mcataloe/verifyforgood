import { describe, expect, it, vi } from "vitest";
import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import {
  createBackendBillingInteractions,
  type BillingInteractions,
} from "./billingInteractions";

describe("billingInteractions", () => {
  it("creates subscriptions through the backend checkout endpoint", async () => {
    const post = vi.fn(
      async (target: Parameters<ApiClient["post"]>[0], options?: unknown) => {
        expect(target).toBe(apiEndpoints.billing.checkoutSession);
        expect(options).toEqual({
          body: {
            cancel_url: "https://example.com/cancel",
            plan_code: "growth",
            success_url: "https://example.com/success",
          },
        });
        return {
          checkout_url: "https://billing.example.test/checkout",
          plan_code: "growth",
          reused: false,
        };
      },
    );

    const service = createBackendBillingInteractions({
      post,
    } as Pick<ApiClient, "post">);
    const result = await service.createSubscription({
      cancelUrl: "https://example.com/cancel",
      planCode: "growth",
      successUrl: "https://example.com/success",
    });

    expect(result).toEqual({
      action: "create_subscription",
      destinationUrl: "https://billing.example.test/checkout",
      kind: "redirect",
      providerBoundary: "backend_managed",
      reused: false,
    });
  });

  it("updates plans through the backend plan-change endpoint", async () => {
    const post = vi.fn(
      async (target: Parameters<ApiClient["post"]>[0], options?: unknown) => {
        expect(target).toBe(apiEndpoints.billing.planChange);
        expect(options).toEqual({
          body: {
            plan_code: "pro",
          },
        });
        return {
          billing_period_end: "2026-04-01T00:00:00+00:00",
          billing_status: "active",
          change_type: "upgrade",
          current_plan_code: "pro",
          effective_from: "2026-03-21T00:00:00+00:00",
          effective_to: null,
          pending_plan_code: null,
          pending_plan_effective_at: null,
          reused: false,
        };
      },
    );

    const service = createBackendBillingInteractions({
      post,
    } as Pick<ApiClient, "post">);
    const result = await service.updatePlan({
      planCode: "pro",
    });

    expect(result).toEqual({
      action: "update_plan",
      billingPeriodEnd: "2026-04-01T00:00:00+00:00",
      billingStatus: "active",
      changeType: "upgrade",
      currentPlanCode: "pro",
      effectiveFrom: "2026-03-21T00:00:00+00:00",
      effectiveTo: null,
      kind: "subscription_updated",
      pendingPlanCode: null,
      pendingPlanEffectiveAt: null,
      providerBoundary: "backend_managed",
      reused: false,
    });
  });

  it("cancels subscriptions through backend plan change by default", async () => {
    const post = vi.fn(
      async (target: Parameters<ApiClient["post"]>[0], options?: unknown) => {
        expect(target).toBe(apiEndpoints.billing.planChange);
        expect(options).toEqual({
          body: {
            plan_code: "free",
          },
        });
        return {
          billing_period_end: "2026-04-01T00:00:00+00:00",
          billing_status: "active",
          change_type: "downgrade_scheduled",
          current_plan_code: "growth",
          effective_from: "2026-03-01T00:00:00+00:00",
          effective_to: null,
          pending_plan_code: "free",
          pending_plan_effective_at: "2026-04-01T00:00:00+00:00",
          reused: false,
        };
      },
    );

    const service: BillingInteractions = createBackendBillingInteractions({
      post,
    } as Pick<ApiClient, "post">);
    const result = await service.cancelSubscription();

    expect(result).toEqual({
      action: "cancel_subscription",
      billingPeriodEnd: "2026-04-01T00:00:00+00:00",
      billingStatus: "active",
      changeType: "downgrade_scheduled",
      currentPlanCode: "growth",
      effectiveFrom: "2026-03-01T00:00:00+00:00",
      effectiveTo: null,
      kind: "subscription_updated",
      pendingPlanCode: "free",
      pendingPlanEffectiveAt: "2026-04-01T00:00:00+00:00",
      providerBoundary: "backend_managed",
      reused: false,
    });
  });

  it("can delegate cancellation to a backend-managed billing portal redirect", async () => {
    const post = vi.fn(
      async (target: Parameters<ApiClient["post"]>[0], options?: unknown) => {
        expect(target).toBe(apiEndpoints.billing.portalSession);
        expect(options).toEqual({
          body: {
            return_url: "https://example.com/billing",
          },
        });
        return {
          portal_url: "https://billing.example.test/portal",
        };
      },
    );

    const service = createBackendBillingInteractions({
      post,
    } as Pick<ApiClient, "post">);
    const result = await service.cancelSubscription({
      returnUrl: "https://example.com/billing",
      strategy: "backend_billing_portal",
    });

    expect(result).toEqual({
      action: "cancel_subscription",
      destinationUrl: "https://billing.example.test/portal",
      kind: "redirect",
      providerBoundary: "backend_managed",
      reused: false,
    });
  });
});
