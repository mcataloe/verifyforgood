import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import { Grid, Panel, PricingPlanGrid } from "@charity-status/shared-ui";
import {
  useMarketingPricingPlans,
  type MarketingPricingPlansController,
} from "../pricing/useMarketingPricingPlans";

interface PricingPageProps {
  controller?: MarketingPricingPlansController;
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;
}

export function PricingPage({ controller, runtimeConfig }: PricingPageProps) {
  const defaultController = useMarketingPricingPlans(runtimeConfig);
  const pricing = controller ?? defaultController;

  return (
    <Grid className="marketing-page-grid">
      <Panel
        title="Plan catalog"
        subtitle="Marketing and portal plan displays now render from backend-authored plan metadata."
      >
        <p>
          Included usage, overage pricing, and feature availability come from
          the public <code>/v1/plans</code> contract. Customer-facing monthly
          subscription pricing remains in Stripe-hosted checkout until the
          backend exposes it directly.
        </p>
      </Panel>

      {pricing.isLoading ? (
        <Panel
          title="Loading plan catalog"
          subtitle="Fetching backend-authored pricing metadata."
        >
          <p>Loading included usage, overage pricing, and feature flags.</p>
        </Panel>
      ) : null}

      {!pricing.isLoading && pricing.error ? (
        <Panel
          title="Plan catalog unavailable"
          subtitle="The public pricing surface could not load the backend plan catalog."
        >
          <p>{pricing.error}</p>
          <button type="button" onClick={() => void pricing.reload()}>
            Retry loading pricing
          </button>
        </Panel>
      ) : null}

      {!pricing.isLoading && !pricing.error ? (
        <PricingPlanGrid
          items={pricing.plans.map((plan) => ({
            highlighted: plan.plan_code === "growth",
            plan,
          }))}
        />
      ) : null}
    </Grid>
  );
}
