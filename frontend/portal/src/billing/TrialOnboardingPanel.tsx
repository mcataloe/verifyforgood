import { List, Stack, Text, Title } from "@mantine/core";
import {
  PortalMetricCard,
  PortalMetricGrid,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import type { PortalUsageBillingSnapshot } from "./portalUsageBilling";
import type { PortalPricingPlanItem } from "./usePortalPricingPlans";

interface TrialOnboardingPanelProps {
  plans: PortalPricingPlanItem[];
  snapshot: PortalUsageBillingSnapshot;
}

export function TrialOnboardingPanel({
  plans,
  snapshot,
}: TrialOnboardingPanelProps) {
  if (snapshot.plan !== "free") {
    return null;
  }

  const freePlan =
    plans.find((item) => item.plan.plan_code === "free")?.plan ?? null;
  const trialPlan =
    plans.find((item) => item.plan.plan_code === snapshot.effectiveAccessPlan)
      ?.plan ??
    plans.find((item) => item.plan.plan_code === "growth")?.plan ??
    null;

  if (snapshot.trialStatus === "active" && snapshot.trialEndsAt) {
    return (
      <PortalNotice tone="warning">
        <Stack gap="md">
          <div>
            <Title order={3}>Trial in Progress</Title>
            <Text c="dimmed" mt={4} size="sm">
              You are still on the free tier for billing, with temporary access
              to {trialPlan?.display_name ?? "expanded"} features while you
              evaluate the product.
            </Text>
          </div>

          <PortalMetricGrid>
            <PortalMetricCard
              label="Time remaining"
              value={formatRemainingTrialTime(snapshot.trialEndsAt)}
            />
            <PortalMetricCard
              label="Trial usage remaining"
              value={`${snapshot.usage.remaining.toLocaleString()} requests`}
            />
            <PortalMetricCard
              label="Expanded access"
              value={trialPlan?.display_name ?? "Configured trial tier"}
            />
          </PortalMetricGrid>

          <List spacing="xs">
            <List.Item>
              The free tier remains available after the trial window ends.
            </List.Item>
            <List.Item>There is no automatic paid conversion tied to this trial.</List.Item>
            <List.Item>
              Move to a paid plan only when the broader limits are useful.
            </List.Item>
          </List>
        </Stack>
      </PortalNotice>
    );
  }

  return (
    <PortalNotice tone="loading">
      <Stack gap="md">
        <div>
          <Title order={3}>Clear Limits, Optional Upgrade Path</Title>
          <Text c="dimmed" mt={4} size="sm">
            Begin with the free tier, then activate a time-limited trial when it
            helps you evaluate higher-capacity workflows. Paid enrollment stays
            a separate decision.
          </Text>
        </div>

        <PortalMetricGrid>
          <PortalMetricCard
            label="Free tier limit"
            value={
              freePlan
                ? `${freePlan.included_usage.monthly_requests.toLocaleString()} requests / month`
                : `${snapshot.usage.limit.toLocaleString()} requests / month`
            }
          />
          <PortalMetricCard
            label="Trial access"
            value={trialPlan?.display_name ?? "Configured trial tier"}
          />
          <PortalMetricCard
            label="Next step"
            value="Upgrade only when usage justifies it"
          />
        </PortalMetricGrid>

        <List spacing="xs">
          <List.Item>
            The free tier is useful on its own and does not require a card.
          </List.Item>
          <List.Item>
            Trial timing stays backend-configured, so the UI can adapt if the
            trial window changes later.
          </List.Item>
          <List.Item>
            Paid plans are presented clearly without forcing an immediate
            choice.
          </List.Item>
        </List>
      </Stack>
    </PortalNotice>
  );
}

function formatRemainingTrialTime(endsAt: string): string {
  const remainingMs = new Date(endsAt).getTime() - Date.now();

  if (Number.isNaN(remainingMs) || remainingMs <= 0) {
    return "Ending soon";
  }

  const remainingHours = Math.ceil(remainingMs / (1000 * 60 * 60));
  if (remainingHours < 24) {
    return `${remainingHours} hour${remainingHours === 1 ? "" : "s"} left`;
  }

  const remainingDays = Math.ceil(remainingHours / 24);
  return `${remainingDays} day${remainingDays === 1 ? "" : "s"} left`;
}
