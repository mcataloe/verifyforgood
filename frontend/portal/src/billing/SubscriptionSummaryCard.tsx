import { Alert, Stack } from "@mantine/core";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { PortalDetailList } from "../components/PortalPrimitives";
import type { PortalUsageBillingSnapshot } from "./portalUsageBilling";

interface SubscriptionSummaryCardProps {
  currentPlan: PricingPlanMetadata | null;
  snapshot: PortalUsageBillingSnapshot;
}

export function SubscriptionSummaryCard({
  currentPlan,
  snapshot,
}: SubscriptionSummaryCardProps) {
  const presentation = getSubscriptionStatusPresentation(snapshot);

  return (
    <Alert color={resolveToneColor(presentation.tone)} radius="lg" title={presentation.title} variant="light">
      <Stack gap="md">
        <p style={{ margin: 0 }}>{presentation.description}</p>
        <PortalDetailList
          items={[
            {
              key: "summary",
              label: "Summary",
              value: presentation.label,
            },
            {
              key: "current-plan",
              label: "Current plan",
              value:
                snapshot.planDisplayName ??
                currentPlan?.display_name ??
                formatPlanLabel(snapshot.plan),
            },
            {
              key: "subscription-status",
              label: "Subscription status",
              value: formatBillingState(
                snapshot.subscriptionStatus ?? presentation.label,
              ),
            },
            {
              key: "current-period-end",
              label: "Current period end",
              value: formatDateLabel(snapshot.billingCycleEnd ?? snapshot.renewalDate),
            },
            {
              key: "billing-state",
              label: "Billing state",
              value: formatBillingState(snapshot.billingStatus),
            },
          ]}
        />
      </Stack>
    </Alert>
  );
}

type SubscriptionTone = "active" | "warning" | "critical";

interface SubscriptionPresentation {
  description: string;
  label: string;
  title: string;
  tone: SubscriptionTone;
}

function getSubscriptionStatusPresentation(
  snapshot: PortalUsageBillingSnapshot,
): SubscriptionPresentation {
  const trialState = normalizeStatusToken(snapshot.trialStatus);
  const billingState = normalizeStatusToken(snapshot.billingStatus);
  const pendingChangeType = normalizeStatusToken(snapshot.pendingChangeType);

  if (pendingChangeType === "cancellation_scheduled") {
    return {
      description:
        "Cancellation is scheduled for the current billing period end. Access remains available until that effective date unless the plan is resumed earlier.",
      label: "Cancels soon",
      title: "Cancellation is scheduled",
      tone: "warning",
    };
  }

  if (trialState === "active" || billingState === "trialing") {
    return {
      description:
        "Trial access is active now. Renewal and plan changes remain visible so there are no surprises.",
      label: "Trial",
      title: "Trial access is active",
      tone: "warning",
    };
  }

  if (billingState === "past_due") {
    return {
      description:
        "Billing needs attention. Access and renewal details stay visible while the account is resolved.",
      label: "Past due",
      title: "Billing action needed",
      tone: "critical",
    };
  }

  if (billingState === "expired") {
    return {
      description:
        "The prior subscription term has ended. The portal is showing the latest known plan and billing details.",
      label: "Expired",
      title: "Subscription expired",
      tone: "critical",
    };
  }

  return {
    description:
      "The subscription is active and billing details are up to date with the current backend visibility.",
    label: "Active",
    title: "Subscription is in good standing",
    tone: "active",
  };
}

function resolveToneColor(tone: SubscriptionTone) {
  switch (tone) {
    case "critical":
      return "red";
    case "warning":
      return "yellow";
    case "active":
    default:
      return "green";
  }
}

function normalizeStatusToken(value: string | null): string {
  if (!value) {
    return "";
  }

  return value.trim().toLowerCase().replace(/\s+/g, "_");
}

function formatBillingState(value: string): string {
  const normalized = normalizeStatusToken(value);

  switch (normalized) {
    case "past_due":
      return "Past due";
    case "payment_failed":
      return "Payment failed";
    case "trialing":
      return "Trialing";
    case "expired":
      return "Expired";
    case "not_enrolled":
      return "Not enrolled";
    case "active":
      return "Active";
    default:
      return toTitleCase(value);
  }
}

function formatPlanLabel(value: string): string {
  return toTitleCase(value);
}

function formatDateLabel(value: string | null): string {
  if (!value) {
    return "Not scheduled";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(parsed);
}

function toTitleCase(value: string): string {
  return value
    .trim()
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
}
