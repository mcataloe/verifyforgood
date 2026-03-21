import type { PricingPlanMetadata } from "@charity-status/shared-types";
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
    <section className="portal-usage-context" aria-label="Usage context">
      <div className="portal-usage-context__header">
        <div>
          <p className="portal-shell__eyebrow">Usage context</p>
          <h3>Usage compared with this plan&apos;s included quota</h3>
          <p>
            Simple month-end estimate based on average daily requests so far in
            this month.
          </p>
        </div>
        <span
          className={`portal-key-chip ${resolveForecastChipClass(
            forecast.status,
          )}`}
        >
          {forecast.projectedPercent}% projected
        </span>
      </div>

      <div className="portal-usage-context__bars">
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
      </div>

      <div className="portal-usage-context__metrics">
        <MetricCard
          label="Included quota"
          value={`${includedQuota.toLocaleString()} requests`}
        />
        <MetricCard
          label="Current pace"
          value={`${forecast.dailyAverage.toLocaleString()} requests / day`}
        />
        <MetricCard
          label="Projected month end"
          value={`${forecast.projectedTotal.toLocaleString()} requests`}
        />
        <MetricCard
          label="Cost scaling"
          value={
            overageUnitPriceMicros === null
              ? "Unavailable"
              : `${formatUsdMicros(overageUnitPriceMicros)} per extra request`
          }
        />
      </div>

      <p className="portal-usage-context__summary">
        {describeForecast({
          budgetStatus,
          forecast,
          includedQuota,
          projectedOverageCostMicros,
          projectedOverageRequests,
        })}
      </p>

      <p className="portal-usage-context__footnote">
        Based on {forecast.daysElapsed} day
        {forecast.daysElapsed === 1 ? "" : "s"} completed so far, with{" "}
        {forecast.daysRemaining} day
        {forecast.daysRemaining === 1 ? "" : "s"} left in the month.
      </p>
    </section>
  );
}

function UsageProgressRow(input: {
  label: string;
  progress: number;
  value: string;
}) {
  return (
    <div className="portal-usage-context__bar-row">
      <div className="portal-usage-context__bar-copy">
        <strong>{input.label}</strong>
        <span>{input.value}</span>
      </div>
      <div className="portal-usage-context__bar-track" aria-hidden="true">
        <div
          className="portal-usage-context__bar-fill"
          style={{ width: `${Math.min(100, input.progress)}%` }}
        />
      </div>
    </div>
  );
}

function MetricCard(input: { label: string; value: string }) {
  return (
    <div className="portal-usage-context__metric">
      <span>{input.label}</span>
      <strong>{input.value}</strong>
    </div>
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

function resolveForecastChipClass(
  status: "within_quota" | "near_quota" | "over_quota",
): string {
  if (status === "within_quota") {
    return "portal-key-chip--active";
  }

  if (status === "over_quota") {
    return "portal-key-chip--revoked";
  }

  return "";
}
