import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import {
  DetailPageLayout,
  PortalActionToolbar,
  PortalPageShell,
  SectionBlock,
} from "../components/shell";
import { NonprofitSearchPanel } from "../nonprofits/NonprofitSearchPanel";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
}

export function WorkspacePage({
  endpoints,
  pane,
  session,
}: WorkspacePageProps) {
  const organization = usePortalOrganization();
  const workspaceLabel =
    pane === "team" ? "Customer admin team" : "Tenant-aware workspace";

  return (
    <PortalPageShell
      description={`Search, review, and inspect nonprofit records for ${organization.activeOrganization.organization_name}. Requests use the current portal session plus organization scope automatically.`}
      eyebrow={workspaceLabel}
      title="Nonprofit search workspace"
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Team role {organization.currentMembership?.role ?? "unknown"}
            </span>
            <span className="portal-shell__summary-pill">
              Status {organization.currentMembership?.status ?? "unknown"}
            </span>
          </div>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Workspace {organization.activeOrganization.workspace_id}
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <DetailPageLayout sectionWrapper={({ section }) => <SectionBlock>{section}</SectionBlock>}>
        <Panel
          title="Team operations"
          subtitle="Search, review, and inspect nonprofit records without leaving the shared team workspace."
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

        <NonprofitSearchPanel />

        <TeamManagementPanel />
      </DetailPageLayout>
    </PortalPageShell>
  );
}
