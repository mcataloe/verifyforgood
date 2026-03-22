import {
  SidebarProfileSection,
  VerifyForGoodAppShell,
} from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import {
  getPortalAccessLabel,
  resolvePortalNavigation,
} from "../app/portalNavigation";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface PortalLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  currentRoute: PortalRouteDefinition;
  onSignOut: () => Promise<void>;
  routes: PortalRouteDefinition[];
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

export function PortalLayout({
  app,
  children,
  currentRoute,
  onSignOut,
  routes,
  runtimeConfig,
  session,
}: PortalLayoutProps) {
  const organization = usePortalOrganization();
  const navigationSections = resolvePortalNavigation({
    plan: session.plan,
    roles: session.roles,
    routes,
  });

  return (
    <VerifyForGoodAppShell
      activeNavigationKey={currentRoute.key}
      appName={app.title}
      headerActions={
        <div className="portal-shell__status-row">
          <span className="portal-shell__status-pill">
            Org: {organization.activeOrganization.organization_name}
          </span>
          <span className="portal-shell__status-pill">
            Env: {runtimeConfig.environment}
          </span>
          <span className="portal-shell__status-pill">Plan: {session.plan}</span>
          <button
            className="portal-shell__action"
            onClick={() => void onSignOut()}
            type="button"
          >
            Sign out
          </button>
        </div>
      }
      navigationSections={navigationSections}
      sidebarFooter={
        <SidebarProfileSection
          accessLabel={getPortalAccessLabel(session.roles)}
          eyebrow="Customer context"
          primaryLabel={organization.activeOrganization.organization_name}
          secondaryLabel={
            organization.activeOrganization.account_id
              ? `Account ${organization.activeOrganization.account_id}`
              : undefined
          }
          tertiaryLabel={session.user.display_name}
        />
      }
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
