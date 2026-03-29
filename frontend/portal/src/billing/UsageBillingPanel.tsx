import { useEffect, useMemo, useState } from "react";
import { Grid, Panel, PricingPlanGrid } from "@charity-status/shared-ui";
import { Button, Group, Text } from "@mantine/core";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalErrorState,
  PortalLoadingState,
  PortalNotice,
} from "../components/feedback";
import {
  usePortalUsageBilling,
  type PortalUsageBillingController,
} from "./usePortalUsageBilling";
import {
  usePortalPricingPlans,
  type PortalPricingPlansController,
} from "./usePortalPricingPlans";
import { SubscriptionSummaryCard } from "./SubscriptionSummaryCard";
import { TrialOnboardingPanel } from "./TrialOnboardingPanel";
import {
  usePortalBillingInteractions,
  type PortalBillingInteractionsController,
} from "./usePortalBillingInteractions";
import { UsageContextPanel } from "./UsageContextPanel";
import type {
  PortalUsageBillingSnapshot,
  PortalUsageMetricSummary,
  PortalUsageTotals,
} from "./portalUsageBilling";
import type { PortalPricingPlanItem } from "./usePortalPricingPlans";
import type { BillingInteractionResult } from "./billingInteractions";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface UsageBillingPanelProps {
  billingActionsController?: PortalBillingInteractionsController;
  controller?: PortalUsageBillingController;
  endpoints: PortalEndpoints;
  focus?: "billing" | "usage";
  plansController?: PortalPricingPlansController;
  session: PortalAuthenticatedSession;
}

