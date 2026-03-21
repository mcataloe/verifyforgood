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
        <div className="portal-onboarding-panel">
          <div>
            <p className="portal-shell__eyebrow">Optional trial</p>
            <h3 className="portal-onboarding-panel__title">
              Trial in progress
            </h3>
            <p className="portal-onboarding-panel__copy">
              You are still on the free tier for billing, with temporary access
              to {trialPlan?.display_name ?? "expanded"} features while you
              evaluate the product.
            </p>
          </div>

          <div className="portal-onboarding-metrics">
            <div className="portal-onboarding-metric">
              <span>Time remaining</span>
              <strong>{formatRemainingTrialTime(snapshot.trialEndsAt)}</strong>
            </div>
            <div className="portal-onboarding-metric">
              <span>Trial usage remaining</span>
              <strong>
                {snapshot.usage.remaining.toLocaleString()} requests
              </strong>
            </div>
            <div className="portal-onboarding-metric">
              <span>Expanded access</span>
              <strong>
                {trialPlan?.display_name ?? "Configured trial tier"}
              </strong>
            </div>
          </div>

          <ul className="portal-list">
            <li>
              The free tier remains available after the trial window ends.
            </li>
            <li>There is no automatic paid conversion tied to this trial.</li>
            <li>
              Move to a paid plan only when the broader limits are useful.
            </li>
          </ul>
        </div>
      </PortalNotice>
    );
  }

  return (
    <PortalNotice tone="loading">
      <div className="portal-onboarding-panel">
        <div>
          <p className="portal-shell__eyebrow">Start on free</p>
          <h3 className="portal-onboarding-panel__title">
            Clear limits, optional upgrade path
          </h3>
          <p className="portal-onboarding-panel__copy">
            Begin with the free tier, then activate a time-limited trial when it
            helps you evaluate higher-capacity workflows. Paid enrollment stays
            a separate decision.
          </p>
        </div>

        <div className="portal-onboarding-metrics">
          <div className="portal-onboarding-metric">
            <span>Free tier limit</span>
            <strong>
              {freePlan
                ? `${freePlan.included_usage.monthly_requests.toLocaleString()} requests / month`
                : `${snapshot.usage.limit.toLocaleString()} requests / month`}
            </strong>
          </div>
          <div className="portal-onboarding-metric">
            <span>Trial access</span>
            <strong>
              {trialPlan?.display_name ?? "Configured trial tier"}
            </strong>
          </div>
          <div className="portal-onboarding-metric">
            <span>Next step</span>
            <strong>Upgrade only when usage justifies it</strong>
          </div>
        </div>

        <ul className="portal-list">
          <li>
            The free tier is useful on its own and does not require a card.
          </li>
          <li>
            Trial timing stays backend-configured, so the UI can adapt if the
            trial window changes later.
          </li>
          <li>
            Paid plans are presented clearly without forcing an immediate
            choice.
          </li>
        </ul>
      </div>
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
