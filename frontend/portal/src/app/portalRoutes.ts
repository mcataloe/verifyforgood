import { useEffect, useState } from "react";

export type PortalProtectedRouteKey =
  | "dashboard"
  | "workspace"
  | "api-access"
  | "usage-billing"
  | "settings";

export type PortalPublicRouteKey = "register" | "sign-in";
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
    key: "sign-in",
    label: "Sign In",
    hash: "#/sign-in",
    description:
      "Public auth boundary for the portal shell while production identity integration remains deferred.",
  },
  {
    access: "public",
    key: "register",
    label: "Register",
    hash: "#/register",
    description:
      "Public registration boundary for creating a new portal account before onboarding is complete.",
  },
];

export const portalProtectedRoutes: PortalRouteDefinition[] = [
  {
    access: "protected",
    key: "dashboard",
    label: "Dashboard",
    hash: "#/dashboard",
    description:
      "High-level authenticated entry point for future product signals and recent activity.",
  },
  {
    access: "protected",
    key: "workspace",
    label: "Workspace",
    hash: "#/workspace",
    description:
      "Organization and workspace context for account, tenant, and membership-aware slices.",
  },
  {
    access: "protected",
    key: "api-access",
    label: "API Access",
    hash: "#/api-access",
    description:
      "Credential, token, and API-usage entry point without assuming self-serve issuance yet.",
  },
  {
    access: "protected",
    key: "usage-billing",
    label: "Usage & Billing",
    hash: "#/usage-billing",
    description:
      "Subscription, backend-managed billing actions, and usage-aware billing workflows.",
  },
  {
    access: "protected",
    key: "settings",
    label: "Settings",
    hash: "#/settings",
    description:
      "Organization-level settings and future integrations configuration.",
  },
];

export const portalRoutes: PortalRouteDefinition[] = [
  ...portalPublicRoutes,
  ...portalProtectedRoutes,
];

export const signInPortalRoute = portalPublicRoutes[0];
export const registerPortalRoute = portalPublicRoutes[1];
export const defaultProtectedPortalRoute = portalProtectedRoutes[0];

export function resolvePortalRoute(hash: string): PortalRouteDefinition {
  const candidate = getPortalHashPath(hash) || defaultProtectedPortalRoute.hash;
  const resolved =
    portalRoutes.find((route) => route.hash === candidate) ??
    defaultProtectedPortalRoute;

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
      window.location.hash = defaultProtectedPortalRoute.hash;
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

export function navigateToPortalRoute(hash: string) {
  if (window.location.hash === hash) {
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