export function UsageBillingPanel({
  billingActionsController,
  controller,
  endpoints,
  focus = "billing",
  plansController,
  session,
}: UsageBillingPanelProps) {
  const defaultController = usePortalUsageBilling(session);
  const billing = controller ?? defaultController;
  const defaultPlansController = usePortalPricingPlans(billing.snapshot);
  const pricingPlans = plansController ?? defaultPlansController;
  const defaultBillingActionsController = usePortalBillingInteractions();
  const billingActions =
    billingActionsController ?? defaultBillingActionsController;
  const organization = usePortalOrganization();
  const [liveSnapshot, setLiveSnapshot] =
    useState<PortalUsageBillingSnapshot | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    setLiveSnapshot(billing.snapshot);
  }, [billing.snapshot]);

  if (billing.isLoading || pricingPlans.isLoading) {
    return (
      <PortalLoadingState
        subtitle="Fetching the current customer billing summary."
        title="Loading usage and billing"
      >
        <p>Loading plan, request usage, and overage policy state.</p>
      </PortalLoadingState>
    );
  }

  if (billing.error || pricingPlans.error || !billing.snapshot) {
    return (
      <PortalErrorState
        actionLabel="Retry billing summary"
        message={
          billing.error ??
          pricingPlans.error ??
          "No billing summary is available right now."
        }
        onAction={() => {
          void billing.reload();
          void pricingPlans.reload();
        }}
        subtitle="The portal could not load the current usage and billing state."
        title="Billing summary unavailable"
      />
    );
  }

  const snapshot = liveSnapshot ?? billing.snapshot;
  if (!snapshot) {
    return null;
  }

  const isAdmin = organization.currentMembership?.role === "admin";
  const effectivePlan =
    pricingPlans.plans.find(
      (item) => item.plan.plan_code === snapshot.effectiveAccessPlan,
    )?.plan ??
    pricingPlans.plans.find((item) => item.plan.plan_code === snapshot.plan)
      ?.plan ??
    null;
  const currentPlan =
    pricingPlans.plans.find((item) => item.plan.plan_code === snapshot.plan)
      ?.plan ?? null;
  const pendingSummary = describePendingChange(snapshot);
  const planItems = pricingPlans.plans.map((item) =>
    createPlanGridItem({
      isAdmin,
      item,
      onPlanAction: async (planCode) => {
        setStatusMessage(null);
        const result = await runPlanAction({
          billing,
          billingActions,
          currentSnapshot: snapshot,
          planCode,
          setLiveSnapshot,
          setStatusMessage,
        });
        if (result?.kind === "redirect") {
          redirectToDestination(result.destinationUrl);
        }
      },
      snapshot,
    }),
  );
  const subscriptionPanelTitle =
    focus === "usage" ? "Usage overview" : "Current subscription";
  const subscriptionPanelSubtitle =
    focus === "usage"
      ? "Usage, budget posture, and effective access stay visible without leaving the shared billing route."
      : "Authoritative backend subscription state, billing cycle visibility, and pending billing changes.";
  const subscriptionSummary = (
    <SubscriptionSummaryCard currentPlan={currentPlan} snapshot={snapshot} />
  );
  const usageSummary = (
    <>
      <div className="portal-usage-meter" aria-label="Request usage meter">
        <div className="portal-usage-meter__header">
          <div>
            <p className="portal-shell__eyebrow">Request usage</p>
            <h3>
              {snapshot.usage.used.toLocaleString()} /{" "}
              {snapshot.usage.limit.toLocaleString()}
            </h3>
            <p>
              {snapshot.usage.remaining.toLocaleString()} requests remaining
              in {snapshot.usage.periodLabel.toLowerCase()}.
            </p>
          </div>
          <span className="portal-key-chip">
            {snapshot.usage.usagePercent}%
          </span>
        </div>
        <div className="portal-usage-meter__track" aria-hidden="true">
          <div
            className="portal-usage-meter__fill"
            style={{ width: `${snapshot.usage.usagePercent}%` }}
          />
        </div>
      </div>

      <UsageContextPanel
        budgetStatus={snapshot.budgetStatus}
        plan={effectivePlan}
        usage={snapshot.usage}
      />
      <UsageSummaryGrid
        limit={
          effectivePlan?.included_usage.monthly_requests ?? snapshot.usage.limit
        }
        totals={resolveUsageTotals(snapshot)}
      />
      <UsageMetricBreakdown metrics={resolveUsageMetrics(snapshot)} />
    </>
  );

  return (
    <Grid className="portal-page-grid">
      <Panel
        title={subscriptionPanelTitle}
        subtitle={subscriptionPanelSubtitle}
      >
        <TrialOnboardingPanel plans={pricingPlans.plans} snapshot={snapshot} />
        {focus === "usage" ? usageSummary : subscriptionSummary}

        {statusMessage ? (
          <PortalNotice tone="warning">
            <p>{statusMessage}</p>
          </PortalNotice>
        ) : null}

        {snapshot.notice ? (
          <PortalNotice tone="warning">
            <p>{snapshot.notice}</p>
          </PortalNotice>
        ) : null}

        {!isAdmin ? (
          <PortalNotice tone="warning">
            <p>
              Billing controls are limited to organization admins. Subscription
              state remains visible here for shared operator context.
            </p>
          </PortalNotice>
        ) : null}

        {focus === "usage" ? subscriptionSummary : usageSummary}

        <dl className="portal-shell__details">
          <div>
          <dt>Effective access</dt>
            <dd>{snapshot.effectiveAccessPlan}</dd>
          </div>
          <div>
            <dt>Budget mode</dt>
            <dd>{snapshot.budgetStatus.label}</dd>
          </div>
          <div>
            <dt>Budget policy source</dt>
            <dd>{snapshot.budgetStatus.policySource}</dd>
          </div>
          <div>
            <dt>Included monthly requests</dt>
            <dd>
              {effectivePlan
                ? effectivePlan.included_usage.monthly_requests.toLocaleString()
                : snapshot.usage.limit.toLocaleString()}
            </dd>
          </div>
          <div>
            <dt>Overage price</dt>
            <dd>
              {effectivePlan
                ? formatUsdMicros(
                    effectivePlan.per_request_pricing.amount_usd_micros,
                  )
                : "Unavailable"}
            </dd>
          </div>
          <div>
            <dt>Data source</dt>
            <dd>{snapshot.source}</dd>
          </div>
          <div>
            <dt>Pending change</dt>
            <dd>{pendingSummary.label}</dd>
          </div>
        </dl>
      </Panel>

      <Panel
        title="Manage plans"
        subtitle="Compare backend-seeded plans and take the next valid billing action for the current subscription state."
      >
        <PricingPlanGrid items={planItems} />
      </Panel>

      <Panel
        title="Billing tools"
        subtitle="Manage invoices and provider billing tools through backend-managed portal sessions."
      >
        {billingActions.error ? (
          <PortalNotice tone="error">
            <p>{billingActions.error}</p>
          </PortalNotice>
        ) : null}

        <dl className="portal-shell__details">
          <div>
            <dt>Renewal date</dt>
            <dd>{snapshot.renewalDate ?? "Not scheduled"}</dd>
          </div>
          <div>
            <dt>Pending plan</dt>
            <dd>{snapshot.pendingDowngradePlan ?? "None"}</dd>
          </div>
          <div>
            <dt>Pending change effective at</dt>
            <dd>{snapshot.pendingDowngradeEffectiveAt ?? "Not scheduled"}</dd>
          </div>
          <div>
            <dt>Pending change type</dt>
            <dd>{pendingSummary.typeLabel}</dd>
          </div>
          <div>
            <dt>Trial status</dt>
            <dd>{snapshot.trialStatus ?? "None"}</dd>
          </div>
          <div>
            <dt>Trial ends at</dt>
            <dd>{snapshot.trialEndsAt ?? "Not applicable"}</dd>
          </div>
        </dl>

        <div className="portal-billing-tools">
          <div className="portal-billing-tools__copy">
            <p className="portal-shell__eyebrow">Invoices & payment methods</p>
            <h4 className="portal-billing-tools__title">
              Open the billing portal
            </h4>
            <p className="portal-billing-tools__description">
              Invoice history and payment-method management stay inside the
              backend-managed provider portal in this phase.
            </p>
          </div>
          <Group gap="sm" wrap="wrap">
            <Button
              disabled={!isAdmin}
              loading={billingActions.isPending}
              onClick={() => {
                setStatusMessage(
                  "Opening the backend-managed billing portal for invoices and payment details.",
                );
                void billingActions
                  .cancelSubscription({
                    returnUrl: defaultReturnUrl(),
                    strategy: "backend_billing_portal",
                  })
                  .then((result) => {
                    if (result.kind === "redirect") {
                      redirectToDestination(result.destinationUrl);
                    }
                  })
                  .catch(() => {});
              }}
              variant="filled"
            >
              Open billing portal
            </Button>
          </Group>
        </div>

        <Text c="dimmed" fz="sm" mt="md">
          Signed in plan baseline: <strong>{session.plan}</strong>. Backend
          routes remain explicit at <code>{endpoints.billingSubscription}</code>
          , <code>{endpoints.organizationUsage ?? "/v1/organization/usage"}</code>,{" "}
          <code>{endpoints.billingCheckout}</code>,{" "}
          <code>{endpoints.billingPlanChange}</code>, and{" "}
          <code>{endpoints.billingPortal}</code>.
        </Text>
      </Panel>
    </Grid>
  );
}

