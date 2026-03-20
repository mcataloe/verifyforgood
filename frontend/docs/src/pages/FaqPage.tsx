import { Grid, Panel } from "@charity-status/shared-ui";

export function FaqPage() {
  return (
    <Grid className="docs-page-grid">
      <Panel
        title="Common questions"
        subtitle="Support-oriented placeholders grounded in current docs."
      >
        <ul className="docs-list">
          <li>
            <strong>How do customers authenticate?</strong> Through API keys or
            OAuth client credentials.
          </li>
          <li>
            <strong>
              Does the platform define final public prices in-repo?
            </strong>{" "}
            No, plan capabilities are modeled here, but final public pricing is
            intentionally not hardcoded.
          </li>
          <li>
            <strong>
              Can customers manage billing without product access?
            </strong>{" "}
            Self-service billing routes remain available during billing
            restrictions.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Support content direction"
        subtitle="Ready for future customer and internal support references."
      >
        <ul className="docs-list">
          <li>Account and workspace setup guidance.</li>
          <li>Billing/trial explanations.</li>
          <li>Integration and troubleshooting notes.</li>
        </ul>
      </Panel>
    </Grid>
  );
}
