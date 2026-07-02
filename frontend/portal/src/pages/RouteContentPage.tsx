import type { readRuntimeConfig } from "@charity-status/shared-config";
import { CustomerUserAutomationPage } from "../customer-user/CustomerUserAutomationPage";
import { CustomerUserProfilePage } from "../customer-user/CustomerUserProfilePage";
import type { PortalNavigationAudience } from "../app/portalNavigation";
import type { portalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { ApiAccessPage } from "./ApiAccessPage";
import { BillingPage } from "./BillingPage";
import { DashboardPage } from "./DashboardPage";
import { OrganizationDetailPage } from "./OrganizationDetailPage";
import { OrganizationsPage } from "./OrganizationsPage";
import { PortalNotFoundPage } from "./PortalNotFoundPage";
import { SettingsPage } from "./SettingsPage";
import { TeamPage } from "./TeamPage";

export function RouteContentPage({
  audience,
  currentRoute,
  endpoints,
  runtimeConfig,
  session,
}: {
  audience: PortalNavigationAudience;
  currentRoute: PortalRouteDefinition;
  endpoints: ReturnType<typeof portalEndpoints>;
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
  session: PortalAuthenticatedSession;
}) {
  switch (currentRoute.page) {
    case "dashboard":
      return (
        <DashboardPage
          pane={audience === "customer_admin" ? "home" : null}
          runtimeConfig={runtimeConfig}
          session={session}
        />
      );
    case "organizations":
      return <OrganizationsPage />;
    case "organization-detail":
      return currentRoute.params?.ein && currentRoute.section ? (
        <OrganizationDetailPage
          ein={currentRoute.params.ein}
          section={currentRoute.section}
        />
      ) : (
        <PortalNotFoundPage />
      );
    case "team":
      return <TeamPage session={session} />;
    case "automation-general":
    case "automation-api-key":
    case "automation-oauth":
      return audience === "customer_user" ? (
        <CustomerUserAutomationPage
          pane={
            currentRoute.page === "automation-api-key"
              ? "automation-api"
              : currentRoute.page === "automation-oauth"
                ? "automation-oauth"
                : "automation-general"
          }
          session={session}
        />
      ) : (
        <ApiAccessPage endpoints={endpoints} pane="api" session={session} />
      );
    case "billing":
      return <BillingPage endpoints={endpoints} pane="billing" session={session} />;
    case "usage":
      return <BillingPage endpoints={endpoints} pane="usage" session={session} />;
    case "settings-profile":
      return audience === "customer_user" ? (
        <CustomerUserProfilePage
          environment={runtimeConfig.environment}
          session={session}
        />
      ) : (
        <SettingsPage endpoints={endpoints} pane="settings" session={session} />
      );
    case "settings-organization":
      return <SettingsPage endpoints={endpoints} pane="settings" session={session} />;
    default:
      return <PortalNotFoundPage />;
  }
}
