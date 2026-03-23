import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type PlanCode,
} from "@charity-status/shared-types";
import {
  filterNavigationSections,
  type VerifyForGoodNavigationSection,
  type VerifyForGoodResolvedNavigationItem,
  type VerifyForGoodResolvedNavigationSection,
} from "@charity-status/shared-ui";
import type {
  PortalProtectedRouteKey,
  PortalRouteDefinition,
} from "./portalRoutes";

export type PortalNavigationAudience =
  | "developer"
  | "portal_admin"
  | "customer_admin"
  | "customer_user";

export function buildPortalNavigationSections(
  routes: readonly PortalRouteDefinition[],
  audience: PortalNavigationAudience,
): VerifyForGoodNavigationSection[] {
  const routeByKey = new Map(
    routes.map((route) => [route.key, route] as const),
  );

  return buildAudienceNavigationSections(routeByKey, audience);
}

export function resolvePortalNavigation(params: {
  plan: string;
  roles: readonly FrontendAccessRole[];
  routes: readonly PortalRouteDefinition[];
}): VerifyForGoodResolvedNavigationSection[] {
  const audience = resolvePortalNavigationAudience(params.roles);

  return filterNavigationSections(
    buildPortalNavigationSections(params.routes, audience),
    {
      plan: params.plan,
      roles: params.roles,
    },
  );
}

export function resolvePortalNavigationAudience(
  roles: readonly FrontendAccessRole[],
): PortalNavigationAudience {
  if (roles.includes(FRONTEND_ACCESS_ROLE.developer)) {
    return "developer";
  }

  if (roles.includes(FRONTEND_ACCESS_ROLE.portalAdmin)) {
    return "portal_admin";
  }

  if (roles.includes(FRONTEND_ACCESS_ROLE.customerAdmin)) {
    return "customer_admin";
  }

  return "customer_user";
}

export function getPortalAccessLabel(
  roles: readonly FrontendAccessRole[],
): string {
  const audience = resolvePortalNavigationAudience(roles);

  switch (audience) {
    case "developer":
      return "Developer";
    case "portal_admin":
      return "Platform admin";
    case "customer_admin":
      return "Admin";
    case "customer_user":
      return "User";
  }
}

export function resolveActivePortalNavigationKey(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
  navigationSections: readonly VerifyForGoodResolvedNavigationSection[];
}): string {
  const normalizedHash = String(params.currentHash || "").trim();
  const exactMatch = findNavigationItem(
    params.navigationSections,
    (item) => item.href === normalizedHash,
  );

  if (exactMatch) {
    return exactMatch.key;
  }

  const routeMatch = findNavigationItem(
    params.navigationSections,
    (item) => item.href?.split("?")[0] === params.currentRoute.hash,
  );

  return routeMatch?.key ?? params.currentRoute.key;
}

function navigationItem(
  routeByKey: Map<PortalRouteDefinition["key"], PortalRouteDefinition>,
  routeKey: PortalProtectedRouteKey,
  itemKey: string,
  label: string,
  options?: {
    allowedPlans?: readonly PlanCode[];
    helpText?: string;
    visibility?: {
      planRestrictedBehavior?: "hidden" | "locked";
      roleRestrictedBehavior?: "hidden" | "locked";
    };
  },
) {
  const route = routeByKey.get(routeKey);

  if (!route || route.access !== "protected") {
    throw new Error(
      `Missing protected portal route for navigation key "${routeKey}".`,
    );
  }

  return {
    key: itemKey,
    label,
    helpText: options?.helpText ?? route.description,
    href: `${route.hash}?nav=${itemKey}`,
    allowedPlans: options?.allowedPlans,
    visibility: {
      planRestrictedBehavior: "locked" as const,
      roleRestrictedBehavior: "hidden" as const,
      ...options?.visibility,
    },
  };
}