function resolveUsageTotals(snapshot: PortalUsageBillingSnapshot): PortalUsageTotals {
  return (
    snapshot.usage.totals ?? {
      apiRequests: snapshot.usage.used,
      enrichmentRequests: 0,
      filingLookupRequests: 0,
      nonprofitLookupRequests: snapshot.usage.used,
      searchRequests: 0,
    }
  );
}

function resolveUsageMetrics(
  snapshot: PortalUsageBillingSnapshot,
): PortalUsageMetricSummary[] {
  return snapshot.usage.metrics ?? [];
}

function UsageSummaryGrid(input: {
  limit: number;
  totals: PortalUsageTotals;
}) {
  return (
    <section className="portal-usage-summary-grid" aria-label="Usage totals">
      <UsageSummaryCard
        label="API requests"
        value={input.totals.apiRequests.toLocaleString()}
      />
      <UsageSummaryCard
        label="Nonprofit lookups"
        value={input.totals.nonprofitLookupRequests.toLocaleString()}
      />
      <UsageSummaryCard
        label="Search requests"
        value={input.totals.searchRequests.toLocaleString()}
      />
      <UsageSummaryCard
        label="Enrichment requests"
        value={input.totals.enrichmentRequests.toLocaleString()}
      />
      <UsageSummaryCard
        label="Filing lookups"
        value={input.totals.filingLookupRequests.toLocaleString()}
      />
      <UsageSummaryCard
        label="Included monthly requests"
        value={input.limit.toLocaleString()}
      />
    </section>
  );
}

function UsageSummaryCard(input: { label: string; value: string }) {
  return (
    <div className="portal-usage-summary-card">
      <span>{input.label}</span>
      <strong>{input.value}</strong>
    </div>
  );
}

