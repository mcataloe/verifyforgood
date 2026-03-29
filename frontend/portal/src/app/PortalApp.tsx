import { useEffect, useMemo } from "react";
import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { usePortalAuth } from "../auth/usePortalAuth";
import { PortalAuthProvider } from "../auth/PortalAuthProvider";
import { PortalAuthLayout } from "../components/PortalAuthLayout";
import { PortalNotice } from "../components/feedback";
import { PortalLayout } from "../components/PortalLayout";
import { CustomerUserAutomationPage } from "../customer-user/CustomerUserAutomationPage";
import { CustomerUserProfilePage } from "../customer-user/CustomerUserProfilePage";
import { PortalOrganizationProvider } from "../organization/PortalOrganizationProvider";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalActiveOrganizationRecord,
  createPortalOrganizationClient,
} from "../organization/portalOrganization";
import { ApiAccessPage } from "../pages/ApiAccessPage";
import { BillingPage } from "../pages/BillingPage";
import { DashboardPage } from "../pages/DashboardPage";
import { PortalOrganizationOnboardingPage } from "../pages/PortalOrganizationOnboardingPage";
import { PortalRegisterPage } from "../pages/PortalRegisterPage";
import { PortalSignInPage } from "../pages/PortalSignInPage";
import { SettingsPage } from "../pages/SettingsPage";
import { WorkspacePage } from "../pages/WorkspacePage";
import {
  resolveMembershipRoleFromContext,
  resolveRouteAuthorization,
} from "./portalAuthorization";
import {
  resolveCustomerAdminPortalPane,
  resolveCustomerUserPortalPane,
  resolvePortalNavigationAudience,
} from "./portalNavigation";
import { portalEndpoints } from "./portalEndpoints";
import {
  consumePortalReturnTo,
  navigateToPortalRoute,
  organizationOnboardingPortalRoute,
  peekPortalReturnTo,
  portalProtectedRoutes,
  registerPortalRoute,
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
  return (
    <PortalAuthProvider runtimeConfig={runtimeConfig}>
      <PortalAppShell runtimeConfig={runtimeConfig} />
    </PortalAuthProvider>
  );
}

function PortalAppShell({
  runtimeConfig,
}: {
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
}) {
  const currentRoute = usePortalRoute();
  const auth = usePortalAuth();
  const endpoints = portalEndpoints(runtimeConfig);
  const requestedRoute = resolvePortalRoute(peekPortalReturnTo());
  const hasPendingOrganization =
    auth.session?.organization_context_status === "pending";
  const organizationClient = useMemo(
    () =>
      auth.accessToken
        ? createPortalOrganizationClient({
            accessToken: auth.accessToken,
            runtimeConfig,
          })
        : null,
    [auth.accessToken, runtimeConfig],
  );

  useEffect(() => {
    if (
      auth.status === "unauthenticated" &&
      currentRoute.access === "protected"
    ) {
      rememberPortalReturnTo(window.location.hash || currentRoute.hash);
      navigateToPortalRoute(signInPortalRoute.hash);
    }
  }, [auth.status, currentRoute]);

  useEffect(() => {
    if (
      auth.status === "authenticated" &&
      (currentRoute.key === signInPortalRoute.key ||
        currentRoute.key === registerPortalRoute.key)
    ) {
      navigateToPortalRoute(consumePortalReturnTo());
    }
  }, [auth.status, currentRoute.key]);

  useEffect(() => {
    if (
      auth.status === "authenticated" &&
      hasPendingOrganization &&
      currentRoute.key !== organizationOnboardingPortalRoute.key
    ) {
      navigateToPortalRoute(organizationOnboardingPortalRoute.hash);
    }
  }, [auth.status, currentRoute.key, hasPendingOrganization]);

  useEffect(() => {
    if (
      auth.status === "authenticated" &&
      !hasPendingOrganization &&
      currentRoute.key === organizationOnboardingPortalRoute.key
    ) {
      navigateToPortalRoute("#/dashboard");
    }
  }, [auth.status, currentRoute.key, hasPendingOrganization]);

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
        subtitle="These are the public auth routes inside the portal application shell."
        title={
          currentRoute.key === registerPortalRoute.key
            ? "Create your customer portal account"
            : "Sign in to the customer portal"
        }
      >
        {currentRoute.key === registerPortalRoute.key ? (
          <PortalRegisterPage
            endpoints={endpoints}
            isBusy={auth.isBusy}
            onRegister={auth.register}
            requestedRoute={requestedRoute}
          />
        ) : (
          <PortalSignInPage
            endpoints={endpoints}
            isBusy={auth.isBusy}
            onLogin={auth.login}
            requestedRoute={requestedRoute}
          />
        )}
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
  if (hasPendingOrganization) {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Create the first organization context before the rest of the portal opens."
        title="Create your first organization"
      >
        <PortalOrganizationOnboardingPage
          endpoints={endpoints}
          isBusy={auth.isBusy}
          onCreateOrganization={async (request) => {
            if (!organizationClient) {
              throw new Error("Authentication is required");
            }

            const created = await organizationClient.createOrganization(request);
            auth.applyOrganization(
              createPortalActiveOrganizationRecord(created),
            );
            navigateToPortalRoute("#/dashboard");
          }}
        />
      </PortalAuthLayout>
    );
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
  const customerAdminPane =
    audience === "customer_admin"
      ? resolveCustomerAdminPortalPane({
          currentHash,
          currentRoute,
        })
      : null;

  return (
    <PortalOrganizationProvider
      accessToken={auth.accessToken}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      <PortalAuthorizedShell
        appInfo={appInfo}
        customerAdminPane={customerAdminPane}
        currentRoute={currentRoute}
        customerUserPane={customerUserPane}
        endpoints={endpoints}
        runtimeConfig={runtimeConfig}
        session={session}
        onSignOut={auth.signOut}
      />
    </PortalOrganizationProvider>
  );
}

