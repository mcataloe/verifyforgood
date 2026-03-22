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

const ACCOUNT_ADMIN_ROLES: FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
];

const BUILDER_ROLES: FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
  FRONTEND_ACCESS_ROLE.developer,
];

const ORGANIZATION_MEMBER_ROLES: FrontendAccessRole[] = [
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
      helpText: "Verification activity and day-to-day review entry points.",
      items: [
        navigationItem(routeByKey, "dashboard", "Dashboard"),
      ],
    },
    {
      key: "organization",
      label: "Organization",
      helpText: "Tenant context and organization-level configuration.",
      items: [
        {
          ...navigationItem(routeByKey, "workspace", "Overview", {
            helpText:
              "Organization and workspace context for account, tenant, and membership-aware slices.",
          }),
          allowedRoles: ORGANIZATION_MEMBER_ROLES,
        },
        {
          ...navigationItem(routeByKey, "settings", "Settings"),
          allowedRoles: ACCOUNT_ADMIN_ROLES,
        },
      ],
    },
    {
      key: "build",
      label: "Build",
      helpText: "Developer-facing access for API integration and automation.",
      items: [
        {
          ...navigationItem(routeByKey, "api-access", "API", {
            allowedPlans: ["growth", "pro", "enterprise"],
            helpText:
              "Self-serve API credentials and token access. Available on Growth and higher plans.",
            visibility: {
              planRestrictedBehavior: "locked",
            },
          }),
          allowedRoles: BUILDER_ROLES,
        },
      ],
    },
    {
      key: "account",
      label: "Account",
      helpText: "Commercial and subscription controls for account administrators.",
      items: [
        {
          ...navigationItem(routeByKey, "usage-billing", "Billing"),
          allowedRoles: ACCOUNT_ADMIN_ROLES,
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
