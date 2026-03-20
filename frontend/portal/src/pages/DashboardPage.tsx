import { Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalSessionStub } from "../app/portalSession";

interface DashboardPageProps {
  endpoints: PortalEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalSessionStub;
}

export function DashboardPage({
  endpoints,
  runtimeConfig,
  session,
}: DashboardPageProps) {
  return (
    <div className="portal-page-grid">
      <Panel title="Portal readiness" subtitle="This shell is organized for future vertical slices.">
        <ul className="portal-list">
          <li>Workspace/account context is separated from page rendering.</li>
          <li>Navigation reflects the backend’s current customer-facing surface.</li>
          <li>Shared API/config packages already normalize early portal dependencies.</li>
        </ul>
      </Panel>

      <Panel title="Current workspace" subtitle="Stubbed until real auth/session wiring lands.">
        <dl className="portal-shell__details">
          <div>
            <dt>Workspace</dt>
            <dd>{session.workspace_id}</dd>
          </div>
          <div>
            <dt>Account</dt>
            <dd>{session.account_id}</dd>
          </div>
          <div>
            <dt>Billing status</dt>
            <dd>{session.billing_status}</dd>
          </div>
          <div>
            <dt>API environment</dt>
            <dd>{runtimeConfig.environment}</dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Early portal anchors" subtitle="Actual endpoints already exist in the backend.">
        <ul className="portal-list">
          <li>
            Organization settings: <code>{endpoints.organizationSettings}</code>
          </li>
          <li>
            Billing summary: <code>{endpoints.billingSubscription}</code>
          </li>
          <li>
            OAuth token exchange: <code>{endpoints.oauthToken}</code>
          </li>
        </ul>
      </Panel>
    </div>
  );
}
