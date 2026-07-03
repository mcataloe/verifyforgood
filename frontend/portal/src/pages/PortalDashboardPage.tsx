import { Panel } from "@charity-status/shared-ui";
import type { readRuntimeConfig } from "@charity-status/shared-config";
import type { PortalNavigationAudience } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { PortalPageShell, StackedDetailSections } from "../components/shell";

export function PortalDashboardPage({
  audience: _audience,
  runtimeConfig: _runtimeConfig,
  session,
}: {
  audience: PortalNavigationAudience;
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
  session: PortalAuthenticatedSession;
}) {
  return (
    <PortalPageShell
      description={`Choose where to continue for ${session.organization_name}. Recent nonprofit searches are kept on the Organizations page.`}
      eyebrow="Portal home"
      title="Home"
    >
      <StackedDetailSections
        sectionWrapper={({ section }) => <section>{section}</section>}
      >
        <Panel
          title="Organizations"
          subtitle="Search nonprofit records and review recent searches."
        >
          <a
            className="portal-shell__action portal-shell__action--primary"
            href="#/organizations"
          >
            Open organizations
          </a>
        </Panel>
        <Panel
          title="Team"
          subtitle="Review organization membership and team information."
        >
          <a className="portal-shell__action" href="#/team">
            Open team
          </a>
        </Panel>
        <Panel
          title="Settings"
          subtitle="Review organization settings and preferences."
        >
          <a className="portal-shell__action" href="#/settings/organization">
            Open settings
          </a>
        </Panel>
      </StackedDetailSections>
    </PortalPageShell>
  );
}
