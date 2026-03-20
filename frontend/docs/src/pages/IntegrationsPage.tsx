import { Grid, Panel } from "@charity-status/shared-ui";

export function IntegrationsPage() {
  return (
    <Grid className="docs-page-grid">
      <Panel title="Integration examples" subtitle="A central place for workflow-oriented reference content.">
        <ul className="docs-list">
          <li>API-first nonprofit verification workflows.</li>
          <li>Organization settings and billing-aware account configuration.</li>
          <li>Future partner and customer workflow recipes.</li>
        </ul>
      </Panel>

      <Panel title="M365 Power Automate stub" subtitle="Explicitly reserved because it was called out as an early example.">
        <ol className="docs-list docs-list--ordered">
          <li>Trigger a flow from a form, CRM event, or list item change.</li>
          <li>Call the VerifyForGood API with an issued API key or OAuth token.</li>
          <li>Store the nonprofit result, score, and source evidence in the downstream system.</li>
          <li>Escalate exceptions or missing required integrations into a manual review path.</li>
        </ol>
      </Panel>
    </Grid>
  );
}
