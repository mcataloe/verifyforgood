import {
  buildOrganizationPortalHash,
  navigateToPortalRoute,
} from "../app/portalRoutes";
import { PortalPageShell } from "../components/shell";
import { NonprofitSearchPanel } from "../nonprofits/NonprofitSearchPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

export function OrganizationsPage() {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Search source-backed nonprofit records for ${organization.activeOrganization.organization_name}. Each result opens on a stable route that can be bookmarked or shared with another authorized user.`}
      eyebrow="Organization review"
      title="Organizations"
    >
      <NonprofitSearchPanel
        onOpenDetail={(ein) => {
          navigateToPortalRoute(buildOrganizationPortalHash(ein));
        }}
      />
    </PortalPageShell>
  );
}
