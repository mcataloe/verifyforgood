import { useEffect } from "react";
import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { usePortalAuth } from "../auth/usePortalAuth";
import { PortalAuthLayout } from "../components/PortalAuthLayout";
import { PortalNotice } from "../components/feedback";
import { PortalLayout } from "../components/PortalLayout";
import { CustomerUserAutomationPage } from "../customer-user/CustomerUserAutomationPage";
import { CustomerUserProfilePage } from "../customer-user/CustomerUserProfilePage";
import { CustomerUserSearchPage } from "../customer-user/CustomerUserSearchPage";
import { PortalOrganizationProvider } from "../organization/PortalOrganizationProvider";
import { ApiAccessPage } from "../pages/ApiAccessPage";
import { BillingPage } from "../pages/BillingPage";
import { DashboardPage } from "../pages/DashboardPage";
import { PortalSignInPage } from "../pages/PortalSignInPage";
import { SettingsPage } from "../pages/SettingsPage";
import { WorkspacePage } from "../pages/WorkspacePage";
import {
  resolveCustomerUserPortalPane,
  resolvePortalNavigationAudience,
} from "./portalNavigation";
import { portalEndpoints } from "./portalEndpoints";
import {
  consumePortalReturnTo,
  navigateToPortalRoute,
  peekPortalReturnTo,
  portalProtectedRoutes,
  rememberPortalReturnTo,
  resolvePortalRoute,
  signInPortalRoute,
  usePortalRoute,
} from "./portalRoutes";

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
  const auth = usePortalAuth();
  const endpoints = portalEndpoints(runtimeConfig);
  const requestedRoute = resolvePortalRoute(peekPortalReturnTo());

  useEffect(() => {
    if (
      auth.status === "unauthenticated" &&
      currentRoute.access === "protected"
    ) {
      rememberPortalReturnTo(currentRoute.hash);
      navigateToPortalRoute(signInPortalRoute.hash);
    }
  }, [auth.status, currentRoute]);

  useEffect(() => {
    if (
      auth.status === "authenticated" &&
      currentRoute.key === signInPortalRoute.key
    ) {
      navigateToPortalRoute(consumePortalReturnTo());
    }
  }, [auth.status, currentRoute.key]);

  if (auth.status === "loading") {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Checking whether a portal session already exists before any protected route can render."
        title="Checking portal access"
      >
        <PortalNotice title="Loading" tone="loading">
          <p>Checking whether a portal session already exists.</p>
        </PortalNotice>
      </PortalAuthLayout>
    );
  }

  if (auth.status !== "authenticated") {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="This is the only public route inside the portal application shell."
        title="Sign in to the customer portal"
      >
        <PortalSignInPage
          endpoints={endpoints}
          isBusy={auth.isBusy}
          onSignIn={auth.signIn}
          requestedRoute={requestedRoute}
        />
      </PortalAuthLayout>
    );
  }

  if (currentRoute.key === signInPortalRoute.key) {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="An authenticated session exists, so the portal is returning to the requested protected route."
        title="Redirecting into the portal"
      >
        <p className="portal-auth-shell__message">
          Restoring access to {requestedRoute.label}.
        </p>
      </PortalAuthLayout>
    );
  }

  const session = auth.session;
  if (!session) {
    return null;
  }
  const audience = resolvePortalNavigationAudience(session.roles);
  const currentHash =
    typeof window === "undefined"
      ? currentRoute.hash
      : window.location.hash || currentRoute.hash;
  const customerUserPane =
    audience === "customer_user"
      ? resolveCustomerUserPortalPane({
          currentHash,
          currentRoute,
        })
      : null;

  return (
    <PortalOrganizationProvider runtimeConfig={runtimeConfig} session={session}>
      <PortalLayout
        app={appInfo}
        currentRoute={currentRoute}
        onSignOut={auth.signOut}
        routes={portalProtectedRoutes}
        runtimeConfig={runtimeConfig}
        session={session}
      >
        {currentRoute.key === "dashboard" ? (
          <DashboardPage runtimeConfig={runtimeConfig} session={session} />
        ) : null}
        {currentRoute.key === "workspace" ? (
          audience === "customer_user" && customerUserPane ? (
            <CustomerUserSearchPage
              pane={
                customerUserPane === "search-address"
                  ? "search-address"
                  : "search-ein"
              }
            />
          ) : (
            <WorkspacePage endpoints={endpoints} session={session} />
          )
        ) : null}
        {currentRoute.key === "api-access" ? (
          audience === "customer_user" && customerUserPane ? (
            <CustomerUserAutomationPage
              pane={
                customerUserPane === "automation-api"
                  ? "automation-api"
                  : customerUserPane === "automation-oauth"
                    ? "automation-oauth"
                    : "automation-general"
              }
              session={session}
            />
          ) : (
            <ApiAccessPage endpoints={endpoints} session={session} />
          )
        ) : null}
        {currentRoute.key === "usage-billing" ? (
          <BillingPage endpoints={endpoints} session={session} />
        ) : null}
        {currentRoute.key === "settings" ? (
          audience === "customer_user" && customerUserPane === "profile" ? (
            <CustomerUserProfilePage session={session} />
          ) : (
            <SettingsPage endpoints={endpoints} session={session} />
          )
        ) : null}
      </PortalLayout>
    </PortalOrganizationProvider>
  );
}
