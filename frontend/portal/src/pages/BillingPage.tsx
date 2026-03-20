import { Grid, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalSessionStub } from "../app/portalSession";

interface BillingPageProps {
  endpoints: PortalEndpoints;
  session: PortalSessionStub;
}

export function BillingPage({ endpoints, session }: BillingPageProps) {
  return (
    <Grid className="portal-page-grid">
      <Panel title="Usage and billing IA" subtitle="Aligned to the current customer-facing billing routes.">
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
      </Panel>

      <Panel title="Current assumptions" subtitle="These come from the existing backend docs, not portal-only invention.">
        <ul className="portal-list">
          <li>Billing access is anchored to account context.</li>
          <li>Stripe-hosted checkout and portal stay external.</li>
          <li>Trials can grant Growth access while billing plan remains `free`.</li>
          <li>Hard-stop overage behavior belongs in settings and usage messaging, not auth wiring.</li>
        </ul>
        <p>
          Current stubbed plan for this workspace: <strong>{session.plan}</strong>
        </p>
      </Panel>
    </Grid>
  );
}