function UsageMetricBreakdown(input: { metrics: PortalUsageMetricSummary[] }) {
  if (input.metrics.length === 0) {
    return (
      <PortalNotice tone="warning">
        <p>
          No tracked usage has been recorded for this organization in the current
          period yet.
        </p>
      </PortalNotice>
    );
  }

  return (
    <section
      className="portal-usage-breakdown"
      aria-label="Usage metric breakdown"
    >
      <div className="portal-usage-breakdown__header">
        <div>
          <p className="portal-shell__eyebrow">Current period breakdown</p>
          <h3>Usage metrics recorded this month</h3>
        </div>
      </div>
      <div className="portal-usage-breakdown__table" role="table">
        <div
          className="portal-usage-breakdown__row portal-usage-breakdown__row--header"
          role="row"
        >
          <span role="columnheader">Metric</span>
          <span role="columnheader">Requests</span>
          <span role="columnheader">Last updated</span>
        </div>
        {input.metrics.map((metric) => (
          <div
            className="portal-usage-breakdown__row"
            key={metric.metricType}
            role="row"
          >
            <span role="cell">{formatUsageMetricLabel(metric.metricType)}</span>
            <span role="cell">{metric.requestCount.toLocaleString()}</span>
            <span role="cell">{metric.lastUpdated ?? "Not yet updated"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatUsageMetricLabel(metricType: string): string {
  return metricType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatUsdMicros(amountUsdMicros: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 3,
    minimumFractionDigits: 3,
    style: "currency",
  }).format(amountUsdMicros / 1_000_000);
}

function createPlanGridItem(input: {
  isAdmin: boolean;
  item: PortalPricingPlanItem;
  onPlanAction: (planCode: string) => Promise<void>;
  snapshot: PortalUsageBillingSnapshot;
}) {
  const action = resolvePlanAction({
    item: input.item,
    snapshot: input.snapshot,
  });

  return {
    ...input.item,
    cta: input.isAdmin ? (
      <Button
        disabled={action.disabled}
        fullWidth
        onClick={() => {
          void input.onPlanAction(input.item.plan.plan_code);
        }}
        size="sm"
        variant={action.variant}
      >
        {action.label}
      </Button>
    ) : undefined,
    footnote: action.footnote ? (
      <Text c="dimmed" fz="sm">
        {action.footnote}
      </Text>
    ) : undefined,
  };
}

function resolvePlanAction(input: {
  item: PortalPricingPlanItem;
  snapshot: PortalUsageBillingSnapshot;
}) {
  const targetPlanCode = input.item.plan.plan_code;
  const currentPlanCode = input.snapshot.plan;
  const pendingPlanCode = input.snapshot.pendingDowngradePlan;
  const pendingChangeType = input.snapshot.pendingChangeType;

  if (targetPlanCode === currentPlanCode) {
    if (pendingPlanCode) {
      return {
        disabled: false,
        footnote:
          pendingChangeType === "cancellation_scheduled"
            ? "Clears the scheduled cancellation and keeps the current paid plan."
            : "Clears the scheduled downgrade and keeps the current plan.",
        label: "Keep this plan",
        variant: "default" as const,
      };
    }

    return {
      disabled: true,
      footnote: "This is the current billing plan.",
      label: "Current plan",
      variant: "default" as const,
    };
  }

  if (targetPlanCode === pendingPlanCode) {
    return {
      disabled: true,
      footnote:
        pendingChangeType === "cancellation_scheduled"
          ? "Cancellation is already scheduled for the current billing period end."
          : "This downgrade is already scheduled for the next billing cycle.",
      label:
        pendingChangeType === "cancellation_scheduled"
          ? "Cancellation scheduled"
          : "Downgrade scheduled",
      variant: "default" as const,
    };
  }

  if (currentPlanCode === "free") {
    return {
      disabled: false,
      footnote: "Starts a backend-managed checkout flow for the selected paid plan.",
      label: "Start checkout",
      variant: "filled" as const,
    };
  }

  if (targetPlanCode === "free") {
    return {
      disabled: false,
      footnote: "Schedules cancellation at the current billing period end.",
      label: "Cancel at period end",
      variant: "outline" as const,
    };
  }

  if (planRank(targetPlanCode) > planRank(currentPlanCode)) {
    return {
      disabled: false,
      footnote:
        pendingChangeType === "cancellation_scheduled"
          ? "Clears the scheduled cancellation and applies the upgrade immediately."
          : "Upgrades take effect immediately.",
      label:
        pendingChangeType === "cancellation_scheduled"
          ? "Resume and upgrade"
          : "Upgrade now",
      variant: "filled" as const,
    };
  }

  return {
    disabled: false,
    footnote:
      pendingChangeType === "cancellation_scheduled"
        ? "Clears the scheduled cancellation and keeps a lower paid plan for the next cycle."
        : "Schedules the lower paid plan for the next billing cycle.",
    label:
      pendingChangeType === "cancellation_scheduled"
        ? "Resume with scheduled downgrade"
        : "Schedule downgrade",
    variant: "default" as const,
  };
}

async function runPlanAction(input: {
  billing: PortalUsageBillingController;
  billingActions: PortalBillingInteractionsController;
  currentSnapshot: PortalUsageBillingSnapshot;
  planCode: string;
  setLiveSnapshot: (snapshot: PortalUsageBillingSnapshot | null) => void;
  setStatusMessage: (message: string | null) => void;
}): Promise<BillingInteractionResult | null> {
  const result =
    input.currentSnapshot.plan === "free" && input.planCode !== "free"
      ? await input.billingActions.createSubscription({
          cancelUrl: defaultReturnUrl(),
          planCode: input.planCode,
          successUrl: defaultReturnUrl(),
        })
      : input.planCode === "free"
        ? await input.billingActions.cancelSubscription()
        : await input.billingActions.updatePlan({
            planCode: input.planCode,
          });

  if (result.kind === "redirect") {
    input.setStatusMessage(
      result.action === "manage_billing_portal"
        ? "Opening the backend-managed billing portal."
        : "Opening the backend-managed checkout experience.",
    );
    return result;
  }

  input.setLiveSnapshot(applyMutationResult(input.currentSnapshot, result));
  input.setStatusMessage(describeMutationResult(result));
  await input.billing.reload();
  return result;
}

function applyMutationResult(
  snapshot: PortalUsageBillingSnapshot,
  result: Extract<BillingInteractionResult, { kind: "subscription_updated" }>,
): PortalUsageBillingSnapshot {
  const pendingChangeType =
    result.pendingPlanCode === "free"
      ? "cancellation_scheduled"
      : result.changeType === "downgrade_scheduled"
        ? "downgrade_scheduled"
        : null;

  return {
    ...snapshot,
    billingStatus: result.billingStatus ?? snapshot.billingStatus,
    pendingChangeType,
    pendingDowngradeEffectiveAt:
      result.pendingPlanEffectiveAt ?? result.effectiveTo ?? null,
    pendingDowngradePlan: result.pendingPlanCode,
    plan: result.currentPlanCode || snapshot.plan,
    renewalDate: result.billingPeriodEnd ?? snapshot.renewalDate,
  };
}

function describeMutationResult(
  result: Extract<BillingInteractionResult, { kind: "subscription_updated" }>,
) {
  switch (result.changeType) {
    case "upgrade":
      return result.reused
        ? "The requested upgrade is already reflected in the current billing state."
        : "The plan upgrade was applied immediately.";
    case "downgrade_scheduled":
      return result.reused
        ? "That downgrade is already scheduled for the next billing cycle."
        : "The downgrade is scheduled for the next billing cycle.";
    case "cancellation_scheduled":
      return result.reused
        ? "Cancellation is already scheduled for the end of the current billing period."
        : "Cancellation is scheduled for the end of the current billing period.";
    case "pending_change_cleared":
      return "The pending billing change was cleared and the current plan will continue.";
    default:
      return "The subscription state was updated.";
  }
}

function describePendingChange(snapshot: PortalUsageBillingSnapshot) {
  if (!snapshot.pendingDowngradePlan) {
    return {
      label: "None",
      typeLabel: "None",
    };
  }

  if (snapshot.pendingChangeType === "cancellation_scheduled") {
    return {
      label: `Cancellation to ${snapshot.pendingDowngradePlan} on ${snapshot.pendingDowngradeEffectiveAt ?? "the current period end"}`,
      typeLabel: "Cancellation at period end",
    };
  }

  return {
    label: `Downgrade to ${snapshot.pendingDowngradePlan} on ${snapshot.pendingDowngradeEffectiveAt ?? "the next billing cycle"}`,
    typeLabel: "Scheduled downgrade",
  };
}

function planRank(planCode: string): number {
  return ["free", "starter", "growth", "pro", "enterprise"].indexOf(
    planCode,
  );
}

function defaultReturnUrl(): string {
  if (typeof window === "undefined") {
    return "https://example.com/billing";
  }

  return window.location.href;
}

function redirectToDestination(url: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.location.assign(url);
}
