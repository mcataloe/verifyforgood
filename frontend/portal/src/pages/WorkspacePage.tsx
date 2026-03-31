import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import {
  PortalActionToolbar,
  PortalPageShell,
  StackedDetailSections,
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
  endpoints: _endpoints,
  pane,
  session,
}: WorkspacePageProps) {
  const organization = usePortalOrganization();
  const workspaceLabel =
    pane === "team" ? "Team access" : "Nonprofit search";

  return (
    <PortalPageShell
      description={`Search, review, and manage nonprofit records for ${organization.activeOrganization.organization_name}.`}
      eyebrow={workspaceLabel}
      title="Nonprofit search"
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              {organization.currentMembership?.role ?? "unknown"} access
            </span>
            <span className="portal-shell__summary-pill">
              {organization.currentMembership?.status ?? "unknown"}
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <StackedDetailSections
        sectionWrapper={({ section }) => <section>{section}</section>}
      >
        <Panel
          title="Team overview"
          subtitle="A quick summary of your organization and access."
        >
          <dl className="portal-shell__details">
            <div>
              <dt>Organization</dt>
              <dd>{organization.activeOrganization.organization_name}</dd>
            </div>
            <div>
              <dt>Your role</dt>
              <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{organization.currentMembership?.status ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Plan</dt>
              <dd>{session.plan}</dd>
            </div>
          </dl>
        </Panel>

        <Panel
          title="Signed-in user"
          subtitle="The account currently using this workspace."
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
          </dl>
        </Panel>

        <NonprofitSearchPanel />

        <TeamManagementPanel />
      </StackedDetailSections>
    </PortalPageShell>
  );
}
