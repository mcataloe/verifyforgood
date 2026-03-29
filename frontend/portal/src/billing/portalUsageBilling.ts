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
    change_type?: string | null;
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

interface BackendOrganizationUsageResponse {
  metrics?: Array<{
    last_updated?: string | null;
    metric_type?: string | null;
    request_count?: number | null;
  }>;
  period_label?: string | null;
  period_month?: string | null;
  plan_limit_context?: {
    allow_overage?: boolean | null;
    monthly_requests_limit?: number | null;
    policy_source?: string | null;
  } | null;
  totals?: {
    api_requests?: number | null;
    enrichment_requests?: number | null;
    filing_lookup_requests?: number | null;
    nonprofit_lookup_requests?: number | null;
    search_requests?: number | null;
  } | null;
}

export interface PortalBudgetStatus {
  allowOverage: boolean;
  label: string;
  policySource: "backend_default" | "organization_settings";
}

export interface PortalUsageTotals {
  apiRequests: number;
  enrichmentRequests: number;
  filingLookupRequests: number;
  nonprofitLookupRequests: number;
  searchRequests: number;
}

export interface PortalUsageMetricSummary {
  lastUpdated: string | null;
  metricType: string;
  requestCount: number;
}

export interface PortalUsageSnapshot {
  limit: number;
  metrics?: PortalUsageMetricSummary[];
  periodMonth?: string | null;
  periodLabel: string;
  remaining: number;
  source: "backend_usage_summary" | "mock_plan_baseline";
  totals?: PortalUsageTotals;
  used: number;
  usagePercent: number;
}

export interface PortalUsageBillingSnapshot {
  billingStatus: string;
  budgetStatus: PortalBudgetStatus;
  effectiveAccessPlan: string;
  notice: string | null;
  pendingChangeType: string | null;
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
        const [subscriptionResult, usageResult] = await Promise.allSettled([
          apiClient.get<BackendBillingSubscriptionResponse>(
            apiEndpoints.billing.subscription,
          ),
          apiClient.get<BackendOrganizationUsageResponse>(
            apiEndpoints.organization.usage,
          ),
        ]);

        if (subscriptionResult.status !== "fulfilled") {
          throw subscriptionResult.reason;
        }

        return createSnapshotFromSubscription({
          plans: catalog.plans,
          organization,
          session,
          source: "backend_subscription",
          subscription: subscriptionResult.value,
          usage:
            usageResult.status === "fulfilled" ? usageResult.value : undefined,
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
  usage?: BackendOrganizationUsageResponse;
}): PortalUsageBillingSnapshot {
  const plan = normalizePlanCode(input.subscription.plan, input.session.plan);
  const effectiveAccessPlan = normalizePlanCode(
    input.subscription.effective_access_plan,
    plan,
  );
  const usage = input.usage
    ? createUsageSnapshotFromBackend(input.usage, input.plans, effectiveAccessPlan)
    : createMockUsageSnapshot(effectiveAccessPlan, input.plans);

  return {
    billingStatus: normalizeText(
      input.subscription.billing_status,
      input.session.billing_status,
    ),
    budgetStatus: resolveBudgetStatus(input.organization, input.usage),
    effectiveAccessPlan,
    notice: input.usage
      ? "Usage totals reflect current organization metering for the active tracking period."
      : "Subscription state comes from the backend. Usage summary was unavailable, so the portal is showing a plan-based baseline.",
    pendingChangeType: input.subscription.pending_downgrade?.change_type ?? null,
    pendingDowngradeEffectiveAt:
      input.subscription.pending_downgrade?.effective_at ?? null,
    pendingDowngradePlan: input.subscription.pending_downgrade?.plan ?? null,
    plan,
    renewalDate: input.subscription.renewal_date ?? null,
    source: input.source,
    trialEndsAt: input.subscription.trial?.ends_at ?? null,
    trialStatus: input.subscription.trial?.status ?? null,
    usage,
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
        ? "Demo portal sessions use a local usage baseline instead of backend metering."
        : "Backend billing visibility was unavailable, so the portal is showing a session-based baseline.",
    pendingChangeType: null,
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
    metrics: [],
    periodMonth: null,
    periodLabel: "Current month",
    remaining: Math.max(0, limit - used),
    source: "mock_plan_baseline",
    totals: {
      apiRequests: used,
      enrichmentRequests: 0,
      filingLookupRequests: 0,
      nonprofitLookupRequests: used,
      searchRequests: 0,
    },
    used,
    usagePercent: Math.min(100, Math.round((used / limit) * 100)),
  };
}

function createUsageSnapshotFromBackend(
  usage: BackendOrganizationUsageResponse,
  plans: PricingPlanMetadata[],
  planCode: string,
): PortalUsageSnapshot {
  const limit =
    normalizePositiveInteger(usage.plan_limit_context?.monthly_requests_limit) ??
    resolvePlanLimit(planCode, plans);
  const totals: PortalUsageTotals = {
    apiRequests: normalizeCount(usage.totals?.api_requests),
    enrichmentRequests: normalizeCount(usage.totals?.enrichment_requests),
    filingLookupRequests: normalizeCount(usage.totals?.filing_lookup_requests),
    nonprofitLookupRequests: normalizeCount(
      usage.totals?.nonprofit_lookup_requests,
    ),
    searchRequests: normalizeCount(usage.totals?.search_requests),
  };
  const used = totals.apiRequests;

  return {
    limit,
    metrics: (usage.metrics ?? []).map((metric) => ({
      lastUpdated:
        typeof metric.last_updated === "string" ? metric.last_updated : null,
      metricType: normalizeText(metric.metric_type, "unknown"),
      requestCount: normalizeCount(metric.request_count),
    })),
    periodMonth:
      typeof usage.period_month === "string" ? usage.period_month : null,
    periodLabel: normalizeText(usage.period_label, "Current month"),
    remaining: Math.max(0, limit - used),
    source: "backend_usage_summary",
    totals,
    used,
    usagePercent:
      limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0,
  };
}

function resolveBudgetStatus(
  organization: PortalOrganization,
  usage?: BackendOrganizationUsageResponse,
): PortalBudgetStatus {
  const allowOverage =
    typeof usage?.plan_limit_context?.allow_overage === "boolean"
      ? usage.plan_limit_context.allow_overage
      : (organization.billing_allow_overage ?? true);
  const policySource =
    usage?.plan_limit_context?.policy_source === "organization_settings" ||
    organization.billing_allow_overage !== null
      ? "organization_settings"
      : "backend_default";

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

function normalizePositiveInteger(value: unknown): number | null {
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    return null;
  }
  return value;
}

function normalizeCount(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return 0;
  }
  return Math.max(0, Math.round(value));
}

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  return fallback;
}
