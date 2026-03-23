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
  resolveActivePortalNavigationKey,
  resolvePortalNavigationAudience,
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
  const audience = resolvePortalNavigationAudience(session.roles);
  const accessLabel = getPortalAccessLabel(session.roles);
  const navigationSections = resolvePortalNavigation({
    plan: session.plan,
    roles: session.roles,
    routes,
  });
  const currentHash =
    typeof window === "undefined"
      ? currentRoute.hash
      : window.location.hash || currentRoute.hash;
  const activeNavigationKey = resolveActivePortalNavigationKey({
    currentHash,
    currentRoute,
    navigationSections,
  });

  return (
    <VerifyForGoodAppShell
      activeNavigationKey={activeNavigationKey}
      appName={app.title}
      headerActions={
        <div className="portal-shell__status-row">
          <span className="portal-shell__status-pill">
            Org: {organization.activeOrganization.organization_name}
          </span>
          <span className="portal-shell__status-pill">
            Env: {runtimeConfig.environment}
          </span>
          <span className="portal-shell__status-pill">
            Plan: {session.plan}
          </span>
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
      sidebarNavigationAriaLabel="Portal navigation"
      sidebarSummary={
        <div className="portal-shell__sidebar-summary">
          <div>
            <p className="portal-shell__summary-eyebrow">Portal navigation</p>
            <p className="portal-shell__summary-title">
              {organization.activeOrganization.organization_name}
            </p>
            <p className="portal-shell__summary-copy">
              {getPortalSidebarSummary(audience)}
            </p>
          </div>
          <div className="portal-shell__summary-meta">
            <span className="portal-shell__summary-pill">
              Access: {accessLabel}
            </span>
            <span className="portal-shell__summary-pill">
              Env: {runtimeConfig.environment}
            </span>
            <span className="portal-shell__summary-pill">
              Plan: {session.plan}
            </span>
          </div>
        </div>
      }
      sidebarFooter={
        <SidebarProfileSection
          accessLabel={accessLabel}
          eyebrow="Signed in"
          primaryLabel={session.user.display_name}
          secondaryLabel={
            organization.activeOrganization.organization_name
              ? `${organization.activeOrganization.organization_name}`
              : undefined
          }
          tertiaryLabel={
            organization.activeOrganization.account_id
              ? `Account ${organization.activeOrganization.account_id}`
              : undefined
          }
        />
      }
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}

function getPortalSidebarSummary(
  audience: ReturnType<typeof resolvePortalNavigationAudience>,
) {
  switch (audience) {
    case "developer":
      return "Nested platform navigation for tenant operations, rollout controls, and system access.";
    case "portal_admin":
      return "Customer, subscription, and support workflows organized to match the current portal surfaces.";
    case "customer_admin":
      return "Team, billing, API, and settings access mapped onto the existing authenticated workspace.";
    case "customer_user":
      return "Search, results, reports, and profile entry points aligned to the current customer experience.";
  }
}
