import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalSessionStub } from "../app/portalSession";

interface SettingsPageProps {
  endpoints: PortalEndpoints;
  session: PortalSessionStub;
}

export function SettingsPage({ endpoints, session }: SettingsPageProps) {
  return (
    <div className="portal-page-grid">
      <Panel title="Organization settings anchor" subtitle="Designed around the existing `GET/PUT /v1/organization/settings` contract.">
        <p>
          Future settings slices should load and persist against <code>{endpoints.organizationSettings}</code>{" "}
          while keeping billing and integrations as explicit subdomains inside the portal.
        </p>
        <ul className="portal-list">
          <li>`billing.allowOverage` stays available across plans.</li>
          <li>Integration toggles remain entitlement-gated by the backend.</li>
          <li>Workspace and account identifiers remain explicit in the shell.</li>
        </ul>
      </Panel>

      <Panel title="Current shell state" subtitle="Enough structure to extend without reworking the app boundary.">
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
            <dt>Plan</dt>
            <dd>{session.plan}</dd>
          </div>
        </dl>
      </Panel>
    </div>
  );
}
