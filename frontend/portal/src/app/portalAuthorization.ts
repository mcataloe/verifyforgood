import type { PortalOrganizationMembership } from "./portalSession";
import type {
  PortalNavigationAudience,
} from "./portalNavigation";
import type {
  PortalProtectedRouteKey,
  PortalRouteDefinition,
} from "./portalRoutes";

export type CustomerMembershipRole = "admin" | "user";
export type CustomerRouteAccessRequirement = "admin" | "user";

const customerAdminRouteAccess: Partial<
  Record<PortalProtectedRouteKey, CustomerRouteAccessRequirement>
> = {
  "api-access": "admin",
  billing: "admin",
  dashboard: "user",
  search: "user",
  settings: "admin",
  team: "user",
  "usage-billing": "admin",
  usage: "admin",
  workspace: "user",
};

const customerAdminNavigationAccess: Record<
  string,
  CustomerRouteAccessRequirement
> = {
  "customer-admin-api": "admin",
  "customer-admin-billing": "admin",
  "customer-admin-home": "user",
  "customer-admin-search": "user",
  "customer-admin-settings": "admin",
  "customer-admin-team": "user",
  "customer-admin-usage": "admin",
};

const nearestAllowedCustomerAdminRouteByKey: Partial<
  Record<PortalProtectedRouteKey, string>
> = {
  search: "#/search",
  team: "#/team",
  billing: "#/billing",
  usage: "#/usage",
  dashboard: "#/dashboard?nav=customer-admin-home",
  workspace: "#/search",
  "usage-billing": "#/billing",
};

export function normalizeCustomerMembershipRole(
  role: string | null | undefined,
): CustomerMembershipRole | null {
  const candidate = String(role || "").trim().toLowerCase();
  if (candidate === "admin" || candidate === "user") {
    return candidate;
  }

  return null;
}

export function hasCustomerMembershipAccess(params: {
  membershipRole: CustomerMembershipRole | null;
  requiredAccess: CustomerRouteAccessRequirement;
}) {
  if (params.requiredAccess === "user") {
    return true;
  }

  return params.membershipRole === "admin";
}

export function filterNavigationSectionsByMembershipRole<
  TSection extends { items: TItem[] },
  TItem extends { children?: TItem[]; key: string },
>(params: {
  audience: PortalNavigationAudience;
  membershipRole: CustomerMembershipRole | null;
  sections: readonly TSection[];
}): TSection[] {
  if (params.audience !== "customer_admin") {
    return params.sections.map((section) => ({
      ...section,
      items: section.items.map((item) => cloneNavigationItem(item)),
    }));
  }

  return params.sections
    .map((section) => ({
      ...section,
      items: section.items
        .map((item) => filterNavigationItemByMembershipRole(item, params.membershipRole))
        .filter(Boolean) as TItem[],
    }))
    .filter((section) => section.items.length > 0);
}

export function resolveRouteAuthorization(params: {
  audience: PortalNavigationAudience;
  currentHash: string;
  currentRoute: PortalRouteDefinition;
  membershipRole: CustomerMembershipRole | null;
}) {
  if (params.audience !== "customer_admin") {
    return {
      allowed: true,
      redirectHash: null,
    } as const;
  }

  if (params.currentRoute.access !== "protected") {
    return {
      allowed: true,
      redirectHash: null,
    } as const;
  }

  const protectedRouteKey = asProtectedRouteKey(params.currentRoute);
  const routeRequirement = customerAdminRouteAccess[protectedRouteKey];
  if (
    routeRequirement &&
    !hasCustomerMembershipAccess({
      membershipRole: params.membershipRole,
      requiredAccess: routeRequirement,
    })
  ) {
    return {
      allowed: false,
      redirectHash: resolveNearestAllowedCustomerRoute({
        currentRoute: params.currentRoute,
        membershipRole: params.membershipRole,
      }),
    } as const;
  }

  const alias = resolvePortalNavigationAlias(params.currentHash);
  const aliasRequirement = alias
    ? customerAdminNavigationAccess[alias]
    : undefined;
  if (
    aliasRequirement &&
    !hasCustomerMembershipAccess({
      membershipRole: params.membershipRole,
      requiredAccess: aliasRequirement,
    })
  ) {
    return {
      allowed: false,
      redirectHash: resolveNearestAllowedCustomerRoute({
        currentRoute: params.currentRoute,
        membershipRole: params.membershipRole,
      }),
    } as const;
  }

  return {
    allowed: true,
    redirectHash: null,
  } as const;
}

export function resolveNearestAllowedCustomerRoute(params: {
  currentRoute: PortalRouteDefinition;
  membershipRole: CustomerMembershipRole | null;
}) {
  if (params.currentRoute.access !== "protected") {
    return "#/dashboard?nav=customer-admin-home";
  }

  const protectedRouteKey = asProtectedRouteKey(params.currentRoute);
  const currentRouteFallback =
    nearestAllowedCustomerAdminRouteByKey[protectedRouteKey];
  if (
    currentRouteFallback &&
    hasCustomerMembershipAccess({
      membershipRole: params.membershipRole,
      requiredAccess: customerAdminRouteAccess[protectedRouteKey] ?? "user",
    })
  ) {
    return currentRouteFallback;
  }

  return "#/dashboard?nav=customer-admin-home";
}

function resolvePortalNavigationAlias(currentHash: string): string | null {
  const query = String(currentHash || "").split("?")[1];
  const params = new URLSearchParams(query);
  const nav = params.get("nav");

  return nav?.trim() || null;
}

function filterNavigationItemByMembershipRole<TItem extends { children?: TItem[]; key: string }>(
  item: TItem,
  membershipRole: CustomerMembershipRole | null,
): TItem | null {
  const requiredAccess = customerAdminNavigationAccess[item.key];
  if (
    requiredAccess &&
    !hasCustomerMembershipAccess({
      membershipRole,
      requiredAccess,
    })
  ) {
    return null;
  }

  const children = item.children
    ?.map((child) => filterNavigationItemByMembershipRole(child, membershipRole))
    .filter(Boolean) as TItem[] | undefined;

  if (item.children && (!children || children.length === 0)) {
    return null;
  }

  return {
    ...item,
    ...(children ? { children } : {}),
  };
}

function cloneNavigationItem<TItem extends { children?: TItem[] }>(item: TItem): TItem {
  return {
    ...item,
    ...(item.children
      ? { children: item.children.map((child) => cloneNavigationItem(child)) }
      : {}),
  };
}

export function resolveMembershipRoleFromContext(
  membership: PortalOrganizationMembership | null | undefined,
) {
  return normalizeCustomerMembershipRole(membership?.role);
}

function asProtectedRouteKey(
  route: PortalRouteDefinition,
): PortalProtectedRouteKey {
  return route.key as PortalProtectedRouteKey;
}
