import type { VerifyForGoodResolvedNavigationSection } from "@charity-status/shared-ui";
import type { PortalAuthenticatedSession, PortalOrganizationMembership } from "./portalSession";
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
  support: "admin",
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
  "customer-admin-support-contact": "admin",
  "customer-admin-support-report-issue": "admin",
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
  support: "#/support?nav=customer-admin-support-contact",
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

export function filterNavigationSectionsByMembershipRole(params: {
  audience: PortalNavigationAudience;
  membershipRole: CustomerMembershipRole | null;
  organizationContextStatus?: PortalAuthenticatedSession["organization_context_status"] | null;
  sections: readonly VerifyForGoodResolvedNavigationSection[];
}): VerifyForGoodResolvedNavigationSection[] {
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
        .map((item) =>
          filterNavigationItemByMembershipRole(
            item,
            params.membershipRole,
            params.organizationContextStatus ?? null,
          ),
        )
        .filter(
          (
            item,
          ): item is VerifyForGoodResolvedNavigationSection["items"][number] =>
            Boolean(item),
        ),
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

function filterNavigationItemByMembershipRole(
  item: VerifyForGoodResolvedNavigationSection["items"][number],
  membershipRole: CustomerMembershipRole | null,
  organizationContextStatus: PortalAuthenticatedSession["organization_context_status"] | null,
): VerifyForGoodResolvedNavigationSection["items"][number] | null {
  const requiredAccess = customerAdminNavigationAccess[item.key];
  if (
    requiredAccess &&
    !hasCustomerMembershipAccess({
      membershipRole,
      requiredAccess,
    })
  ) {
    if (membershipRole === null && organizationContextStatus === "pending") {
      return lockNavigationItemForPendingOrganization(item);
    }

    return null;
  }

  const children = item.children
    ?.map((child) =>
      filterNavigationItemByMembershipRole(
        child,
        membershipRole,
        organizationContextStatus,
      ),
    )
    .filter(
      (
        child,
      ): child is VerifyForGoodResolvedNavigationSection["items"][number] =>
        Boolean(child),
    );

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

function lockNavigationItemForPendingOrganization(
  item: VerifyForGoodResolvedNavigationSection["items"][number],
): VerifyForGoodResolvedNavigationSection["items"][number] {
  if ((item.children ?? []).length > 0) {
    return {
      ...item,
      children: item.children?.map((child) =>
        lockNavigationItemForPendingOrganization(child),
      ),
      href: undefined,
      helpText:
        item.helpText ?? "Available after you create your organization.",
      visibilityState: "visible",
    };
  }

  return {
    ...item,
    href: undefined,
    helpText: appendPendingOrganizationHelpText(item.helpText),
    visibilityState: "locked",
  };
}

function appendPendingOrganizationHelpText(helpText?: string) {
  const suffix = "Available after you create your organization.";
  if (!helpText) {
    return suffix;
  }

  if (helpText.includes(suffix)) {
    return helpText;
  }

  return `${helpText} ${suffix}`;
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
