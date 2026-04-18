import {
  DetailPageLayout,
  PortalPageShell,
  SectionBlock,
} from "../components/shell";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface TeamPageProps {
  session: unknown;
}

export function TeamPage({ session: _session }: TeamPageProps) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Manage team access for ${organization.activeOrganization.organization_name}.`}
      title="Team Access"
    >
      <DetailPageLayout>
        <SectionBlock>
          <TeamManagementPanel />
        </SectionBlock>
      </DetailPageLayout>
    </PortalPageShell>
  );
}
