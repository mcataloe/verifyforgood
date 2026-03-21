import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";

export interface CreateSubscriptionInput {
  cancelUrl: string;
  planCode: string;
  successUrl: string;
}

export interface UpdateSubscriptionPlanInput {
  planCode: string;
}

export interface CancelSubscriptionInput {
  returnUrl?: string;
  strategy?: "backend_plan_change" | "backend_billing_portal";
}

export interface BillingRedirectResult {
  action:
    | "cancel_subscription"
    | "create_subscription"
    | "manage_billing_portal";
  destinationUrl: string;
  kind: "redirect";
  providerBoundary: "backend_managed";
  reused: boolean;
}

export interface BillingSubscriptionMutationResult {
  action: "cancel_subscription" | "update_plan";
  billingPeriodEnd: string | null;
  billingStatus: string | null;
  changeType: string;
  currentPlanCode: string;
  effectiveFrom: string | null;
  effectiveTo: string | null;
  kind: "subscription_updated";
  pendingPlanCode: string | null;
  pendingPlanEffectiveAt: string | null;
  providerBoundary: "backend_managed";
  reused: boolean;
}

export type BillingInteractionResult =
  | BillingRedirectResult
  | BillingSubscriptionMutationResult;

export interface BillingInteractions {
  cancelSubscription: (
    input?: CancelSubscriptionInput,
  ) => Promise<BillingInteractionResult>;
  createSubscription: (
    input: CreateSubscriptionInput,
  ) => Promise<BillingInteractionResult>;
  updatePlan: (
    input: UpdateSubscriptionPlanInput,
  ) => Promise<BillingInteractionResult>;
}

interface CheckoutSessionResponse {
  checkout_url: string;
  plan_code: string;
  reused?: boolean;
}

interface PlanChangeResponse {
  billing_period_end?: string | null;
  billing_status?: string | null;
  change_type?: string | null;
  current_plan_code?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  pending_plan_code?: string | null;
  pending_plan_effective_at?: string | null;
  reused?: boolean;
}

interface BillingPortalSessionResponse {
  portal_url: string;
}

export function createBackendBillingInteractions(
  apiClient: Pick<ApiClient, "post">,
): BillingInteractions {
  return {
    async createSubscription(input) {
      const response = await apiClient.post<
        CheckoutSessionResponse,
        {
          cancel_url: string;
          plan_code: string;
          success_url: string;
        }
      >(apiEndpoints.billing.checkoutSession, {
        body: {
          cancel_url: input.cancelUrl,
          plan_code: input.planCode,
          success_url: input.successUrl,
        },
      });

      return {
        action: "create_subscription",
        destinationUrl: response.checkout_url,
        kind: "redirect",
        providerBoundary: "backend_managed",
        reused: Boolean(response.reused),
      };
    },

    async updatePlan(input) {
      const response = await apiClient.post<
        PlanChangeResponse,
        { plan_code: string }
      >(apiEndpoints.billing.planChange, {
        body: {
          plan_code: input.planCode,
        },
      });

      return toSubscriptionMutationResult(response, "update_plan");
    },

    async cancelSubscription(input = {}) {
      if (input.strategy === "backend_billing_portal") {
        const response = await apiClient.post<
          BillingPortalSessionResponse,
          { return_url: string }
        >(apiEndpoints.billing.portalSession, {
          body: {
            return_url: input.returnUrl ?? defaultReturnUrl(),
          },
        });

        return {
          action: "cancel_subscription",
          destinationUrl: response.portal_url,
          kind: "redirect",
          providerBoundary: "backend_managed",
          reused: false,
        };
      }

      const response = await apiClient.post<
        PlanChangeResponse,
        { plan_code: string }
      >(apiEndpoints.billing.planChange, {
        body: {
          plan_code: "free",
        },
      });

      return toSubscriptionMutationResult(response, "cancel_subscription");
    },
  };
}

function toSubscriptionMutationResult(
  response: PlanChangeResponse,
  action: "cancel_subscription" | "update_plan",
): BillingSubscriptionMutationResult {
  return {
    action,
    billingPeriodEnd: response.billing_period_end ?? null,
    billingStatus: response.billing_status ?? null,
    changeType: response.change_type ?? "updated",
    currentPlanCode: response.current_plan_code ?? "free",
    effectiveFrom: response.effective_from ?? null,
    effectiveTo: response.effective_to ?? null,
    kind: "subscription_updated",
    pendingPlanCode: response.pending_plan_code ?? null,
    pendingPlanEffectiveAt: response.pending_plan_effective_at ?? null,
    providerBoundary: "backend_managed",
    reused: Boolean(response.reused),
  };
}

function defaultReturnUrl(): string {
  if (typeof window === "undefined") {
    return "https://example.com/billing";
  }

  return window.location.href;
}
