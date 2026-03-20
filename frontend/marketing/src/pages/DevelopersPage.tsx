import { Grid, Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { MarketingEndpoints } from "../app/marketingEndpoints";

interface DevelopersPageProps {
  endpoints: MarketingEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
}

export function DevelopersPage({ endpoints, runtimeConfig }: DevelopersPageProps) {
  return (
    <Grid className="marketing-page-grid">
      <Panel title="Developer onboarding" subtitle="A public-facing API path without turning this shell into docs infrastructure yet.">
        <ul className="marketing-list">
          <li>Primary auth modes: API keys and OAuth client credentials.</li>
          <li>Customer-facing endpoints are versioned under <code>/{runtimeConfig.apiVersion}</code>.</li>
          <li>Public docs can later expand from this page into the separate frontend docs surface.</li>
        </ul>
      </Panel>

      <Panel title="Early integration anchors" subtitle="Backed by the current live API contract.">
        <ul className="marketing-list">
          <li>
            Search nonprofits: <code>{endpoints.nonprofitSearch}</code>
          </li>
          <li>
            Verify a nonprofit: <code>{endpoints.nonprofitVerify}</code>
          </li>
          <li>
            Fetch filing history: <code>{endpoints.filings}</code>
          </li>
          <li>
            Token exchange: <code>{endpoints.oauthToken}</code>
          </li>
        </ul>
      </Panel>
    </Grid>
  );
}
