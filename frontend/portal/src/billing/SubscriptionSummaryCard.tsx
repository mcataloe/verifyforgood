import type { PricingPlanMetadata } from "@charity-status/shared-types";
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
    <section className="portal-subscription-summary">
      <div className="portal-subscription-summary__header">
        <div>
          <p className="portal-shell__eyebrow">Subscription summary</p>
          <h3 className="portal-subscription-summary__title">
            {presentation.title}
          </h3>
          <p className="portal-subscription-summary__copy">
            {presentation.description}
          </p>
        </div>
        <span
          className={`portal-subscription-status portal-subscription-status--${presentation.tone}`}
        >
          {presentation.label}
        </span>
      </div>

      <dl className="portal-subscription-summary__grid">
        <div>
          <dt>Current plan</dt>
          <dd>{currentPlan?.display_name ?? formatPlanLabel(snapshot.plan)}</dd>
        </div>
        <div>
          <dt>Subscription status</dt>
          <dd>{presentation.label}</dd>
        </div>
        <div>
          <dt>Renewal date</dt>
          <dd>{formatDateLabel(snapshot.renewalDate)}</dd>
        </div>
        <div>
          <dt>Billing state</dt>
          <dd>{formatBillingState(snapshot.billingStatus)}</dd>
        </div>
      </dl>
    </section>
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
