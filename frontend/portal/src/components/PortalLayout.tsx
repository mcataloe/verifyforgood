import {
  Card,
  VerifyForGoodAppShell,
} from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import { resolvePortalNavigation } from "../app/portalNavigation";
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
        <Card
          description="Workspace and account context remain explicit while deeper organization review screens are still placeholder-backed."
          title="Active organization context"
        >
          <dl className="portal-shell__details">
            <div>
              <dt>Organization</dt>
              <dd>{organization.activeOrganization.organization_name}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{organization.activeOrganization.workspace_id}</dd>
            </div>
            <div>
              <dt>Account</dt>
              <dd>{organization.activeOrganization.account_id}</dd>
            </div>
            <div>
              <dt>Scope source</dt>
              <dd>{organization.activeOrganization.scope_source}</dd>
            </div>
            <div>
              <dt>Roles</dt>
              <dd>{session.roles.join(", ")}</dd>
            </div>
          </dl>
        </Card>
      }
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
