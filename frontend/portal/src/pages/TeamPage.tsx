import { Panel } from "@charity-status/shared-ui";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  DetailPageLayout,
  PortalActionToolbar,
  PortalPageShell,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface TeamPageProps {
  session: PortalAuthenticatedSession;
}

export function TeamPage({ session }: TeamPageProps) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Manage team access and review organization details for ${organization.activeOrganization.organization_name}.`}
      eyebrow="Team"
      title="Team access"
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
      <DetailPageLayout>
        <SectionBlock>
          <Panel
            title="Organization details"
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
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Signed-in account"
            subtitle="The account currently using this organization."
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
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <TeamManagementPanel />
        </SectionBlock>
      </DetailPageLayout>
    </PortalPageShell>
  );
}
