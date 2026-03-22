import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
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

const CUSTOMER_ADMIN_ROLES: FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
  FRONTEND_ACCESS_ROLE.developer,
];

export function buildPortalNavigationSections(
  routes: readonly PortalRouteDefinition[],
): VerifyForGoodNavigationSection[] {
  const routeByKey = new Map(
    routes.map((route) => [route.key, route] as const),
  );

  return [
    {
      key: "review",
      label: "Review",
      helpText: "Core verification and entity review entry points.",
      items: [
        navigationItem(routeByKey, "dashboard", "Dashboard"),
      ],
    },
    {
      key: "operations",
      label: "Operations",
      helpText: "Customer workspace, credentials, and billing controls.",
      items: [
        {
          ...navigationItem(routeByKey, "workspace", "Workspace"),
          allowedRoles: CUSTOMER_ADMIN_ROLES,
        },
        {
          ...navigationItem(routeByKey, "api-access", "API"),
          allowedRoles: CUSTOMER_ADMIN_ROLES,
        },
        {
          ...navigationItem(routeByKey, "usage-billing", "Billing"),
          allowedRoles: CUSTOMER_ADMIN_ROLES,
        },
      ],
    },
    {
      key: "admin",
      label: "Admin",
      helpText: "Account-level configuration and future management tools.",
      items: [
        {
          ...navigationItem(routeByKey, "settings", "Settings"),
          allowedRoles: CUSTOMER_ADMIN_ROLES,
        },
      ],
    },
  ];
}

export function resolvePortalNavigation(params: {
  plan: string;
  roles: readonly FrontendAccessRole[];
  routes: readonly PortalRouteDefinition[];
}): VerifyForGoodResolvedNavigationSection[] {
  return filterNavigationSections(buildPortalNavigationSections(params.routes), {
    plan: params.plan,
    roles: params.roles,
  });
}

function navigationItem(
  routeByKey: Map<PortalRouteDefinition["key"], PortalRouteDefinition>,
  key: PortalProtectedRouteKey,
  label: string,
) {
  const route = routeByKey.get(key);

  if (!route || route.access !== "protected") {
    throw new Error(`Missing protected portal route for navigation key "${key}".`);
  }

  return {
    key: route.key,
    label,
    helpText: route.description,
    href: route.hash,
    visibility: {
      planRestrictedBehavior: "locked" as const,
      roleRestrictedBehavior: "hidden" as const,
    },
  };
}
