import { ErrorState, LoadingSkeleton, PricingPlanGrid } from "@charity-status/shared-ui";
import { usePortalPricingPlans } from "../billing/usePortalPricingPlans";
import { PortalPageShell } from "../components/shell";

export function ComparePlansPage() {
  const pricing = usePortalPricingPlans(null);

  return (
    <PortalPageShell
      description="Compare plan features, cost, and API limits to choose the right plan for your organization."
      title="Compare Plans"
    >
      {pricing.isLoading ? (
        <LoadingSkeleton
          description="Loading the current plan catalog."
          title="Loading plans"
          variant="card"
        />
      ) : null}
      {pricing.error ? (
        <ErrorState description={pricing.error} title="Plans unavailable" />
      ) : null}
      {!pricing.isLoading && !pricing.error ? (
        <PricingPlanGrid items={pricing.plans} />
      ) : null}
    </PortalPageShell>
  );
}
