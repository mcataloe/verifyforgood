import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";
import {
  PortalActionToolbar,
  PortalPageShell,
} from "../components/shell";
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
      description={
        focus === "usage"
          ? `Monitor request consumption, budget posture, and quota visibility for ${organization.activeOrganization.organization_name} without leaving the shared billing surface.`
          : `Review subscription state, compare plans, and manage provider billing tools for ${organization.activeOrganization.organization_name}.`
      }
      eyebrow={focus === "usage" ? "Customer admin usage" : "Customer admin billing"}
      title={focus === "usage" ? "Usage visibility" : "Billing management"}
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Org {organization.activeOrganization.organization_name}
            </span>
            <span className="portal-shell__summary-pill">
              Role {organization.currentMembership?.role ?? "unknown"}
            </span>
          </div>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Route #/usage-billing
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <UsageBillingPanel
        endpoints={endpoints}
        focus={focus}
        session={session}
      />
    </PortalPageShell>
  );
}
