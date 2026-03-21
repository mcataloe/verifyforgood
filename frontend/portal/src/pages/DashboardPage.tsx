import { Grid, Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { NonprofitSearchPanel } from "../nonprofits/NonprofitSearchPanel";

interface DashboardPageProps {
  endpoints: PortalEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

export function DashboardPage({
  endpoints,
  runtimeConfig,
  session,
}: DashboardPageProps) {
  return (
    <>
      <NonprofitSearchPanel />

      <Grid className="portal-page-grid">
        <Panel
          title="Current workspace"
          subtitle="Portal search runs inside the active organization scope."
        >
          <dl className="portal-shell__details">
            <div>
              <dt>User</dt>
              <dd>{session.user.email}</dd>
            </div>
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

        <Panel
          title="Search anchors"
          subtitle="The dashboard now uses the real nonprofit backend surface."
        >
          <ul className="portal-list">
            <li>
              EIN lookup: <code>{endpoints.nonprofitLookup}</code>
            </li>
            <li>
              Name search: <code>{endpoints.nonprofitSearch}</code>
            </li>
            <li>
              Filing history: <code>{endpoints.nonprofitFilings}</code>
            </li>
            <li>
              Session roles: <code>{session.roles.join(", ")}</code>
            </li>
          </ul>
        </Panel>
      </Grid>
    </>
  );
}
