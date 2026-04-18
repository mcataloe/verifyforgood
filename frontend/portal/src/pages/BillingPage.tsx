import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";
import { PortalPageShell } from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface BillingPageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function BillingPage({
  endpoints,
  session,
}: BillingPageProps) {
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description={`Review billing, plan details, and included features for ${organization.activeOrganization.organization_name}.`}
      title="Billing"
    >
      <UsageBillingPanel
        endpoints={endpoints}
        focus="billing"
        managementMode="visibility"
        session={session}
      />
    </PortalPageShell>
  );
}
