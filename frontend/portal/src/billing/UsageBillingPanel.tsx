import { useEffect, useState } from "react";
import { Panel, PricingPlanGrid } from "@charity-status/shared-ui";
import { Button, Group, Paper, Stack, Tabs, Text, Title } from "@mantine/core";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalErrorState,
  PortalLoadingState,
  PortalNotice,
  PortalNoticeList,
  type PortalNoticeListItem,
} from "../components/feedback";
import {
  PortalDetailList,
  PortalMetricCard,
  PortalMetricGrid,
} from "../components/PortalPrimitives";
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
  managementMode?: "manage" | "visibility";
  plansController?: PortalPricingPlansController;
  session: PortalAuthenticatedSession;
}

export function UsageBillingPanel({
  billingActionsController,
  controller,
  endpoints,
  focus = "billing",
  managementMode = "manage",
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
  const [dismissedUsageNoticeIds, setDismissedUsageNoticeIds] = useState<
    string[]
  >([]);

  useEffect(() => {
    setLiveSnapshot(billing.snapshot);
  }, [billing.snapshot]);

  useEffect(() => {
    setDismissedUsageNoticeIds([]);
  }, [
    billing.snapshot,
    focus,
    managementMode,
    organization.currentMembership?.role,
    statusMessage,
  ]);

  if (billing.isLoading || pricingPlans.isLoading) {
    return (
      <PortalLoadingState
        subtitle="Fetching your current billing summary."
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
        subtitle="We couldn't load your current usage and billing details."
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
  const visibilityOnly = managementMode === "visibility";
  const planItems = visibilityOnly
    ? []
    : pricingPlans.plans.map((item) =>
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
    focus === "usage"
      ? "Usage"
      : visibilityOnly
        ? "Subscription Visibility"
        : "Current Subscription";
  const subscriptionPanelSubtitle =
    focus === "usage"
      ? "Track request usage, limits, and budget settings for your organization."
      : visibilityOnly
        ? "Review your current plan, billing dates, limits, and enabled features."
        : "Review your plan, billing cycle, and any pending changes.";
  const thirdTabLabel = visibilityOnly ? "Included Limits" : "Manage Plans";
  const fourthTabLabel = visibilityOnly
    ? "Enabled Capabilities"
    : "Billing Tools";
  const subscriptionSummary = (
    <SubscriptionSummaryCard currentPlan={currentPlan} snapshot={snapshot} />
  );
  const usageSummary = (
    <>
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
  const usageSectionNotices: PortalNoticeListItem[] = [];
  if (!visibilityOnly && statusMessage) {
    usageSectionNotices.push({
      body: statusMessage,
      id: `status:${statusMessage}`,
      tone: "warning",
    });
  }
  if (snapshot.notice) {
    usageSectionNotices.push({
      body: snapshot.notice,
      id: `snapshot:${snapshot.notice}`,
      tone: "warning",
    });
  }
  if (!isAdmin) {
    usageSectionNotices.push({
      body: "Only organization admins can make billing changes. Billing details are still visible here.",
      id: "billing-admin-visibility",
      tone: "warning",
    });
  }
  if (focus === "usage" && resolveUsageMetrics(snapshot).length === 0) {
    usageSectionNotices.push({
      body: "No tracked usage has been recorded for this organization in the current period yet.",
      id: "usage-metrics-empty",
      tone: "empty",
    });
  }
  const visibleUsageSectionNotices = usageSectionNotices.filter(
    (notice) => !dismissedUsageNoticeIds.includes(notice.id),
  );

  return (
    <Tabs color="primary" defaultValue="overview" variant="outline">
      <Tabs.List aria-label="Billing sections">
        <Tabs.Tab value="overview">{subscriptionPanelTitle}</Tabs.Tab>
        <Tabs.Tab value="details">Subscription Details</Tabs.Tab>
        <Tabs.Tab value="plan">{thirdTabLabel}</Tabs.Tab>
        <Tabs.Tab value="capabilities">{fourthTabLabel}</Tabs.Tab>
      </Tabs.List>

      <Tabs.Panel pt="md" value="overview">
        <Panel
          title={focus === "usage" ? undefined : subscriptionPanelTitle}
          subtitle={focus === "usage" ? undefined : subscriptionPanelSubtitle}
        >
          <PortalNoticeList
            notices={visibleUsageSectionNotices}
            onDismiss={(id) => {
              setDismissedUsageNoticeIds((current) =>
                current.includes(id) ? current : [...current, id],
              );
            }}
          />
          <TrialOnboardingPanel
            plans={pricingPlans.plans}
            snapshot={snapshot}
          />
          {focus === "usage" ? usageSummary : subscriptionSummary}
        </Panel>
      </Tabs.Panel>

      <Tabs.Panel pt="md" value="details">
        <Panel
          title="Subscription Details"
          subtitle="Review plan details, billing dates, and scheduled changes."
        >
          <PortalDetailList
            columns={2}
            items={[
              {
                key: "current-plan",
                label: "Current plan",
                value: snapshot.planDisplayName ?? toTitleCase(snapshot.plan),
              },
              {
                key: "effective-plan",
                label: "Effective access plan",
                value:
                  snapshot.effectiveAccessPlanDisplayName ??
                  toTitleCase(snapshot.effectiveAccessPlan),
              },
              {
                key: "subscription-status",
                label: "Subscription status",
                value: toTitleCase(
                  snapshot.subscriptionStatus ?? snapshot.billingStatus,
                ),
              },
              {
                key: "billing-status",
                label: "Billing status",
                value: toTitleCase(snapshot.billingStatus),
              },
              {
                key: "period-start",
                label: "Current period start",
                value: formatBillingDate(snapshot.billingCycleStart),
              },
              {
                key: "period-end",
                label: "Current period end",
                value: formatBillingDate(
                  snapshot.billingCycleEnd ?? snapshot.renewalDate,
                ),
              },
              {
                key: "pending-plan",
                label: "Pending plan",
                value: snapshot.pendingDowngradePlan
                  ? toTitleCase(snapshot.pendingDowngradePlan)
                  : "None",
              },
              {
                key: "pending-effective-at",
                label: "Pending change effective at",
                value: formatBillingDate(snapshot.pendingDowngradeEffectiveAt),
              },
              {
                key: "pending-change-type",
                label: "Pending change type",
                value: pendingSummary.typeLabel,
              },
              {
                key: "trial-status",
                label: "Trial status",
                value: snapshot.trialStatus
                  ? toTitleCase(snapshot.trialStatus)
                  : "None",
              },
              {
                key: "trial-ends-at",
                label: "Trial ends at",
                value:
                  snapshot.trialEndsAt === null
                    ? "Not applicable"
                    : formatBillingDate(snapshot.trialEndsAt),
              },
            ]}
          />
        </Panel>
      </Tabs.Panel>

      <Tabs.Panel pt="md" value="plan">
        {visibilityOnly ? (
          <Panel
            title="Included Limits"
            subtitle="These limits apply to your current plan."
          >
            <PortalMetricGrid>
              <UsageSummaryCard
                label="Monthly requests"
                value={(
                  snapshot.includedLimits?.monthlyRequests ??
                  snapshot.usage.limit
                ).toLocaleString()}
              />
              <UsageSummaryCard
                label="Requests per minute"
                value={(
                  snapshot.includedLimits?.requestsPerMinute ?? 0
                ).toLocaleString()}
              />
              <UsageSummaryCard
                label="Batch items"
                value={(
                  snapshot.includedLimits?.batchItems ?? 0
                ).toLocaleString()}
              />
            </PortalMetricGrid>
          </Panel>
        ) : (
          <Panel
            title="Manage Plans"
            subtitle="Compare plans and choose the next billing action."
          >
            <PricingPlanGrid items={planItems} />
          </Panel>
        )}
      </Tabs.Panel>

      <Tabs.Panel pt="md" value="capabilities">
        {visibilityOnly ? (
          <Panel
            title="Enabled Capabilities"
            subtitle="Features available with your current plan."
          >
            <CapabilityVisibilityPanel snapshot={snapshot} />
          </Panel>
        ) : (
          <Panel
            title="Billing Tools"
            subtitle="Open invoice history and payment settings."
          >
            {billingActions.error ? (
              <PortalNotice tone="error">
                <p>{billingActions.error}</p>
              </PortalNotice>
            ) : null}

            <Paper p="lg" radius="lg" withBorder>
              <Stack gap="md">
                <div>
                  <Title order={4}>Open the Billing Portal</Title>
                  <Text c="dimmed" mt={4} size="sm">
                    Manage invoices and payment methods in the billing portal.
                  </Text>
                </div>
                <Group gap="sm" wrap="wrap">
                  <Button
                    disabled={!isAdmin}
                    loading={billingActions.isPending}
                    onClick={() => {
                      setStatusMessage(
                        "Opening the billing portal for invoices and payment details.",
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
                    Open Portal
                  </Button>
                </Group>
              </Stack>
            </Paper>

            <Text c="dimmed" fz="sm" mt="md">
              Your current plan is <strong>{session.plan}</strong>. Use this
              page to review usage, manage billing, and make plan changes.
            </Text>
          </Panel>
        )}
      </Tabs.Panel>
    </Tabs>
  );
}

function CapabilityVisibilityPanel(input: {
  snapshot: PortalUsageBillingSnapshot;
}) {
  const enabledFeatureFlags = (input.snapshot.featureFlags ?? []).filter(
    (item) => item.enabled,
  );
  const visibleCapabilities = (input.snapshot.enabledCapabilities ?? []).filter(
    (capability) => capability !== "verification",
  );

  if (visibleCapabilities.length === 0 && enabledFeatureFlags.length === 0) {
    return (
      <PortalNotice tone="warning">
        <p>
          No premium capabilities are enabled for the current plan beyond the
          included verification features.
        </p>
      </PortalNotice>
    );
  }

  return (
    <PortalMetricGrid>
      {visibleCapabilities.map((capability) => (
        <UsageSummaryCard
          key={capability}
          label="Capability"
          value={formatUsageMetricLabel(capability)}
        />
      ))}
      {enabledFeatureFlags.map((flag) => (
        <UsageSummaryCard
          key={flag.flagKey}
          label="Feature flag"
          value={flag.label}
        />
      ))}
    </PortalMetricGrid>
  );
}

function resolveUsageTotals(
  snapshot: PortalUsageBillingSnapshot,
): PortalUsageTotals {
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

function UsageSummaryGrid(input: { limit: number; totals: PortalUsageTotals }) {
  const items = [
    {
      key: "api-requests",
      label: "API requests",
      value: input.totals.apiRequests.toLocaleString(),
    },
    {
      key: "nonprofit-lookups",
      label: "Nonprofit lookups",
      value: input.totals.nonprofitLookupRequests.toLocaleString(),
    },
    {
      key: "search-requests",
      label: "Search requests",
      value: input.totals.searchRequests.toLocaleString(),
    },
    {
      key: "enrichment-requests",
      label: "Enrichment requests",
      value: input.totals.enrichmentRequests.toLocaleString(),
    },
    {
      key: "filing-lookups",
      label: "Filing lookups",
      value: input.totals.filingLookupRequests.toLocaleString(),
    },
    {
      key: "included-monthly-requests",
      label: "Included monthly requests",
      value: input.limit.toLocaleString(),
    },
  ];

  return (
    <section aria-label="Usage totals" className="portal-usage-summary-grid">
      <PortalDetailList columns={3} items={items} />
    </section>
  );
}

function UsageSummaryCard(input: { label: string; value: string }) {
  return <PortalMetricCard label={input.label} value={input.value} />;
}

function UsageMetricBreakdown(input: { metrics: PortalUsageMetricSummary[] }) {
  if (input.metrics.length === 0) {
    return null;
  }

  return (
    <section aria-label="Usage metric breakdown">
      <Stack gap="md">
        <Title order={3}>Usage Metrics Recorded This Month</Title>
        <div className="portal-usage-summary-grid">
          <PortalDetailList
            columns={3}
            items={input.metrics.map((metric) => ({
              key: metric.metricType,
              label: formatUsageMetricLabel(metric.metricType),
              value: (
                <div className="portal-usage-detail-value">
                  <strong>{metric.requestCount.toLocaleString()}</strong>
                  <span>{metric.lastUpdated ?? "Not yet updated"}</span>
                </div>
              ),
            }))}
          />
        </div>
      </Stack>
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
      footnote: "Starts checkout for the selected paid plan.",
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
        ? "Opening the billing portal."
        : "Opening checkout.",
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
  return ["free", "starter", "growth", "pro", "enterprise"].indexOf(planCode);
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

function toTitleCase(value: string): string {
  return value
    .trim()
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
}

function formatBillingDate(value: string | null | undefined) {
  if (!value) {
    return "Not scheduled";
  }

  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(parsed));
}
