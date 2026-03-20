import { Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { DocsEndpoints } from "../app/docsEndpoints";

interface ApiUsagePageProps {
  endpoints: DocsEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
}

export function ApiUsagePage({ endpoints, runtimeConfig }: ApiUsagePageProps) {
  return (
    <div className="docs-page-grid">
      <Panel title="API onboarding" subtitle="A docs-first view of the existing contract.">
        <ul className="docs-list">
          <li>All current customer routes are versioned under `/{runtimeConfig.apiVersion}`.</li>
          <li>Customer access is modeled through API keys and OAuth client credentials.</li>
          <li>Standard responses use a consistent envelope with `data`, `meta`, and `errors`.</li>
        </ul>
      </Panel>

      <Panel title="Reference endpoints" subtitle="Useful anchors for future guides and examples.">
        <ul className="docs-list">
          <li>
            Token exchange: <code>{endpoints.oauthToken}</code>
          </li>
          <li>
            Organization settings: <code>{endpoints.organizationSettings}</code>
          </li>
          <li>
            Billing summary: <code>{endpoints.billingSubscription}</code>
          </li>
        </ul>
      </Panel>
    </div>
  );
}
