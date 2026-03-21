import { Grid, Panel } from "@charity-status/shared-ui";

export function ProductOverviewPage() {
  return (
    <Grid className="docs-page-grid">
      <Panel
        title="Current product shape"
        subtitle="Content structure that can serve customers and internal references."
      >
        <ul className="docs-list">
          <li>Verification by EIN and name-based search.</li>
          <li>
            Source-level inspection, filings, compliance, and federal-award
            views.
          </li>
          <li>
            Customer-managed organization settings and billing-aware access
            controls.
          </li>
          <li>Progressive plan tiers from free through enterprise.</li>
        </ul>
      </Panel>

      <Panel
        title="Documentation intent"
        subtitle="This app is a docs surface, not a docs platform."
      >
        <ul className="docs-list">
          <li>No markdown engine or CMS is required yet.</li>
          <li>
            Product, API, integration, and support guidance can grow page by
            page.
          </li>
          <li>
            Portal and marketing remain separate runtimes with their own
            concerns.
          </li>
        </ul>
      </Panel>
    </Grid>
  );
}