function PortalAuthorizedShell({
  appInfo,
  customerAdminPane,
  currentRoute,
  customerUserPane,
  endpoints,
  onSignOut,
  runtimeConfig,
  session,
}: {
  appInfo: FrontendAppInfo;
  customerAdminPane: ReturnType<typeof resolveCustomerAdminPortalPane> | null;
  currentRoute: ReturnType<typeof usePortalRoute>;
  customerUserPane: ReturnType<typeof resolveCustomerUserPortalPane> | null;
  endpoints: ReturnType<typeof portalEndpoints>;
  onSignOut: () => Promise<void>;
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
  session: NonNullable<ReturnType<typeof usePortalAuth>["session"]>;
}) {
  const organization = usePortalOrganization();
  const audience = resolvePortalNavigationAudience(session.roles);
  const currentHash =
    typeof window === "undefined"
      ? currentRoute.hash
      : window.location.hash || currentRoute.hash;
  const membershipRole = resolveMembershipRoleFromContext(
    organization.currentMembership ?? session.organization_membership,
  );
  const routeAuthorization = resolveRouteAuthorization({
    audience,
    currentHash,
    currentRoute,
    membershipRole,
  });

  useEffect(() => {
    if (
      currentRoute.access === "protected" &&
      !routeAuthorization.allowed &&
      routeAuthorization.redirectHash &&
      currentHash !== routeAuthorization.redirectHash
    ) {
      navigateToPortalRoute(routeAuthorization.redirectHash);
    }
  }, [
    currentHash,
    currentRoute.access,
    routeAuthorization.allowed,
    routeAuthorization.redirectHash,
  ]);

  if (!routeAuthorization.allowed) {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Checking whether the current organization role allows this route."
        title="Redirecting to an allowed area"
      >
        <PortalNotice title="Redirecting" tone="loading">
          <p>Returning to the nearest allowed portal destination.</p>
        </PortalNotice>
      </PortalAuthLayout>
    );
  }

  return (
    <PortalLayout
      app={appInfo}
      currentRoute={currentRoute}
      onSignOut={onSignOut}
      routes={portalProtectedRoutes.filter(
        (route) => route.key !== organizationOnboardingPortalRoute.key,
      )}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      {currentRoute.key === "dashboard" ? (
        <DashboardPage runtimeConfig={runtimeConfig} session={session} />
      ) : null}
      {currentRoute.key === "workspace" ? (
        <WorkspacePage
          endpoints={endpoints}
          pane={customerAdminPane}
          session={session}
        />
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
          <ApiAccessPage
            endpoints={endpoints}
            pane={customerAdminPane}
            session={session}
          />
        )
      ) : null}
      {currentRoute.key === "usage-billing" ? (
        <BillingPage
          endpoints={endpoints}
          pane={customerAdminPane}
          session={session}
        />
      ) : null}
      {currentRoute.key === "settings" ? (
        audience === "customer_user" && customerUserPane === "profile" ? (
          <CustomerUserProfilePage
            environment={runtimeConfig.environment}
            session={session}
          />
        ) : (
          <SettingsPage
            endpoints={endpoints}
            pane={customerAdminPane}
            session={session}
          />
        )
      ) : null}
    </PortalLayout>
  );
}
