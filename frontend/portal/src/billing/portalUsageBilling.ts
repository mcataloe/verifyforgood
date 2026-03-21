import {
  apiEndpoints,
  loadPricingPlanCatalog,
  type ApiClient,
} from "@charity-status/shared-api";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganization } from "../organization/portalOrganization";
import type { PricingPlanMetadata } from "@charity-status/shared-types";

interface BackendBillingSubscriptionResponse {
  billing_status?: string | null;
  effective_access_plan?: string | null;
  pending_downgrade?: {
    effective_at?: string | null;
    plan?: string | null;
  } | null;
  plan?: string | null;
  renewal_date?: string | null;
  trial?: {
    active?: boolean | null;
    ends_at?: string | null;
    status?: string | null;
  } | null;
}

export interface PortalBudgetStatus {
  allowOverage: boolean;
  label: string;
  policySource: "backend_default" | "organization_settings";
}

export interface PortalUsageSnapshot {
  limit: number;
  periodLabel: string;
  remaining: number;
  source: "mock_plan_baseline";
  used: number;
  usagePercent: number;
}

export interface PortalUsageBillingSnapshot {
  billingStatus: string;
  budgetStatus: PortalBudgetStatus;
  effectiveAccessPlan: string;
  notice: string | null;
  pendingDowngradeEffectiveAt: string | null;
  pendingDowngradePlan: string | null;
  plan: string;
  renewalDate: string | null;
  source: "backend_subscription" | "session_fallback" | "session_mock";
  trialEndsAt: string | null;
  trialStatus: string | null;
  usage: PortalUsageSnapshot;
}

export interface PortalUsageBillingService {
  loadSnapshot(input: {
    organization: PortalOrganization;
    session: PortalAuthenticatedSession;
  }): Promise<PortalUsageBillingSnapshot>;
}

const PLAN_USAGE_RATIOS: Record<string, number> = {
  enterprise: 0.12,
  free: 0.72,
  growth: 0.31,
  pro: 0.19,
  starter: 0.58,
};

export function createPortalUsageBillingService(
  apiClient: ApiClient,
  loadPlanCatalog: typeof loadPricingPlanCatalog = loadPricingPlanCatalog,
): PortalUsageBillingService {
  return {
    async loadSnapshot({ organization, session }) {
      const catalog = await loadPlanCatalog(apiClient);

      if (session.auth_method === "mock_browser_session") {
        return createMockSnapshot({
          plans: catalog.plans,
          organization,
          session,
          source: "session_mock",
        });
      }

      try {
        const subscription =
          await apiClient.get<BackendBillingSubscriptionResponse>(
            apiEndpoints.billing.subscription,
          );

        return createSnapshotFromSubscription({
          plans: catalog.plans,
          organization,
          session,
          source: "backend_subscription",
          subscription,
        });
      } catch {
        return createMockSnapshot({
          plans: catalog.plans,
          organization,
          session,
          source: "session_fallback",
        });
      }
    },
  };
}

function createSnapshotFromSubscription(input: {
  plans: PricingPlanMetadata[];
  organization: PortalOrganization;
  session: PortalAuthenticatedSession;
  source: PortalUsageBillingSnapshot["source"];
  subscription: BackendBillingSubscriptionResponse;
}): PortalUsageBillingSnapshot {
  const plan = normalizePlanCode(input.subscription.plan, input.session.plan);
  const effectiveAccessPlan = normalizePlanCode(
    input.subscription.effective_access_plan,
    plan,
  );

  return {
    billingStatus: normalizeText(
      input.subscription.billing_status,
      input.session.billing_status,
    ),
    budgetStatus: resolveBudgetStatus(input.organization),
    effectiveAccessPlan,
    notice:
      input.source === "backend_subscription"
        ? "Subscription state comes from the backend. Request usage remains a portal-local baseline until a customer usage endpoint exists."
        : "Backend billing visibility was unavailable, so the portal is showing a session-based baseline.",
    pendingDowngradeEffectiveAt:
      input.subscription.pending_downgrade?.effective_at ?? null,
    pendingDowngradePlan: input.subscription.pending_downgrade?.plan ?? null,
    plan,
    renewalDate: input.subscription.renewal_date ?? null,
    source: input.source,
    trialEndsAt: input.subscription.trial?.ends_at ?? null,
    trialStatus: input.subscription.trial?.status ?? null,
    usage: createMockUsageSnapshot(effectiveAccessPlan, input.plans),
  };
}

function createMockSnapshot(input: {
  plans: PricingPlanMetadata[];
  organization: PortalOrganization;
  session: PortalAuthenticatedSession;
  source: Extract<
    PortalUsageBillingSnapshot["source"],
    "session_fallback" | "session_mock"
  >;
}): PortalUsageBillingSnapshot {
  const plan = normalizePlanCode(input.session.plan, "free");

  return {
    billingStatus: normalizeText(input.session.billing_status, "active"),
    budgetStatus: resolveBudgetStatus(input.organization),
    effectiveAccessPlan: plan,
    notice:
      input.source === "session_mock"
        ? "Demo portal sessions use a local usage baseline until browser identity and customer usage endpoints are available."
        : "Backend billing visibility was unavailable, so the portal is showing a session-based baseline.",
    pendingDowngradeEffectiveAt: null,
    pendingDowngradePlan: null,
    plan,
    renewalDate: null,
    source: input.source,
    trialEndsAt: null,
    trialStatus: null,
    usage: createMockUsageSnapshot(plan, input.plans),
  };
}

function createMockUsageSnapshot(
  planCode: string,
  plans: PricingPlanMetadata[],
): PortalUsageSnapshot {
  const normalizedPlan = normalizePlanCode(planCode, "free");
  const limit = resolvePlanLimit(normalizedPlan, plans);
  const ratio = PLAN_USAGE_RATIOS[normalizedPlan] ?? 0.25;
  const used = Math.max(1, Math.round(limit * ratio));

  return {
    limit,
    periodLabel: "Current month",
    remaining: Math.max(0, limit - used),
    source: "mock_plan_baseline",
    used,
    usagePercent: Math.min(100, Math.round((used / limit) * 100)),
  };
}

function resolveBudgetStatus(
  organization: PortalOrganization,
): PortalBudgetStatus {
  const allowOverage = organization.billing_allow_overage ?? true;
  const policySource =
    organization.billing_allow_overage === null
      ? "backend_default"
      : "organization_settings";

  return {
    allowOverage,
    label: allowOverage
      ? "Overage allowed beyond included usage"
      : "Hard stop enabled at the monthly request limit",
    policySource,
  };
}

function resolvePlanLimit(
  planCode: string,
  plans: PricingPlanMetadata[],
): number {
  const match =
    plans.find((plan) => plan.plan_code === planCode) ??
    plans.find((plan) => plan.plan_code === "free");
  if (!match) {
    throw new Error("Plan catalog is missing the free tier.");
  }
  return match.included_usage.monthly_requests;
}

function normalizePlanCode(value: unknown, fallback: string): string {
  const candidate = normalizeText(value, fallback).toLowerCase();
  return candidate || fallback;
}

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  return fallback;
}