function buildAudienceNavigationSections(
  routeByKey: Map<PortalRouteDefinition["key"], PortalRouteDefinition>,
  audience: PortalNavigationAudience,
): VerifyForGoodNavigationSection[] {
  switch (audience) {
    case "developer":
      return [
        {
          key: "build",
          label: "Build",
          helpText:
            "Platform-wide views for tenant, plan, and environment oversight.",
          items: [
            navigationItem(
              routeByKey,
              "dashboard",
              "developer-overview",
              "Overview",
              {
                helpText:
                  "Shared operational snapshot for the current environment.",
              },
            ),
            navigationItem(
              routeByKey,
              "workspace",
              "developer-tenants",
              "Tenants",
              {
                helpText:
                  "Tenant and workspace context for platform operators.",
              },
            ),
            navigationItem(
              routeByKey,
              "usage-billing",
              "developer-plans",
              "Plans",
              {
                helpText: "Plan assignment, quotas, and billing posture.",
              },
            ),
          ],
        },
        {
          key: "controls",
          label: "Controls",
          helpText:
            "Rollout and governance controls across the platform surface.",
          items: [
            navigationItem(
              routeByKey,
              "settings",
              "developer-feature-flags",
              "Feature Flags",
              {
                helpText: "Feature rollout and gated capability controls.",
              },
            ),
            navigationItem(routeByKey, "settings", "developer-audit", "Audit", {
              helpText: "Change review and audit visibility.",
            }),
            navigationItem(
              routeByKey,
              "api-access",
              "developer-system",
              "System",
              {
                allowedPlans: ["growth", "pro", "enterprise"],
                helpText: "API credentials, integrations, and runtime access.",
                visibility: {
                  planRestrictedBehavior: "locked",
                },
              },
            ),
          ],
        },
      ];
    case "portal_admin":
      return [
        {
          key: "operations",
          label: "Operations",
          helpText: "Daily customer-management and support workflows.",
          items: [
            navigationItem(
              routeByKey,
              "dashboard",
              "portal-admin-dashboard",
              "Dashboard",
              {
                helpText: "Operational overview for the portal surface.",
              },
            ),
            navigationItem(
              routeByKey,
              "workspace",
              "portal-admin-customers",
              "Customers",
              {
                helpText: "Customer workspace context and account lookup.",
              },
            ),
            navigationItem(
              routeByKey,
              "workspace",
              "portal-admin-support",
              "Support",
              {
                helpText: "Support-led workspace review and troubleshooting.",
              },
            ),
          ],
        },
        {
          key: "revenue",
          label: "Revenue",
          helpText: "Subscription oversight and reporting surfaces.",
          items: [
            navigationItem(
              routeByKey,
              "usage-billing",
              "portal-admin-subscriptions",
              "Subscriptions",
              {
                helpText:
                  "Subscription status, plan changes, and billing posture.",
              },
            ),
            navigationItem(
              routeByKey,
              "usage-billing",
              "portal-admin-reports",
              "Reports",
              {
                helpText: "Commercial and usage reporting snapshots.",
              },
            ),
          ],
        },
        {
          key: "configure",
          label: "Configure",
          helpText: "Administrative settings and platform policies.",
          items: [
            navigationItem(
              routeByKey,
              "settings",
              "portal-admin-settings",
              "Settings",
              {
                helpText: "Administrative settings and configuration controls.",
              },
            ),
          ],
        },
      ];
    case "customer_admin":
      return [
        {
          key: "workspace",
          label: "Workspace",
          helpText: "Day-to-day verification, team, and workspace operations.",
          items: [
            navigationItem(
              routeByKey,
              "dashboard",
              "customer-admin-home",
              "Home",
              {
                helpText:
                  "Recent activity, nonprofit search, and review entry points.",
              },
            ),
            navigationItem(
              routeByKey,
              "workspace",
              "customer-admin-team",
              "Team",
              {
                helpText: "Team, membership, and workspace context.",
              },
            ),
          ],
        },
        {
          key: "account",
          label: "Account",
          helpText:
            "Commercial, API, and settings controls for account owners.",
          items: [
            navigationItem(
              routeByKey,
              "usage-billing",
              "customer-admin-billing",
              "Billing",
              {
                helpText: "Plan, billing actions, and subscription controls.",
              },
            ),
            navigationItem(
              routeByKey,
              "usage-billing",
              "customer-admin-usage",
              "Usage",
              {
                helpText: "Usage baselines, limits, and budget visibility.",
              },
            ),
            navigationItem(
              routeByKey,
              "api-access",
              "customer-admin-api",
              "API",
              {
                allowedPlans: ["growth", "pro", "enterprise"],
                helpText: "Self-serve API credentials and token access.",
                visibility: {
                  planRestrictedBehavior: "locked",
                },
              },
            ),
            navigationItem(
              routeByKey,
              "settings",
              "customer-admin-settings",
              "Settings",
              {
                helpText: "Workspace settings and budget controls.",
              },
            ),
          ],
        },
      ];
    case "customer_user":
      return [
        {
          key: "work",
          label: "Work",
          helpText:
            "Daily nonprofit search and verification workflow entry points.",
          items: [
            navigationItem(
              routeByKey,
              "dashboard",
              "customer-user-home",
              "Home",
              {
                helpText:
                  "Starting point for recent activity and quick actions.",
              },
            ),
            navigationItem(
              routeByKey,
              "dashboard",
              "customer-user-search",
              "Search",
              {
                helpText: "Find organizations and begin verification review.",
              },
            ),
            navigationItem(
              routeByKey,
              "dashboard",
              "customer-user-results",
              "Results",
              {
                helpText: "Return to the latest search and review output.",
              },
            ),
          ],
        },
        {
          key: "personal",
          label: "Personal",
          helpText: "Reporting access and personal workspace context.",
          items: [
            navigationItem(
              routeByKey,
              "usage-billing",
              "customer-user-reports",
              "Reports",
              {
                helpText: "Reporting snapshots tied to recent portal activity.",
              },
            ),
            navigationItem(
              routeByKey,
              "settings",
              "customer-user-profile",
              "Profile",
              {
                helpText: "Profile and account-level settings access.",
              },
            ),
          ],
        },
      ];
  }
}

function findNavigationItem(
  sections: readonly VerifyForGoodResolvedNavigationSection[],
  predicate: (item: VerifyForGoodResolvedNavigationItem) => boolean,
) {
  for (const section of sections) {
    for (const item of section.items) {
      const match = findNavigationItemRecursive(item, predicate);
      if (match) {
        return match;
      }
    }
  }

  return undefined;
}

function findNavigationItemRecursive(
  item: VerifyForGoodResolvedNavigationItem,
  predicate: (item: VerifyForGoodResolvedNavigationItem) => boolean,
): VerifyForGoodResolvedNavigationItem | undefined {
  if (predicate(item)) {
    return item;
  }

  for (const child of item.children ?? []) {
    const match = findNavigationItemRecursive(child, predicate);
    if (match) {
      return match;
    }
  }

  return undefined;
}
