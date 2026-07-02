import { Panel } from "@charity-status/shared-ui";
import type { readRuntimeConfig } from "@charity-status/shared-config";
import type { PortalNavigationAudience } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { PortalPageShell, StackedDetailSections } from "../components/shell";
import { DashboardPage } from "./DashboardPage";

export function PortalDashboardPage({
  audience,
  runtimeConfig,
  session,
}: {
  audience: PortalNavigationAudience;
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
  session: PortalAuthenticatedSession;
}) {
  if (audience === "customer_admin") {
    return (
      <DashboardPage
        pane="home"
        runtimeConfig={runtimeConfig}
        session={session}
      />
    );
  }

  return (
    <PortalPageShell
      description={`Choose a task for ${session.organization_name}. This page intentionally avoids unsupported operational metrics.`}
      eyebrow="Portal home"
      title="Dashboard"
    >
      <StackedDetailSections
        sectionWrapper={({ section }) => <section>{section}</section>}
      >
        <Panel
          title="Review organizations"
          subtitle="Search nonprofit records and open a shareable evidence profile."
        >
          <a className="portal-shell__action portal-shell__action--primary" href="#/organizations">
            Open organizations
          </a>
        </Panel>
        <Panel
          title="Manage automation"
          subtitle="Review integration access without mixing credentials into organization search."
        >
          <a className="portal-shell__action" href="#/automation">
            Open automation
          </a>
        </Panel>
      </StackedDetailSections>
    </PortalPageShell>
  );
}
