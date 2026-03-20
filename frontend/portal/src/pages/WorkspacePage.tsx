import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalSessionStub } from "../app/portalSession";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  session: PortalSessionStub;
}

export function WorkspacePage({ endpoints, session }: WorkspacePageProps) {
  return (
    <div className="portal-page-grid">
      <Panel title="Workspace context" subtitle="Ready for tenant, account, and membership-aware slices.">
        <p>
          The backend already models both <code>workspace_id</code> and <code>account_id</code>.
          The portal shell keeps those concepts visible without assuming the future user-role model.
        </p>
        <dl className="portal-shell__details">
          <div>
            <dt>Organization</dt>
            <dd>{session.organization_name}</dd>
          </div>
          <div>
            <dt>Workspace ID</dt>
            <dd>{session.workspace_id}</dd>
          </div>
          <div>
            <dt>Account ID</dt>
            <dd>{session.account_id}</dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Current backend anchor" subtitle="Settings are already keyed to workspace/account context.">
        <p>
          Future organization management slices should align to the existing settings contract at{" "}
          <code>{endpoints.organizationSettings}</code>.
        </p>
        <ul className="portal-list">
          <li>Integration toggles are workspace-aware.</li>
          <li>Billing overage preferences are account-wide.</li>
          <li>Defaults remain backward compatible when nothing has been persisted.</li>
        </ul>
      </Panel>
    </div>
  );
}
