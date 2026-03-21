import { Grid, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function WorkspacePage({ endpoints, session }: WorkspacePageProps) {
  const organization = usePortalOrganization();

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Workspace context"
        subtitle="Ready for tenant, account, and membership-aware slices."
      >
        <p>
          The portal now carries an active organization context that future
          slices can access through a shared provider instead of re-deriving
          tenant scope from page-local props.
        </p>
        <dl className="portal-shell__details">
          <div>
            <dt>Organization</dt>
            <dd>{organization.activeOrganization.organization_name}</dd>
          </div>
          <div>
            <dt>Workspace ID</dt>
            <dd>{organization.activeOrganization.workspace_id}</dd>
          </div>
          <div>
            <dt>Account ID</dt>
            <dd>{organization.activeOrganization.account_id}</dd>
          </div>
          <div>
            <dt>Settings source</dt>
            <dd>{organization.activeOrganization.settings_source}</dd>
          </div>
        </dl>
      </Panel>

      <Panel
        title="Current backend anchor"
        subtitle="Settings are already keyed to workspace/account context."
      >
        <p>
          Future organization management slices should align to the existing
          settings contract at <code>{endpoints.organizationSettings}</code>.
        </p>
        <ul className="portal-list">
          <li>
            Active scope status: <strong>{organization.status}</strong>.
          </li>
          <li>
            Billing overage allowed:{" "}
            <strong>
              {organization.activeOrganization.billing_allow_overage === null
                ? "not loaded"
                : String(organization.activeOrganization.billing_allow_overage)}
            </strong>
            .
          </li>
          <li>Integration toggles are workspace-aware.</li>
          <li>Billing overage preferences are account-wide.</li>
          <li>
            Defaults remain backward compatible when nothing has been persisted.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Signed-in operator"
        subtitle="Session identity stays separate from the active organization boundary."
      >
        <dl className="portal-shell__details">
          <div>
            <dt>User</dt>
            <dd>{session.user.display_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{session.user.email}</dd>
          </div>
          <div>
            <dt>Scope source</dt>
            <dd>{organization.activeOrganization.scope_source}</dd>
          </div>
        </dl>
      </Panel>
    </Grid>
  );
}
