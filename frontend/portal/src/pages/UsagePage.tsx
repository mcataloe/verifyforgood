import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";
import { PortalPageShell } from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface UsagePageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function UsagePage({ endpoints, session }: UsagePageProps) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Track request usage, limits, and budget settings for ${organization.activeOrganization.organization_name}.`}
      title="Usage"
    >
      <UsageBillingPanel
        endpoints={endpoints}
        focus="usage"
        managementMode="visibility"
        session={session}
      />
    </PortalPageShell>
  );
}
