import { Grid, Panel } from "@charity-status/shared-ui";

const plans = [
  {
    name: "Free",
    summary:
      "Entry point for nonprofit verification and light evaluation workflows.",
    details: "250 monthly requests and verification-focused capabilities.",
  },
  {
    name: "Starter",
    summary: "Adds more capacity and risk-oriented visibility.",
    details: "1,000 monthly requests with risk flags.",
  },
  {
    name: "Growth",
    summary: "The main expansion tier for teams doing deeper diligence.",
    details:
      "10,000 monthly requests with benchmarking and batch verification.",
  },
  {
    name: "Pro / Enterprise",
    summary:
      "For higher-scale monitoring, settings, and state-registry heavy workflows.",
    details:
      "Higher throughput, broader capabilities, and room for account-level controls.",
  },
];

export function PricingPage() {
  return (
    <Grid className="marketing-page-grid">
      <Panel
        title="Pricing posture"
        subtitle="This repo models plans and capabilities without publishing final public prices here."
      >
        <p>
          The public site should educate prospects on plan progression, free
          trial behavior, and hosted billing flows without hardcoding pricing
          details that may change outside the repo.
        </p>
      </Panel>

      {plans.map((plan) => (
        <Panel key={plan.name} title={plan.name} subtitle={plan.summary}>
          <p>{plan.details}</p>
        </Panel>
      ))}
    </Grid>
  );
}
