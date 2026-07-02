import { useEffect, useMemo } from "react";
import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { usePortalAuth } from "../auth/usePortalAuth";
import { PortalAuthProvider } from "../auth/PortalAuthProvider";
import { PortalAuthLayout } from "../components/PortalAuthLayout";
import { PortalNotice } from "../components/feedback";
import { PortalLayout } from "../components/PortalLayout";
import { PortalOrganizationProvider } from "../organization/PortalOrganizationProvider";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalActiveOrganizationRecord,
  createPortalOrganizationClient,
} from "../organization/portalOrganization";
import { PortalOrganizationOnboardingPage } from "../pages/PortalOrganizationOnboardingPage";
import { PortalRegisterPage } from "../pages/PortalRegisterPage";
import { RouteContentPage } from "../pages/RouteContentPage";
import { PortalSignInPage } from "../pages/PortalSignInPage";
import {
  resolveMembershipRoleFromContext,
  resolveRouteAuthorization,
} from "./portalAuthorization";
import { resolvePortalNavigationAudience } from "./portalNavigation";
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
  type PortalRouteDefinition,
} from "./portalRoutes";

const appInfo: FrontendAppInfo = {
  audience: "Authenticated customers managing verification workflows and account settings.",
  description: "Customer portal for nonprofit review, organization administration, integrations, usage, and billing.",
  title: "VerifyForGood Portal",
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
        subtitle="Checking whether a portal session already exists."
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
        subtitle="Sign in or create an account to open protected portal routes."
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
        subtitle="An authenticated session exists."
        title="Redirecting into the portal"
      >
        <p className="portal-auth-shell__message">
          Restoring access to {requestedRoute.label}.
        </p>
      </PortalAuthLayout>
    );
  }

  const session = auth.session;
  if (!session) return null;

  if (hasPendingOrganization) {
    return (
      <PortalAuthLayout
        app={appInfo}
        runtimeConfig={runtimeConfig}
        subtitle="Create the first organization context before the portal opens."
        title="Create your first organization"
      >
        <PortalOrganizationOnboardingPage
          endpoints={endpoints}
          isBusy={auth.isBusy}
          onCreateOrganization={async (request) => {
            if (!organizationClient) throw new Error("Authentication is required");
            const created = await organizationClient.createOrganization(request);
            auth.applyOrganization(createPortalActiveOrganizationRecord(created));
            navigateToPortalRoute("#/dashboard");
          }}
        />
      </PortalAuthLayout>
    );
  }

  return (
    <PortalOrganizationProvider
      accessToken={auth.accessToken}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      <PortalAuthorizedShell
        currentRoute={currentRoute}
        endpoints={endpoints}
        onSignOut={auth.signOut}
        runtimeConfig={runtimeConfig}
        session={session}
      />
    </PortalOrganizationProvider>
  );
}

function PortalAuthorizedShell({
  currentRoute,
  endpoints,
  onSignOut,
  runtimeConfig,
  session,
}: {
  currentRoute: PortalRouteDefinition;
  endpoints: ReturnType<typeof portalEndpoints>;
  onSignOut: () => Promise<void>;
  runtimeConfig: ReturnType<typeof readRuntimeConfig>;
  session: NonNullable<ReturnType<typeof usePortalAuth>["session"]>;
}) {
  const organization = usePortalOrganization();
  const audience = resolvePortalNavigationAudience(session.roles);
  const membershipRole = resolveMembershipRoleFromContext(
    organization.currentMembership ?? session.organization_membership,
  );
  const routeAuthorization = resolveRouteAuthorization({
    audience,
    currentHash: currentRoute.hash,
    currentRoute,
    membershipRole,
  });

  useEffect(() => {
    if (
      currentRoute.access === "protected" &&
      !routeAuthorization.allowed &&
      routeAuthorization.redirectHash &&
      currentRoute.hash !== routeAuthorization.redirectHash
    ) {
      navigateToPortalRoute(routeAuthorization.redirectHash);
    }
  }, [currentRoute, routeAuthorization]);

  useEffect(() => {
    document.title = `${currentRoute.label} | VerifyForGood`;
    window.requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>("main h1, main h2");
      if (heading) {
        heading.tabIndex = -1;
        heading.focus();
      }
    });
  }, [currentRoute.hash, currentRoute.label]);

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
      <RouteContentPage
        audience={audience}
        currentRoute={currentRoute}
        endpoints={endpoints}
        runtimeConfig={runtimeConfig}
        session={session}
      />
    </PortalLayout>
  );
}
