import { Paper, Progress, Stack, Text, Title } from "@mantine/core";
import { PortalDetailList } from "../components/PortalPrimitives";
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
      <Text c="dimmed" size="sm">
        Current usage will appear here once the billing summary is available.
      </Text>
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
    <Paper p="lg" radius="lg" withBorder>
      <Stack gap="md">
        <div>
          <Title order={3}>
            {snapshot.usage.used.toLocaleString()} / {limit.toLocaleString()}
          </Title>
          <Text c="dimmed" mt={4} size="sm">
            {describeUsageState({
              allowOverage,
              configuredLimit,
              remaining,
            })}
          </Text>
        </div>

        <Text fw={700} size="sm">
          {usagePercent}% of this limit
        </Text>
        <Progress radius="xl" value={usagePercent} />

        <PortalDetailList
          items={[
            {
              key: "current-usage",
              label: "Current usage",
              value: `${snapshot.usage.used.toLocaleString()} requests`,
            },
            {
              key: "remaining",
              label: "Remaining to this limit",
              value: `${remaining.toLocaleString()} requests`,
            },
            {
              key: "limit-source",
              label: "Limit source",
              value: limitLabel,
            },
            {
              key: "enforcement-mode",
              label: "Enforcement mode",
              value: allowOverage ? "Overage allowed" : "Hard stop enabled",
            },
          ]}
        />
      </Stack>
    </Paper>
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
