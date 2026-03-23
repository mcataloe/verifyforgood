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
  resolveCustomerUserPortalPane,
  resolveActivePortalNavigationKey,
  resolvePortalProfileNavigationTarget,
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
  const profileNavigationTarget = resolvePortalProfileNavigationTarget({
    audience,
    routes,
  });
  const isProfileActive =
    audience === "customer_user"
      ? resolveCustomerUserPortalPane({ currentHash, currentRoute }) ===
        "profile"
      : currentRoute.key === "settings";

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
      sidebarFooter={
        <SidebarProfileSection
          active={isProfileActive}
          accessLabel={accessLabel}
          ariaLabel={
            profileNavigationTarget
              ? `${profileNavigationTarget.label} for ${session.user.display_name}`
              : undefined
          }
          eyebrow="Signed in"
          href={profileNavigationTarget?.href}
          primaryLabel={session.user.display_name}
        />
      }
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
