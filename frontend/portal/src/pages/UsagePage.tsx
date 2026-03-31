import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { UsageBillingPanel } from "../billing/UsageBillingPanel";
import {
  PortalActionToolbar,
  PortalPageShell,
} from "../components/shell";
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
      eyebrow="Usage"
      title="Usage"
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
        </PortalActionToolbar>
      }
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
