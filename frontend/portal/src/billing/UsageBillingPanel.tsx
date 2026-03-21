import { Grid, Panel } from "@charity-status/shared-ui";
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

interface UsageBillingPanelProps {
  controller?: PortalUsageBillingController;
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function UsageBillingPanel({
  controller,
  endpoints,
  session,
}: UsageBillingPanelProps) {
  const defaultController = usePortalUsageBilling(session);
  const billing = controller ?? defaultController;

  if (billing.isLoading) {
    return (
      <PortalLoadingState
        subtitle="Fetching the current customer billing summary."
        title="Loading usage and billing"
      >
        <p>Loading plan, request usage, and overage policy state.</p>
      </PortalLoadingState>
    );
  }

  if (billing.error || !billing.snapshot) {
    return (
      <PortalErrorState
        actionLabel="Retry billing summary"
        message={billing.error ?? "No billing summary is available right now."}
        onAction={() => {
          void billing.reload();
        }}
        subtitle="The portal could not load the current usage and billing state."
        title="Billing summary unavailable"
      />
    );
  }

  const { snapshot } = billing;

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Usage and billing state"
        subtitle="Simple customer-facing visibility into plan, request usage, and budget enforcement."
      >
        {snapshot.notice ? (
          <PortalNotice tone="warning">
            <p>{snapshot.notice}</p>
          </PortalNotice>
        ) : null}

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

        <dl className="portal-shell__details">
          <div>
            <dt>Current plan</dt>
            <dd>{snapshot.plan}</dd>
          </div>
          <div>
            <dt>Effective access</dt>
            <dd>{snapshot.effectiveAccessPlan}</dd>
          </div>
          <div>
            <dt>Billing status</dt>
            <dd>{snapshot.billingStatus}</dd>
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
            <dt>Data source</dt>
            <dd>{snapshot.source}</dd>
          </div>
        </dl>
      </Panel>

      <Panel
        title="Renewal and billing actions"
        subtitle="Product-focused state from the existing billing endpoints."
      >
        <dl className="portal-shell__details">
          <div>
            <dt>Renewal date</dt>
            <dd>{snapshot.renewalDate ?? "Not scheduled"}</dd>
          </div>
          <div>
            <dt>Pending downgrade</dt>
            <dd>{snapshot.pendingDowngradePlan ?? "None"}</dd>
          </div>
          <div>
            <dt>Pending downgrade effective at</dt>
            <dd>{snapshot.pendingDowngradeEffectiveAt ?? "Not scheduled"}</dd>
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

        <ul className="portal-list">
          <li>
            Subscription summary: <code>{endpoints.billingSubscription}</code>
          </li>
          <li>
            Checkout session: <code>{endpoints.billingCheckout}</code>
          </li>
          <li>
            Plan change: <code>{endpoints.billingPlanChange}</code>
          </li>
          <li>
            Stripe customer portal: <code>{endpoints.billingPortal}</code>
          </li>
        </ul>

        <p>
          Signed in plan baseline: <strong>{session.plan}</strong>
        </p>
      </Panel>
    </Grid>
  );
}
