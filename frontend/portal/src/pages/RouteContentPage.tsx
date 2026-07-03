import type { readRuntimeConfig } from "@charity-status/shared-config";
import { CustomerUserAutomationPage } from "../customer-user/CustomerUserAutomationPage";
import { CustomerUserProfilePage } from "../customer-user/CustomerUserProfilePage";
import type { PortalNavigationAudience } from "../app/portalNavigation";
import type { portalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { ApiAccessPage } from "./ApiAccessPage";
import { BillingPage } from "./BillingPage";
import { ComparePlansPage } from "./ComparePlansPage";
import { OrganizationDetailPage } from "./OrganizationDetailPage";
import { NonprofitSearchPage } from "./NonprofitSearchPage";
import { PortalDashboardPage } from "./PortalDashboardPage";
import { PortalNotFoundPage } from "./PortalNotFoundPage";
import { PortalPlaceholderPage } from "./PortalPlaceholderPage";
import { SettingsPage } from "./SettingsPage";
import { SupportPage } from "./SupportPage";
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
        <PortalDashboardPage
          audience={audience}
          runtimeConfig={runtimeConfig}
          session={session}
        />
      );
    case "organizations":
      return <NonprofitSearchPage />;
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
    case "support-contact":
      return <SupportPage pane="support-contact" />;
    case "support-report-issue":
      return <SupportPage pane="support-report-issue" />;
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
        <ApiAccessPage pane="api" />
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
    case "compare-plans":
      return <ComparePlansPage />;
    case "help":
      return (
        <PortalPlaceholderPage
          description="Get help using the VerifyForGood portal."
          title="Help"
        />
      );
    case "help-documentation":
      return (
        <PortalPlaceholderPage
          description="Read product documentation."
          title="Documentation"
        />
      );
    default:
      return <PortalNotFoundPage />;
  }
}
