import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalActionToolbar,
  PortalPageShell,
} from "../components/shell";
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
      eyebrow="Nonprofit search"
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
      <NonprofitSearchPanel />
    </PortalPageShell>
  );
}
