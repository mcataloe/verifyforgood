import { VerifyForGoodAppShell } from "@charity-status/shared-ui";
import { Group } from "@mantine/core";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import {
  resolveActivePortalNavigationKey,
  resolvePortalProfileNavigationTarget,
  resolvePortalNavigationAudience,
  resolvePortalNavigation,
} from "../app/portalNavigation";
import { resolveMembershipRoleFromContext } from "../app/portalAuthorization";
import { billingPortalRoute } from "../app/portalRouteCatalog";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalAuth } from "../auth/usePortalAuth";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { PortalOrganizationSwitcher } from "./PortalOrganizationSwitcher";
import { PortalUserMenu } from "./PortalUserMenu";
import { portalHelpMenuItems } from "./portalHelpMenuItems";

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

  return (
    <VerifyForGoodAppShell
      activeNavigationKey={activeNavigationKey}
      appName={app.title}
      headerActions={
        <Group gap="sm" wrap="nowrap">
          <PortalOrganizationSwitcher
            activeOrganizationId={organization.activeOrganization.organization_id}
            activeOrganizationName={organization.activeOrganization.organization_name}
            availableOrganizations={auth.availableOrganizations}
            onCreateOrganization={onOpenOrganizationOnboarding}
            onSelectOrganization={(nextOrganization) => {
              auth.applyOrganization(nextOrganization);
            }}
          />
          <PortalUserMenu
            editProfileHref={profileNavigationTarget?.href}
            email={session.user.email}
            onSignOut={() => {
              void onSignOut();
            }}
            primaryLabel={session.user.display_name}
          />
        </Group>
      }
      navigationSections={navigationSections}
      sidebarHelpItems={portalHelpMenuItems}
      sidebarNavigationAriaLabel="Portal navigation"
      sidebarUpgradeHref={billingPortalRoute.hash}
      showHeader
      showSidebarHeader={false}
      subtitle={app.description}
    >
      {children}
    </VerifyForGoodAppShell>
  );
}
