import { useEffect, useState } from "react";

export interface PortalRouteDefinition {
  key: "dashboard" | "workspace" | "api-access" | "usage-billing" | "settings";
  description: string;
  hash: string;
  label: string;
}

export const portalRoutes: PortalRouteDefinition[] = [
  {
    key: "dashboard",
    label: "Dashboard",
    hash: "#/dashboard",
    description: "High-level authenticated entry point for future product signals and recent activity.",
  },
  {
    key: "workspace",
    label: "Workspace",
    hash: "#/workspace",
    description: "Organization and workspace context for account, tenant, and membership-aware slices.",
  },
  {
    key: "api-access",
    label: "API Access",
    hash: "#/api-access",
    description: "Credential, token, and API-usage entry point without assuming self-serve issuance yet.",
  },
  {
    key: "usage-billing",
    label: "Usage & Billing",
    hash: "#/usage-billing",
    description: "Subscription, checkout, Stripe portal, and usage-aware billing workflows.",
  },
  {
    key: "settings",
    label: "Settings",
    hash: "#/settings",
    description: "Organization-level settings and future integrations configuration.",
  },
];

const defaultRoute = portalRoutes[0];

export function resolvePortalRoute(hash: string): PortalRouteDefinition {
  const candidate = hash.trim() || defaultRoute.hash;
  return portalRoutes.find((route) => route.hash === candidate) ?? defaultRoute;
}

export function usePortalRoute(): PortalRouteDefinition {
  const [route, setRoute] = useState<PortalRouteDefinition>(() =>
    resolvePortalRoute(window.location.hash),
  );

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = defaultRoute.hash;
    }

    const handleHashChange = () => {
      setRoute(resolvePortalRoute(window.location.hash));
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  return route;
}
