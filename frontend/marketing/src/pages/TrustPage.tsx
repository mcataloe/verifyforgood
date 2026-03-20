import { Grid, Panel } from "@charity-status/shared-ui";

export function TrustPage() {
  return (
    <Grid className="marketing-page-grid">
      <Panel
        title="Trust posture"
        subtitle="Public trust cues should reflect the actual platform, not generic claims."
      >
        <ul className="marketing-list">
          <li>
            Deterministic scoring and audit-friendly evidence remain central
            product claims.
          </li>
          <li>
            Hosted billing and customer self-service are delegated to
            Stripe-hosted surfaces.
          </li>
          <li>
            Customer-facing branding is configuration-driven, while platform
            internals stay capability-based.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Security and reliability themes"
        subtitle="Intentional placeholders for future expansion."
      >
        <ul className="marketing-list">
          <li>
            Infrastructure and runtime identity are separated from public
            branding.
          </li>
          <li>
            Support metadata can be surfaced through standard API error
            envelopes.
          </li>
          <li>
            Future trust content can grow here without inheriting
            authenticated-app layout assumptions.
          </li>
        </ul>
      </Panel>
    </Grid>
  );
}
