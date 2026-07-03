import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";
import { PortalPageShell } from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface BillingPageProps {
  endpoints: PortalEndpoints;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
}

export function BillingPage({
  endpoints,
  pane,
  session,
}: BillingPageProps) {
  const organization = usePortalOrganization();
  const focus = pane === "usage" ? "usage" : "billing";

  return (
    <PortalPageShell
      description={`Review billing, plan details, and included features for ${organization.activeOrganization.organization_name}.`}
      title={focus === "usage" ? "Usage" : "Billing"}
    >
      <UsageBillingPanel
        endpoints={endpoints}
        focus={focus}
        managementMode="visibility"
        session={session}
      />
    </PortalPageShell>
  );
}
