import { Grid, Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { DocsEndpoints } from "../app/docsEndpoints";

interface GettingStartedPageProps {
  endpoints: DocsEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
}

export function GettingStartedPage({
  endpoints,
  runtimeConfig,
}: GettingStartedPageProps) {
  return (
    <Grid className="docs-page-grid">
      <Panel
        title="Start here"
        subtitle="The first docs stop for customers and developers."
      >
        <ol className="docs-list docs-list--ordered">
          <li>
            Understand the product's verification and monitoring use cases.
          </li>
          <li>Pick an auth mode: API key or OAuth client credentials.</li>
          <li>
            Test the core API flows against the current `/
            {runtimeConfig.apiVersion}` routes.
          </li>
          <li>
            Expand into settings, usage, billing, and integrations as adoption
            grows.
          </li>
        </ol>
      </Panel>

      <Panel
        title="Early endpoint anchors"
        subtitle="Backed by the current customer-facing API contract."
      >
        <ul className="docs-list">
          <li>
            Search nonprofits: <code>{endpoints.nonprofitSearch}</code>
          </li>
          <li>
            Verify nonprofit data: <code>{endpoints.nonprofitLookup}</code>
          </li>
          <li>
            Batch verification: <code>{endpoints.verifyBatch}</code>
          </li>
        </ul>
      </Panel>
    </Grid>
  );
}
