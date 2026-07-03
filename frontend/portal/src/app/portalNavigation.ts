import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
} from "@charity-status/shared-types";
import {
  filterNavigationSections,
  type VerifyForGoodNavigationSection,
  type VerifyForGoodResolvedNavigationItem,
  type VerifyForGoodResolvedNavigationSection,
} from "@charity-status/shared-ui";
import type { CustomerMembershipRole } from "./portalAuthorization";
import { filterNavigationSectionsByMembershipRole } from "./portalAuthorization";
import { buildAudienceNavigationSections } from "./portalNavigationCatalog";
import type { PortalRouteDefinition } from "./portalRoutes";

export type PortalNavigationAudience =
  | "developer"
  | "portal_admin"
  | "customer_admin"
  | "customer_user";
export type CustomerUserPortalPane =
  | "dashboard"
  | "search-ein"
  | "search-address"
  | "automation-general"
  | "automation-api"
  | "automation-oauth"
  | "profile";
export type CustomerAdminPortalPane =
  | "home"
  | "search"
  | "team"
  | "support-contact"
  | "support-report-issue"
  | "billing"
  | "usage"
  | "api"
  | "settings"
  | "profile";

export function buildPortalNavigationSections(
  routes: readonly PortalRouteDefinition[],
  audience: PortalNavigationAudience,
): VerifyForGoodNavigationSection[] {
  return buildAudienceNavigationSections(
    new Map(routes.map((route) => [route.page, route] as const)),
    audience,
  );
}

export function resolvePortalNavigation(params: {
  membershipRole?: CustomerMembershipRole | null;
  organizationContextStatus?: "active" | "pending" | null;
  plan: string;
  roles: readonly FrontendAccessRole[];
  routes: readonly PortalRouteDefinition[];
}): VerifyForGoodResolvedNavigationSection[] {
  const audience = resolvePortalNavigationAudience(params.roles);
  const sections = filterNavigationSections(
    buildPortalNavigationSections(params.routes, audience),
    { plan: params.plan, roles: params.roles },
  );
  return filterNavigationSectionsByMembershipRole({
    audience,
    membershipRole: params.membershipRole ?? null,
    organizationContextStatus: params.organizationContextStatus ?? null,
    sections,
  });
}

export function resolvePortalNavigationAudience(
  roles: readonly FrontendAccessRole[],
): PortalNavigationAudience {
  if (roles.includes(FRONTEND_ACCESS_ROLE.developer)) return "developer";
  if (roles.includes(FRONTEND_ACCESS_ROLE.portalAdmin)) return "portal_admin";
  if (roles.includes(FRONTEND_ACCESS_ROLE.customerAdmin))
    return "customer_admin";
  return "customer_user";
}

export function getPortalAccessLabel(roles: readonly FrontendAccessRole[]) {
  const labels: Record<PortalNavigationAudience, string> = {
    developer: "Developer",
    portal_admin: "Platform admin",
    customer_admin: "Admin",
    customer_user: "User",
  };
  return labels[resolvePortalNavigationAudience(roles)];
}

export function resolveCustomerUserPortalPane(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}): CustomerUserPortalPane {
  switch (params.currentRoute.page) {
    case "organizations":
    case "organization-detail":
      return "search-ein";
    case "automation-general":
      return "automation-general";
    case "automation-api-key":
      return "automation-api";
    case "automation-oauth":
      return "automation-oauth";
    case "settings-profile":
      return "profile";
    default:
      return "dashboard";
  }
}

export function resolveCustomerAdminPortalPane(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}): CustomerAdminPortalPane {
  switch (params.currentRoute.page) {
    case "team":
      return "team";
    case "billing":
      return "billing";
    case "usage":
      return "usage";
    case "automation-general":
    case "automation-api-key":
    case "automation-oauth":
      return "api";
    case "settings-profile":
    case "settings-organization":
      return "settings";
    default:
      return "home";
  }
}

export function resolvePortalProfileNavigationTarget(params: {
  routes: readonly PortalRouteDefinition[];
}): { href: string; label: string } | undefined {
  const route = params.routes.find(
    (candidate) => candidate.page === "settings-profile",
  );
  return route ? { href: route.hash, label: route.label } : undefined;
}

export function resolveActivePortalNavigationKey(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
  navigationSections: readonly VerifyForGoodResolvedNavigationSection[];
}): string {
  const exact = findNavigationItem(
    params.navigationSections,
    (item) => item.href === params.currentRoute.hash,
  );
  if (exact) return exact.key;

  if (params.currentRoute.page === "organization-detail") {
    const organizationItem = findNavigationItem(
      params.navigationSections,
      (item) =>
        item.href === "#/organizations" ||
        item.key.endsWith("organizations") ||
        item.key === "portal-admin-customers" ||
        item.key === "developer-tenants",
    );
    if (organizationItem) return organizationItem.key;
  }
  return params.currentRoute.page ?? params.currentRoute.key;
}

function findNavigationItem(
  sections: readonly VerifyForGoodResolvedNavigationSection[],
  predicate: (item: VerifyForGoodResolvedNavigationItem) => boolean,
) {
  for (const section of sections) {
    for (const item of section.items) {
      const match = findNavigationItemRecursive(item, predicate);
      if (match) return match;
    }
  }
  return undefined;
}

function findNavigationItemRecursive(
  item: VerifyForGoodResolvedNavigationItem,
  predicate: (item: VerifyForGoodResolvedNavigationItem) => boolean,
): VerifyForGoodResolvedNavigationItem | undefined {
  if (predicate(item)) return item;
  for (const child of item.children ?? []) {
    const match = findNavigationItemRecursive(child, predicate);
    if (match) return match;
  }
  return undefined;
}
