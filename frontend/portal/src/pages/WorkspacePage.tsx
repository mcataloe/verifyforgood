import { Grid, PageHeader, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { NonprofitSearchPanel } from "../nonprofits/NonprofitSearchPanel";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function WorkspacePage({ endpoints, session }: WorkspacePageProps) {
  const organization = usePortalOrganization();

  return (
    <div className="portal-dashboard">
      <PageHeader
        eyebrow="Tenant-aware workspace"
        title="Nonprofit search workspace"
        description={`Search, review, and inspect nonprofit records for ${organization.activeOrganization.organization_name}. Requests use the current portal session plus organization scope automatically.`}
      />

      <Grid className="portal-page-grid">
        <NonprofitSearchPanel />

        <Panel
          title="Workspace context"
          subtitle="The nonprofit search flow runs through the shared organization-aware API client."
        >
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
              <dt>Membership role</dt>
              <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Membership status</dt>
              <dd>{organization.currentMembership?.status ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Settings endpoint</dt>
              <dd>
                <code>{endpoints.organizationSettings}</code>
              </dd>
            </div>
          </dl>
        </Panel>

        <Panel
          title="Signed-in operator"
          subtitle="Session identity stays separate from the current organization boundary."
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
              <dt>Plan</dt>
              <dd>{session.plan}</dd>
            </div>
            <div>
              <dt>Scope source</dt>
              <dd>{organization.activeOrganization.scope_source}</dd>
            </div>
          </dl>
        </Panel>

        <TeamManagementPanel />
      </Grid>
    </div>
  );
}
