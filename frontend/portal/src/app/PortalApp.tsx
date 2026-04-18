import { useEffect, useMemo, useState } from "react";
import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { usePortalAuth } from "../auth/usePortalAuth";
import { PortalAuthProvider } from "../auth/PortalAuthProvider";
import { PortalAuthLayout } from "../components/PortalAuthLayout";
import { PortalNotice } from "../components/feedback";
import { PortalLayout } from "../components/PortalLayout";
import { CustomerUserAutomationPage } from "../customer-user/CustomerUserAutomationPage";
import { CustomerUserProfilePage } from "../customer-user/CustomerUserProfilePage";
import { CustomerUserSearchPage } from "../customer-user/CustomerUserSearchPage";
import { PortalOrganizationProvider } from "../organization/PortalOrganizationProvider";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalActiveOrganizationRecord,
  createPortalOrganizationClient,
  type PortalOrganizationCreateRequest,
} from "../organization/portalOrganization";
import { ApiAccessPage } from "../pages/ApiAccessPage";
import { BillingPage } from "../pages/BillingPage";
import { DashboardPage } from "../pages/DashboardPage";
import { PortalOrganizationOnboardingPage } from "../pages/PortalOrganizationOnboardingPage";
import { PortalHomePage } from "../pages/PortalHomePage";
import { PortalRegisterPage } from "../pages/PortalRegisterPage";
import { PortalSignInPage } from "../pages/PortalSignInPage";
import { SettingsPage } from "../pages/SettingsPage";
import { TeamPage } from "../pages/TeamPage";
import { UsagePage } from "../pages/UsagePage";
import { WorkspacePage } from "../pages/WorkspacePage";
import {
  resolveMembershipRoleFromContext,
  resolveRouteAuthorization,
} from "./portalAuthorization";
import {
  resolveCustomerAdminPortalPane,
  resolveCanonicalCustomerAdminHash,
  resolveCustomerUserPortalPane,
  resolvePortalNavigationAudience,
} from "./portalNavigation";
import { portalEndpoints } from "./portalEndpoints";
import {
  consumePortalReturnTo,
  navigateToPortalRoute,
  homePortalRoute,
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
    "Manage verification activity, billing, API access, and organization settings.",
  title: "Customer portal",
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
  const authAudience = auth.session
    ? resolvePortalNavigationAudience(auth.session.roles)
    : null;
  const authMembershipRole = auth.session
    ? resolveMembershipRoleFromContext(auth.session.organization_membership)
    : null;
  const [isOrganizationOnboardingOpen, setIsOrganizationOnboardingOpen] =
    useState(false);
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
      (currentRoute.key === homePortalRoute.key ||
        currentRoute.key === signInPortalRoute.key ||
        currentRoute.key === registerPortalRoute.key)
    ) {
      navigateToPortalRoute(
        hasPendingOrganization
          ? "#/dashboard"
          : consumePortalReturnTo(),
      );
    }
  }, [auth.status, currentRoute.key, hasPendingOrganization]);

  useEffect(() => {
    if (
      auth.status === "authenticated" &&
      hasPendingOrganization &&
      currentRoute.key !== "dashboard"
    ) {
      navigateToPortalRoute("#/dashboard");
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

  useEffect(() => {
    if (auth.status !== "authenticated" || hasPendingOrganization) {
      return;
    }

    if (authAudience !== "customer_admin") {
      return;
    }

    const canonicalHash = resolveCanonicalCustomerAdminHash({
      currentHash:
        typeof window === "undefined"
          ? currentRoute.hash
          : window.location.hash || currentRoute.hash,
      currentRoute,
    });
    const routeAuthorization = resolveRouteAuthorization({
      audience: authAudience,
      currentHash:
        typeof window === "undefined"
          ? currentRoute.hash
          : window.location.hash || currentRoute.hash,
      currentRoute,
      membershipRole: authMembershipRole,
    });

    if (!routeAuthorization.allowed) {
      return;
    }

    if (
      canonicalHash &&
      (typeof window === "undefined"
        ? currentRoute.hash
        : window.location.hash || currentRoute.hash) !== canonicalHash
    ) {
      navigateToPortalRoute(canonicalHash);
    }
  }, [
    auth.status,
    authAudience,
    authMembershipRole,
    currentRoute,
    hasPendingOrganization,
  ]);

  useEffect(() => {
    if (auth.status === "authenticated" && hasPendingOrganization) {
      setIsOrganizationOnboardingOpen(true);
    }
  }, [auth.status, hasPendingOrganization]);

  if (auth.status === "loading") {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Checking your account access."
        title="Checking portal access"
      >
        <PortalNotice title="Loading" tone="loading">
          <p>Checking your account access.</p>
        </PortalNotice>
      </PortalAuthLayout>
    );
  }

  if (auth.status !== "authenticated") {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Sign in or create an account to continue."
        title={
          currentRoute.key === homePortalRoute.key
            ? "Customer portal entry"
            : currentRoute.key === registerPortalRoute.key
              ? "Create your customer portal account"
              : "Sign in to the customer portal"
        }
      >
        {currentRoute.key === homePortalRoute.key ? (
          <PortalHomePage requestedRoute={requestedRoute} />
        ) : currentRoute.key === registerPortalRoute.key ? (
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
        subtitle="Taking you back to your account."
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
        isOrganizationOnboardingBusy={auth.isBusy}
        isOrganizationOnboardingOpen={isOrganizationOnboardingOpen}
        onCloseOrganizationOnboarding={() => setIsOrganizationOnboardingOpen(false)}
        onOpenOrganizationOnboarding={() => setIsOrganizationOnboardingOpen(true)}
        onCreateOrganization={async (request) => {
          if (!organizationClient) {
            throw new Error("Authentication is required");
          }

          const created = await organizationClient.createOrganization(request);
          auth.applyOrganization(createPortalActiveOrganizationRecord(created));
          setIsOrganizationOnboardingOpen(false);
          navigateToPortalRoute("#/dashboard");
        }}
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
  isOrganizationOnboardingBusy,
  isOrganizationOnboardingOpen,
  onCloseOrganizationOnboarding,
  onOpenOrganizationOnboarding,
  onCreateOrganization,
  onSignOut,
  runtimeConfig,
  session,
}: {
  appInfo: FrontendAppInfo;
  customerAdminPane: ReturnType<typeof resolveCustomerAdminPortalPane> | null;
  currentRoute: ReturnType<typeof usePortalRoute>;
  customerUserPane: ReturnType<typeof resolveCustomerUserPortalPane> | null;
  endpoints: ReturnType<typeof portalEndpoints>;
  isOrganizationOnboardingBusy: boolean;
  isOrganizationOnboardingOpen: boolean;
  onCloseOrganizationOnboarding: () => void;
  onOpenOrganizationOnboarding: () => void;
  onCreateOrganization: (request: PortalOrganizationCreateRequest) => Promise<void>;
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
        subtitle="Checking access to this area."
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
      onOpenOrganizationOnboarding={onOpenOrganizationOnboarding}
      onSignOut={onSignOut}
      routes={portalProtectedRoutes.filter(
        (route) => route.key !== organizationOnboardingPortalRoute.key,
      )}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      {session.organization_context_status === "pending" &&
      !isOrganizationOnboardingOpen ? (
        <div className="portal-auth-page" data-testid="pending-organization-callout">
          <div className="portal-auth-page__card-copy">
            <p className="portal-shell__eyebrow">Organization setup</p>
            <h2>Create your organization to continue</h2>
            <p>
              Finish creating your organization to unlock billing, team access,
              and verification tools.
            </p>
          </div>

          <div className="portal-form__actions">
            <button
              className="portal-shell__action portal-shell__action--primary"
              onClick={onOpenOrganizationOnboarding}
              type="button"
            >
              Open organization setup
            </button>
          </div>
        </div>
      ) : null}
      {currentRoute.key === "dashboard" ? (
        <DashboardPage
          pane={customerAdminPane}
          runtimeConfig={runtimeConfig}
          session={session}
        />
      ) : null}
      {currentRoute.key === "workspace" ? (
        audience === "customer_user" &&
        (customerUserPane === "search-ein" ||
          customerUserPane === "search-address") ? (
          <CustomerUserSearchPage pane={customerUserPane} />
        ) : (
          <WorkspacePage
            endpoints={endpoints}
            session={session}
          />
        )
      ) : null}
      {currentRoute.key === "search" ? (
        <WorkspacePage
          endpoints={endpoints}
          session={session}
        />
      ) : null}
      {currentRoute.key === "team" ? (
        <TeamPage session={session} />
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
          session={session}
        />
      ) : null}
      {currentRoute.key === "billing" ? (
        <BillingPage
          endpoints={endpoints}
          session={session}
        />
      ) : null}
      {currentRoute.key === "usage" ? (
        <UsagePage
          endpoints={endpoints}
          session={session}
        />
      ) : null}
      {currentRoute.key === "settings" ? (
        (audience === "customer_user" && customerUserPane === "profile") ||
        (audience === "customer_admin" && customerAdminPane === "profile") ? (
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
      {isOrganizationOnboardingOpen ? (
        <PortalOrganizationOnboardingPage
          endpoints={endpoints}
          isBusy={isOrganizationOnboardingBusy}
          onClose={onCloseOrganizationOnboarding}
          onCreateOrganization={onCreateOrganization}
        />
      ) : null}
    </PortalLayout>
  );
}
