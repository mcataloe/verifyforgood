import { Grid, Panel } from "@charity-status/shared-ui";

export function ProductPage() {
  return (
    <Grid className="marketing-page-grid">
      <Panel
        title="Core product story"
        subtitle="Deliberate placeholders for future richer content blocks."
      >
        <ul className="marketing-list">
          <li>
            Verification by EIN with deterministic scoring and explainable
            outputs.
          </li>
          <li>
            Source inspection for filings, compliance, and provenance-sensitive
            workflows.
          </li>
          <li>
            Batch and premium capabilities that expand with plan entitlements.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Likely future expansions"
        subtitle="Kept local to marketing until reuse is proven."
      >
        <ul className="marketing-list">
          <li>Industry-specific proof points and segment landing pages.</li>
          <li>Interactive product tours and comparison narratives.</li>
          <li>Conversion modules tied to demo and trial journeys.</li>
        </ul>
      </Panel>
    </Grid>
  );
}
