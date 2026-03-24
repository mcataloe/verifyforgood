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
  resolveCustomerUserPortalPane,
  resolveActivePortalNavigationKey,
  resolvePortalProfileNavigationTarget,
  resolvePortalNavigationAudience,
  resolvePortalNavigation,
} from "../app/portalNavigation";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";

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
  runtimeConfig: _runtimeConfig,
  session,
}: PortalLayoutProps) {
  const audience = resolvePortalNavigationAudience(session.roles);
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
      navigationSections={navigationSections}
      sidebarNavigationAriaLabel="Portal navigation"
      sidebarFooter={
        <SidebarProfileSection
          active={isProfileActive}
          actionAriaLabel="Log out of the portal"
          actionLabel="Log out"
          actionOnClick={() => {
            void onSignOut();
          }}
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
      showHeader={false}
      showSidebarHeader={false}
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
