import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type PlanCode,
} from "@charity-status/shared-types";
import {
  filterNavigationSections,
  type VerifyForGoodResolvedNavigationSection,
  type VerifyForGoodNavigationSection,
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

function navigationItem(
  routeByKey: Map<PortalRouteDefinition["key"], PortalRouteDefinition>,
  key: PortalProtectedRouteKey,
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
  const route = routeByKey.get(key);

  if (!route || route.access !== "protected") {
    throw new Error(`Missing protected portal route for navigation key "${key}".`);
  }

  return {
    key: route.key,
    label,
    helpText: options?.helpText ?? route.description,
    href: route.hash,
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
          key: "platform",
          label: "Platform",
          helpText: "Developer-oriented visibility across workspace and tenant context.",
          items: [
            navigationItem(routeByKey, "dashboard", "Overview", {
              helpText:
                "High-level system context with the same search-driven dashboard surface used elsewhere in the portal.",
            }),
            navigationItem(routeByKey, "workspace", "Tenants", {
              helpText:
                "Workspace and organization context, standing in for deeper tenant administration until dedicated platform pages exist.",
            }),
          ],
        },
        {
          key: "system",
          label: "System",
          helpText: "Technical entry points for API and integration access.",
          items: [
            navigationItem(routeByKey, "api-access", "System", {
              allowedPlans: ["growth", "pro", "enterprise"],
              helpText:
                "API credentials and integration access. Future system, audit, and feature-flag tooling should extend from this technical area.",
              visibility: {
                planRestrictedBehavior: "locked",
              },
            }),
          ],
        },
      ];
    case "portal_admin":
      return [
        {
          key: "operations",
          label: "Operations",
          helpText: "Platform administration views for customer and support workflows.",
          items: [
            navigationItem(routeByKey, "dashboard", "Dashboard"),
            navigationItem(routeByKey, "workspace", "Customers", {
              helpText:
                "Customer and workspace context until dedicated customer-management pages exist.",
            }),
          ],
        },
        {
          key: "commercial",
          label: "Commercial",
          helpText: "Subscription visibility and account-level commercial controls.",
          items: [
            navigationItem(routeByKey, "usage-billing", "Subscriptions", {
              helpText:
                "Subscription and usage visibility, standing in for a richer subscriptions surface.",
            }),
          ],
        },
        {
          key: "admin",
          label: "Admin",
          helpText: "Configuration controls for the current portal administration surface.",
          items: [
            navigationItem(routeByKey, "settings", "Settings"),
          ],
        },
      ];
    case "customer_admin":
      return [
        {
          key: "workspace",
          label: "Workspace",
          helpText: "Team and day-to-day workspace views for customer administrators.",
          items: [
            navigationItem(routeByKey, "dashboard", "Home", {
              helpText:
                "Home view for verification activity, nonprofit search, and recent results.",
            }),
            navigationItem(routeByKey, "workspace", "Team", {
              helpText:
                "Workspace context and team-adjacent administration until a dedicated member-management page exists.",
            }),
          ],
        },
        {
          key: "account",
          label: "Account",
          helpText: "Commercial, integration, and settings controls for customer admins.",
          items: [
            navigationItem(routeByKey, "usage-billing", "Billing", {
              helpText:
                "Billing and usage visibility combined into the current subscription surface.",
            }),
            navigationItem(routeByKey, "api-access", "API", {
              allowedPlans: ["growth", "pro", "enterprise"],
              helpText:
                "Self-serve API credentials and token access. Available on Growth and higher plans.",
              visibility: {
                planRestrictedBehavior: "locked",
              },
            }),
            navigationItem(routeByKey, "settings", "Settings"),
          ],
        },
      ];
    case "customer_user":
      return [
        {
          key: "work",
          label: "Work",
          helpText: "Daily review and nonprofit lookup entry points for customer users.",
          items: [
            navigationItem(routeByKey, "dashboard", "Home", {
              helpText:
                "Home view for nonprofit search, result review, and recent verification activity.",
            }),
          ],
        },
      ];
  }
}
