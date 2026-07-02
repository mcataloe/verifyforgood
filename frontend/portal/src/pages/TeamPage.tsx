import { Panel } from "@charity-status/shared-ui";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { PortalPageShell, StackedDetailSections } from "../components/shell";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

export function TeamPage({ session }: { session: PortalAuthenticatedSession }) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Manage membership and workspace access for ${organization.activeOrganization.organization_name}.`}
      eyebrow="Workspace administration"
      title="Team"
    >
      <StackedDetailSections
        sectionWrapper={({ section }) => <section>{section}</section>}
      >
        <Panel
          title="Workspace context"
          subtitle="Membership changes apply to the active organization only."
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
              <dt>Signed-in operator</dt>
              <dd>{session.user.display_name}</dd>
            </div>
            <div>
              <dt>Membership role</dt>
              <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
            </div>
          </dl>
        </Panel>
        <TeamManagementPanel />
      </StackedDetailSections>
    </PortalPageShell>
  );
}
