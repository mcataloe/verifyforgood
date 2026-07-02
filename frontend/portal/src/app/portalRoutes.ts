import { useEffect, useState } from "react";
import {
  dashboardPortalRoute,
  legacyPortalAliases,
  organizationOnboardingPortalRoute,
  organizationsPortalRoute,
  portalProtectedRoutes,
  portalPublicRoutes,
} from "./portalRouteCatalog";

export type OrganizationDetailSection =
  | "overview"
  | "filings"
  | "compliance"
  | "sources"
  | "activity";
export type PortalPageKey =
  | "onboarding-organization"
  | "dashboard"
  | "organizations"
  | "organization-detail"
  | "team"
  | "automation-general"
  | "automation-api-key"
  | "automation-oauth"
  | "billing"
  | "usage"
  | "settings-profile"
  | "settings-organization"
  | "not-found"
  | "register"
  | "sign-in"
  | "workspace"
  | "api-access"
  | "usage-billing"
  | "settings";
export type PortalProtectedRouteKey =
  | "onboarding-organization"
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
  page?: PortalPageKey;
  description: string;
  hash: string;
  label: string;
  params?: { ein?: string };
  section?: OrganizationDetailSection;
}

export {
  dashboardPortalRoute,
  organizationOnboardingPortalRoute,
  organizationsPortalRoute,
  portalProtectedRoutes,
  portalPublicRoutes,
};
export const portalRoutes = [...portalPublicRoutes, ...portalProtectedRoutes];
export const signInPortalRoute = portalPublicRoutes[0];
export const registerPortalRoute = portalPublicRoutes[1];
export const defaultProtectedPortalRoute = dashboardPortalRoute;

const returnToKey = "verifyforgood.portal.return-to";
const organizationPattern =
  /^#\/organizations\/(\d{9})(?:\/(overview|filings|compliance|sources|activity))?$/;

export function buildOrganizationPortalHash(
  ein: string,
  section: OrganizationDetailSection = "overview",
) {
  const normalizedEin = String(ein || "").replaceAll(/\D/g, "");
  return normalizedEin.length === 9
    ? `#/organizations/${normalizedEin}/${section}`
    : organizationsPortalRoute.hash;
}

export function resolvePortalRoute(hash: string): PortalRouteDefinition {
  const candidate = String(hash || "").trim();
  if (!candidate) return { ...defaultProtectedPortalRoute };

  const candidatePath = getPortalHashPath(candidate);
  const canonical =
    legacyPortalAliases[candidate] ??
    legacyPortalAliases[candidatePath] ??
    candidate;
  const path = getPortalHashPath(canonical);
  const staticRoute = portalRoutes.find((route) => route.hash === path);
  if (staticRoute) return { ...staticRoute };

  const match = path.match(organizationPattern);
  if (match) {
    const ein = match[1];
    const section = (match[2] || "overview") as OrganizationDetailSection;
    return {
      access: "protected",
      key: "workspace",
      page: "organization-detail",
      label: sectionLabel(section),
      description: "Inspect source-backed nonprofit details.",
      hash: buildOrganizationPortalHash(ein, section),
      params: { ein },
      section,
    };
  }

  return {
    access: "protected",
    key: "dashboard",
    page: "not-found",
    label: "Page Not Found",
    description: "The requested portal destination does not exist.",
    hash: path,
  };
}

export function usePortalRoute() {
  const [route, setRoute] = useState(() => resolvePortalRoute(window.location.hash));
  useEffect(() => {
    const applyRoute = () => {
      const currentHash = window.location.hash;
      const resolved = resolvePortalRoute(currentHash);
      setRoute(resolved);
      if (!currentHash || (resolved.page !== "not-found" && currentHash !== resolved.hash)) {
        window.history.replaceState(null, "", resolved.hash);
      }
    };
    applyRoute();
    window.addEventListener("hashchange", applyRoute);
    return () => window.removeEventListener("hashchange", applyRoute);
  }, []);
  return route;
}

export function consumePortalReturnTo() {
  const storage = portalSessionStorage();
  if (!storage) return defaultProtectedPortalRoute.hash;
  const remembered = normalizePortalHash(storage.getItem(returnToKey) || "");
  storage.removeItem(returnToKey);
  return remembered || defaultProtectedPortalRoute.hash;
}

export function peekPortalReturnTo() {
  const storage = portalSessionStorage();
  return storage
    ? normalizePortalHash(storage.getItem(returnToKey) || "") ||
        defaultProtectedPortalRoute.hash
    : defaultProtectedPortalRoute.hash;
}

export function rememberPortalReturnTo(hash: string) {
  const storage = portalSessionStorage();
  const normalized = normalizePortalHash(hash);
  if (
    storage &&
    normalized &&
    !portalPublicRoutes.some((route) => route.hash === normalized)
  ) {
    storage.setItem(returnToKey, normalized);
  }
}

export function navigateToPortalRoute(hash: string) {
  const resolved = resolvePortalRoute(hash);
  const destination = resolved.page === "not-found" ? hash : resolved.hash;
  if (window.location.hash !== destination) window.location.hash = destination;
}

export function getPortalHashPath(hash: string) {
  return String(hash || "").trim().split("?")[0] || "";
}

function normalizePortalHash(hash: string) {
  const resolved = resolvePortalRoute(hash);
  return resolved.page === "not-found" ? "" : resolved.hash;
}

function sectionLabel(section: OrganizationDetailSection) {
  const labels: Record<OrganizationDetailSection, string> = {
    overview: "Organization Overview",
    filings: "Organization Filings",
    compliance: "Organization Compliance Evidence",
    sources: "Organization Sources",
    activity: "Organization Activity",
  };
  return labels[section];
}

function portalSessionStorage() {
  return typeof window === "undefined" ? null : window.sessionStorage;
}
