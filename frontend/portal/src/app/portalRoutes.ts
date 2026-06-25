import { useEffect, useState } from "react";

export type PortalProtectedRouteKey =
  | "onboarding-organization"
  | "dashboard"
  | "search"
  | "team"
  | "support"
  | "billing"
  | "usage"
  | "workspace"
  | "api-access"
  | "usage-billing"
  | "settings";

export type PortalPublicRouteKey = "home" | "register" | "sign-in";
export type PortalRouteKey = PortalProtectedRouteKey | PortalPublicRouteKey;

export interface PortalRouteDefinition {
  access: "protected" | "public";
  key: PortalRouteKey;
  description: string;
  hash: string;
  label: string;
}

const PORTAL_RETURN_TO_STORAGE_KEY = "verifyforgood.portal.return-to";

export const portalPublicRoutes: PortalRouteDefinition[] = [
  {
    access: "public",
    key: "home",
    label: "Portal Home",
    hash: "#/",
    description:
      "Portal home and sign-in entry point.",
  },
  {
    access: "public",
    key: "sign-in",
    label: "Sign In",
    hash: "#/sign-in",
    description:
      "Sign in to your account.",
  },
  {
    access: "public",
    key: "register",
    label: "Register",
    hash: "#/register",
    description:
      "Create a new account.",
  },
];

export const organizationOnboardingPortalRoute: PortalRouteDefinition = {
  access: "protected",
  key: "onboarding-organization",
  label: "Create Organization",
  hash: "#/onboarding/organization",
  description:
    "Create your organization after signing in.",
};

export const portalProtectedRoutes: PortalRouteDefinition[] = [
  organizationOnboardingPortalRoute,
  {
    access: "protected",
    key: "dashboard",
    label: "Dashboard",
    hash: "#/dashboard",
    description:
      "Overview of organization activity and priorities.",
  },
  {
    access: "protected",
    key: "search",
    label: "Search",
    hash: "#/search",
    description:
      "Search and review nonprofit organizations.",
  },
  {
    access: "protected",
    key: "team",
    label: "Team",
    hash: "#/team",
    description:
      "Manage team access and review organization details.",
  },
  {
    access: "protected",
    key: "support",
    label: "Support",
    hash: "#/support",
    description:
      "Contact support and report issues for your organization.",
  },
  {
    access: "protected",
    key: "billing",
    label: "Billing",
    hash: "#/billing",
    description:
      "Review billing, plan details, and subscription status.",
  },
  {
    access: "protected",
    key: "usage",
    label: "Usage",
    hash: "#/usage",
    description:
      "Track usage, limits, and budget visibility.",
  },
  {
    access: "protected",
    key: "workspace",
    label: "Workspace",
    hash: "#/workspace",
    description:
      "Legacy workspace route.",
  },
  {
    access: "protected",
    key: "api-access",
    label: "API Access",
    hash: "#/api-access",
    description:
      "Manage API keys and related access settings.",
  },
  {
    access: "protected",
    key: "usage-billing",
    label: "Usage & Billing",
    hash: "#/usage-billing",
    description:
      "Legacy billing and usage route.",
  },
  {
    access: "protected",
    key: "settings",
    label: "Settings",
    hash: "#/settings",
    description:
      "Update organization settings and preferences.",
  },
];

export const portalRoutes: PortalRouteDefinition[] = [
  ...portalPublicRoutes,
  ...portalProtectedRoutes,
];

export const homePortalRoute = portalPublicRoutes[0];
export const signInPortalRoute = portalPublicRoutes[1];
export const registerPortalRoute = portalPublicRoutes[2];
export const defaultProtectedPortalRoute =
  portalProtectedRoutes.find((route) => route.key === "dashboard") ??
  portalProtectedRoutes[0];
export const defaultPortalRoute = homePortalRoute;

export function resolvePortalRoute(hash: string): PortalRouteDefinition {
  const candidate = getPortalHashPath(hash) || defaultPortalRoute.hash;
  const resolved =
    portalRoutes.find((route) => route.hash === candidate) ?? defaultPortalRoute;

  // Return a fresh object so hash-only query changes like ?nav=... still
  // trigger React state updates even when the base route key stays the same.
  return { ...resolved };
}

export function usePortalRoute(): PortalRouteDefinition {
  const [route, setRoute] = useState<PortalRouteDefinition>(() =>
    resolvePortalRoute(window.location.hash),
  );

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = defaultPortalRoute.hash;
    }

    const handleHashChange = () => {
      setRoute(resolvePortalRoute(window.location.hash));
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  return route;
}

export function consumePortalReturnTo(): string {
  const storage = resolvePortalSessionStorage();
  if (!storage) {
    return defaultProtectedPortalRoute.hash;
  }

  const rememberedRoute = normalizePortalHash(
    storage.getItem(PORTAL_RETURN_TO_STORAGE_KEY) || "",
  );
  storage.removeItem(PORTAL_RETURN_TO_STORAGE_KEY);
  return rememberedRoute || defaultProtectedPortalRoute.hash;
}

export function peekPortalReturnTo(): string {
  const storage = resolvePortalSessionStorage();
  if (!storage) {
    return defaultProtectedPortalRoute.hash;
  }

  return (
    normalizePortalHash(storage.getItem(PORTAL_RETURN_TO_STORAGE_KEY) || "") ||
    defaultProtectedPortalRoute.hash
  );
}

export function rememberPortalReturnTo(hash: string) {
  const storage = resolvePortalSessionStorage();
  if (!storage) {
    return;
  }

  const normalizedHash = normalizePortalHash(hash);
  if (
    !normalizedHash ||
    portalPublicRoutes.some((route) => route.hash === getPortalHashPath(normalizedHash))
  ) {
    return;
  }

  storage.setItem(PORTAL_RETURN_TO_STORAGE_KEY, normalizedHash);
}

export function navigateToPortalRoute(
  hash: string,
  options: { replace?: boolean } = {},
) {
  if (window.location.hash === hash) {
    return;
  }

  if (options.replace) {
    const nextUrl = `${window.location.pathname}${window.location.search}${hash}`;
    window.history.replaceState(window.history.state, "", nextUrl);
    window.dispatchEvent(new Event("hashchange"));
    return;
  }

  window.location.hash = hash;
}

export function getPortalHashPath(hash: string): string {
  const candidate = String(hash || "").trim();
  const [routeHash] = candidate.split("?");
  return routeHash || "";
}

function normalizePortalHash(hash: string): string {
  const candidate = String(hash || "").trim();
  const routeHash = getPortalHashPath(candidate);

  if (!routeHash || !portalRoutes.some((route) => route.hash === routeHash)) {
    return "";
  }

  return candidate;
}

function resolvePortalSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage;
}
