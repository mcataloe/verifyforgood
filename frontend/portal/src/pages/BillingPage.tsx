import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";

interface BillingPageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function BillingPage({ endpoints, session }: BillingPageProps) {
  return <UsageBillingPanel endpoints={endpoints} session={session} />;
}
