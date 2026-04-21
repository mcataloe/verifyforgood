import { Group, Progress, Stack, Text, Title } from "@mantine/core";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import {
  PortalDetailList,
} from "../components/PortalPrimitives";
import type {
  PortalBudgetStatus,
  PortalUsageSnapshot,
} from "./portalUsageBilling";

interface UsageContextPanelProps {
  budgetStatus: PortalBudgetStatus;
  plan: PricingPlanMetadata | null;
  usage: PortalUsageSnapshot;
}

export function UsageContextPanel({
  budgetStatus,
  plan,
  usage,
}: UsageContextPanelProps) {
  const includedQuota = plan?.included_usage.monthly_requests ?? usage.limit;
  const overageUnitPriceMicros =
    plan?.per_request_pricing.amount_usd_micros ?? null;
  const forecast = estimateMonthEndUsage(usage.used, includedQuota, new Date());
  const projectedOverageRequests = Math.max(
    0,
    forecast.projectedTotal - includedQuota,
  );
  const projectedOverageCostMicros =
    overageUnitPriceMicros === null
      ? null
      : projectedOverageRequests * overageUnitPriceMicros;

  return (
    <Stack gap="md" className="portal-usage-context">
      <Group align="start" justify="space-between" wrap="wrap">
        <div>
          <Title order={3}>Usage compared with this plan&apos;s included quota</Title>
          <Text c="dimmed" mt={4} size="sm">
            Current month usage and estimate based on average daily requests so
            far this month.
          </Text>
        </div>
        <Text fw={700} size="sm">
          Projected month end: {forecast.projectedPercent}% of included quota
        </Text>
      </Group>

      <PortalDetailList
        columns={3}
        items={[
          {
            key: "current-usage",
            label: "Current usage",
            value: `${usage.used.toLocaleString()} / ${includedQuota.toLocaleString()}`,
          },
          {
            key: "remaining-usage",
            label: "Remaining in current period",
            value: `${usage.remaining.toLocaleString()} requests`,
          },
          {
            key: "current-percent",
            label: "Current usage share",
            value: `${usage.usagePercent}% of included quota`,
          },
        ]}
      />

      <UsageProgressRow
        label="Current usage"
        progress={usage.usagePercent}
        value={`${usage.used.toLocaleString()} requests used`}
      />
      <UsageProgressRow
        label="Projected month end"
        progress={forecast.projectedPercent}
        value={`About ${forecast.projectedTotal.toLocaleString()} requests`}
      />

      <div className="portal-usage-summary-grid">
        <PortalDetailList
          columns={3}
          items={[
            {
              key: "included-quota",
              label: "Included quota",
              value: `${includedQuota.toLocaleString()} requests`,
            },
            {
              key: "current-pace",
              label: "Current pace",
              value: `${forecast.dailyAverage.toLocaleString()} requests / day`,
            },
            {
              key: "projected-month-end",
              label: "Projected month end",
              value: `${forecast.projectedTotal.toLocaleString()} requests`,
            },
            {
              key: "cost-scaling",
              label: "Cost scaling",
              value:
                overageUnitPriceMicros === null
                  ? "Unavailable"
                  : `${formatUsdMicros(overageUnitPriceMicros)} per extra request`,
            },
            {
              key: "forecast-summary",
              label: "Forecast summary",
              value: describeForecast({
                budgetStatus,
                forecast,
                includedQuota,
                projectedOverageCostMicros,
                projectedOverageRequests,
              }),
            },
            {
              key: "forecast-window",
              label: "Forecast window",
              value: `Based on ${forecast.daysElapsed} day${forecast.daysElapsed === 1 ? "" : "s"} completed so far, with ${forecast.daysRemaining} day${forecast.daysRemaining === 1 ? "" : "s"} left in the month.`,
            },
          ]}
        />
      </div>
    </Stack>
  );
}

function UsageProgressRow(input: {
  label: string;
  progress: number;
  value: string;
}) {
  return (
    <Stack gap={6}>
      <Group justify="space-between" wrap="wrap">
        <Text fw={600} size="sm">
          {input.label}
        </Text>
        <Text c="dimmed" size="sm">
          {input.value}
        </Text>
      </Group>
      <Progress radius="xl" value={Math.min(100, input.progress)} />
    </Stack>
  );
}

function estimateMonthEndUsage(
  used: number,
  includedQuota: number,
  today: Date,
): {
  dailyAverage: number;
  daysElapsed: number;
  daysRemaining: number;
  projectedPercent: number;
  projectedTotal: number;
  status: "within_quota" | "near_quota" | "over_quota";
} {
  const totalDays = new Date(
    today.getFullYear(),
    today.getMonth() + 1,
    0,
  ).getDate();
  const daysElapsed = Math.min(totalDays, Math.max(1, today.getDate()));
  const daysRemaining = Math.max(0, totalDays - daysElapsed);
  const dailyAverage = Math.max(1, Math.round(used / daysElapsed));
  const projectedTotal = Math.max(
    used,
    Math.round((used / daysElapsed) * totalDays),
  );
  const projectedPercent =
    includedQuota > 0 ? Math.round((projectedTotal / includedQuota) * 100) : 0;

  return {
    dailyAverage,
    daysElapsed,
    daysRemaining,
    projectedPercent,
    projectedTotal,
    status:
      projectedPercent > 100
        ? "over_quota"
        : projectedPercent >= 85
          ? "near_quota"
          : "within_quota",
  };
}

function describeForecast(input: {
  budgetStatus: PortalBudgetStatus;
  forecast: {
    projectedPercent: number;
    projectedTotal: number;
    status: "within_quota" | "near_quota" | "over_quota";
  };
  includedQuota: number;
  projectedOverageCostMicros: number | null;
  projectedOverageRequests: number;
}): string {
  if (input.forecast.status === "within_quota") {
    return `At this pace, usage should stay within the included quota, finishing around ${input.forecast.projectedTotal.toLocaleString()} requests for the month.`;
  }

  if (input.forecast.status === "near_quota") {
    return `At this pace, usage is likely to finish close to the included quota of ${input.includedQuota.toLocaleString()} requests, so it may be worth watching before month end.`;
  }

  if (!input.budgetStatus.allowOverage) {
    return `At this pace, usage would likely exceed the included quota by about ${input.projectedOverageRequests.toLocaleString()} requests. Hard stop is enabled, so requests should stop near the limit unless the cap or plan changes.`;
  }

  if (input.projectedOverageCostMicros !== null) {
    return `At this pace, usage would likely go about ${input.projectedOverageRequests.toLocaleString()} requests beyond the included quota, which is about ${formatUsdMicros(input.projectedOverageCostMicros)} in usage-based charges.`;
  }

  return `At this pace, usage would likely go about ${input.projectedOverageRequests.toLocaleString()} requests beyond the included quota.`;
}

function formatUsdMicros(amountUsdMicros: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 3,
    minimumFractionDigits: 3,
    style: "currency",
  }).format(amountUsdMicros / 1_000_000);
}
