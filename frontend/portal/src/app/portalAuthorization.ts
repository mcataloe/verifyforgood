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

const customerUserAllowedRoutes = new Set<PortalProtectedRouteKey>([
  "api-access",
  "dashboard",
  "settings",
  "workspace",
]);

const customerUserNavigationAccess: Record<string, true> = {
  "customer-user-automation-api": true,
  "customer-user-automation-general": true,
  "customer-user-automation-oauth": true,
  "customer-user-dashboard": true,
  "customer-user-profile": true,
  "customer-user-search-address": true,
  "customer-user-search-ein": true,
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

  const filteredSections = params.sections
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

  if (params.organizationContextStatus === "pending") {
    return groupPendingOrganizationAccountNavigation(filteredSections);
  }

  return filteredSections;
}

export function resolveRouteAuthorization(params: {
  audience: PortalNavigationAudience;
  currentHash: string;
  currentRoute: PortalRouteDefinition;
  membershipRole: CustomerMembershipRole | null;
}) {
  if (params.audience === "customer_user") {
    return resolveCustomerUserRouteAuthorization(params);
  }

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

function resolveCustomerUserRouteAuthorization(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}) {
  if (params.currentRoute.access !== "protected") {
    return {
      allowed: true,
      redirectHash: null,
    } as const;
  }

  const protectedRouteKey = asProtectedRouteKey(params.currentRoute);
  if (!customerUserAllowedRoutes.has(protectedRouteKey)) {
    return {
      allowed: false,
      redirectHash: null,
    } as const;
  }

  const alias = resolvePortalNavigationAlias(params.currentHash);
  if (alias && !customerUserNavigationAccess[alias]) {
    return {
      allowed: false,
      redirectHash: null,
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

function groupPendingOrganizationAccountNavigation(
  sections: VerifyForGoodResolvedNavigationSection[],
): VerifyForGoodResolvedNavigationSection[] {
  const accountSection = sections.find((section) => section.key === "account");
  if (!accountSection || accountSection.items.length === 0) {
    return sections;
  }

  const accountBranch: VerifyForGoodResolvedNavigationSection["items"][number] =
    {
      key: "customer-admin-account",
      label: accountSection.label,
      helpText: "Available after you create your organization.",
      visibilityState: "visible",
      children: accountSection.items,
    };

  let attached = false;
  const grouped = sections
    .filter((section) => section.key !== accountSection.key)
    .map((section, index) => {
      if (!attached && (section.key === "workspace" || index === 0)) {
        attached = true;
        return {
          ...section,
          items: [...section.items, accountBranch],
        };
      }

      return section;
    });

  return attached ? grouped : sections;
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
