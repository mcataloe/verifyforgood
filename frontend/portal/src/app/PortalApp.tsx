import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { PortalLayout } from "../components/PortalLayout";
import { ApiAccessPage } from "../pages/ApiAccessPage";
import { BillingPage } from "../pages/BillingPage";
import { DashboardPage } from "../pages/DashboardPage";
import { SettingsPage } from "../pages/SettingsPage";
import { WorkspacePage } from "../pages/WorkspacePage";
import { portalEndpoints } from "./portalEndpoints";
import { getPortalSessionStub } from "./portalSession";
import { portalRoutes, usePortalRoute } from "./portalRoutes";

const appInfo: FrontendAppInfo = {
  audience:
    "Authenticated customers managing verification workflows and account settings.",
  description:
    "Application shell for future authenticated product slices including workspace management, API access, usage, billing, and settings.",
  title: "Customer portal shell",
  surface: "portal",
};

export function PortalApp() {
  const runtimeConfig = readRuntimeConfig(import.meta.env);
  const currentRoute = usePortalRoute();
  const session = getPortalSessionStub();
  const endpoints = portalEndpoints(runtimeConfig);

  return (
    <PortalLayout
      app={appInfo}
      currentRoute={currentRoute}
      routes={portalRoutes}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      {currentRoute.key === "dashboard" ? (
        <DashboardPage
          endpoints={endpoints}
          runtimeConfig={runtimeConfig}
          session={session}
        />
      ) : null}
      {currentRoute.key === "workspace" ? (
        <WorkspacePage endpoints={endpoints} session={session} />
      ) : null}
      {currentRoute.key === "api-access" ? (
        <ApiAccessPage endpoints={endpoints} session={session} />
      ) : null}
      {currentRoute.key === "usage-billing" ? (
        <BillingPage endpoints={endpoints} session={session} />
      ) : null}
      {currentRoute.key === "settings" ? (
        <SettingsPage endpoints={endpoints} session={session} />
      ) : null}
    </PortalLayout>
  );
}
