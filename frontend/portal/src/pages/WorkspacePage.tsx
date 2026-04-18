import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { PortalPageShell } from "../components/shell";
import { NonprofitSearchPanel } from "../nonprofits/NonprofitSearchPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function WorkspacePage({
  endpoints: _endpoints,
  session: _session,
}: WorkspacePageProps) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Search, review, and manage nonprofit records for ${organization.activeOrganization.organization_name}.`}
      title="Nonprofit Search"
    >
      <NonprofitSearchPanel />
    </PortalPageShell>
  );
}
