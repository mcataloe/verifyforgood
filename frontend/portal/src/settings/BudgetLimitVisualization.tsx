import type { PortalUsageBillingSnapshot } from "../billing/portalUsageBilling";

interface BudgetLimitVisualizationProps {
  allowOverage: boolean;
  configuredLimit: number | null;
  snapshot: PortalUsageBillingSnapshot | null;
}

export function BudgetLimitVisualization({
  allowOverage,
  configuredLimit,
  snapshot,
}: BudgetLimitVisualizationProps) {
  if (!snapshot) {
    return (
      <p className="portal-budget-visualization__empty">
        Current usage will appear here once the billing summary is available.
      </p>
    );
  }

  const limit = configuredLimit ?? snapshot.usage.limit;
  const limitLabel =
    configuredLimit === null ? "Included plan limit" : "Configured cap";
  const remaining = Math.max(0, limit - snapshot.usage.used);
  const usagePercent =
    limit > 0
      ? Math.min(100, Math.round((snapshot.usage.used / limit) * 100))
      : 0;

  return (
    <div className="portal-budget-visualization">
      <div className="portal-budget-visualization__header">
        <div>
          <p className="portal-shell__eyebrow">{limitLabel}</p>
          <h3>
            {snapshot.usage.used.toLocaleString()} / {limit.toLocaleString()}
          </h3>
          <p>
            {describeUsageState({
              allowOverage,
              configuredLimit,
              remaining,
            })}
          </p>
        </div>
        <p className="portal-budget-visualization__percent">
          {usagePercent}% of this limit
        </p>
      </div>

      <div className="portal-usage-meter__track" aria-hidden="true">
        <div
          className="portal-usage-meter__fill"
          style={{ width: `${usagePercent}%` }}
        />
      </div>

      <dl className="portal-shell__details">
        <div>
          <dt>Current usage</dt>
          <dd>{snapshot.usage.used.toLocaleString()} requests</dd>
        </div>
        <div>
          <dt>Remaining to this limit</dt>
          <dd>{remaining.toLocaleString()} requests</dd>
        </div>
        <div>
          <dt>Limit source</dt>
          <dd>{limitLabel}</dd>
        </div>
        <div>
          <dt>Enforcement mode</dt>
          <dd>{allowOverage ? "Overage allowed" : "Hard stop enabled"}</dd>
        </div>
      </dl>
    </div>
  );
}

function describeUsageState(input: {
  allowOverage: boolean;
  configuredLimit: number | null;
  remaining: number;
}): string {
  if (input.remaining > 0 && !input.allowOverage) {
    return `${input.remaining.toLocaleString()} requests remain before the hard stop is reached.`;
  }

  if (input.remaining > 0 && input.configuredLimit !== null) {
    return `${input.remaining.toLocaleString()} requests remain before the configured cap, with overage still allowed after that point.`;
  }

  if (input.remaining > 0) {
    return `${input.remaining.toLocaleString()} requests remain in the included plan allowance.`;
  }

  if (input.allowOverage) {
    return "This limit has been reached, but requests can continue because hard-stop enforcement is disabled.";
  }

  return "This limit has been reached. Additional requests should stop until the next billing period or until the cap is changed.";
}
