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
  resolveCustomerAdminPortalPane,
  resolveCustomerUserPortalPane,
  resolveActivePortalNavigationKey,
  resolvePortalProfileNavigationTarget,
  resolvePortalNavigationAudience,
  resolvePortalNavigation,
} from "../app/portalNavigation";
import { resolveMembershipRoleFromContext } from "../app/portalAuthorization";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalAuth } from "../auth/usePortalAuth";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { PortalOrganizationSwitcher } from "./PortalOrganizationSwitcher";

interface PortalLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  currentRoute: PortalRouteDefinition;
  onOpenOrganizationOnboarding: () => void;
  onSignOut: () => Promise<void>;
  routes: PortalRouteDefinition[];
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

export function PortalLayout({
  app,
  children,
  currentRoute,
  onOpenOrganizationOnboarding,
  onSignOut,
  routes,
  runtimeConfig: _runtimeConfig,
  session,
}: PortalLayoutProps) {
  const auth = usePortalAuth();
  const organization = usePortalOrganization();
  const audience = resolvePortalNavigationAudience(session.roles);
  const membershipRole = resolveMembershipRoleFromContext(
    organization.currentMembership ?? session.organization_membership,
  );
  const navigationSections = resolvePortalNavigation({
    membershipRole,
    organizationContextStatus: session.organization_context_status,
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
  const customerAdminPane =
    audience === "customer_admin"
      ? resolveCustomerAdminPortalPane({ currentHash, currentRoute })
      : null;
  const isProfileActive =
    audience === "customer_user"
      ? resolveCustomerUserPortalPane({ currentHash, currentRoute }) ===
        "profile"
      : audience === "customer_admin"
        ? customerAdminPane === "profile"
        : currentRoute.key === "settings";

  return (
    <VerifyForGoodAppShell
      activeNavigationKey={activeNavigationKey}
      appName={app.title}
      headerActions={
        <PortalOrganizationSwitcher
          activeOrganizationId={organization.activeOrganization.organization_id}
          activeOrganizationName={organization.activeOrganization.organization_name}
          availableOrganizations={auth.availableOrganizations}
          onCreateOrganization={onOpenOrganizationOnboarding}
          onSelectOrganization={(nextOrganization) => {
            auth.applyOrganization(nextOrganization);
          }}
        />
      }
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
          href={profileNavigationTarget?.href}
          primaryLabel={session.user.display_name}
        />
      }
      showHeader
      showSidebarHeader={false}
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
