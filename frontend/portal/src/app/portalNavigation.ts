import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type PlanCode,
} from "@charity-status/shared-types";
import {
  IconBolt,
  IconDashboard,
  IconSearch,
  IconSettingsAutomation,
  IconKey,
} from "@tabler/icons-react";
import {
  filterNavigationSections,
  type VerifyForGoodNavigationSection,
  type VerifyForGoodResolvedNavigationItem,
  type VerifyForGoodResolvedNavigationSection,
} from "@charity-status/shared-ui";
import { createElement, type ReactNode } from "react";
import type {
  PortalProtectedRouteKey,
  PortalRouteDefinition,
} from "./portalRoutes";
import type { CustomerMembershipRole } from "./portalAuthorization";
import { filterNavigationSectionsByMembershipRole as filterResolvedNavigationSectionsByMembershipRole } from "./portalAuthorization";

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

const customerUserPaneByAlias: Record<string, CustomerUserPortalPane> = {
  "customer-user-automation-api": "automation-api",
  "customer-user-automation-general": "automation-general",
  "customer-user-automation-oauth": "automation-oauth",
  "customer-user-dashboard": "dashboard",
  "customer-user-profile": "profile",
  "customer-user-search-address": "search-address",
  "customer-user-search-ein": "search-ein",
};

const customerAdminPaneByAlias: Record<string, CustomerAdminPortalPane> = {
  "customer-admin-api": "api",
  "customer-admin-billing": "billing",
  "customer-admin-home": "home",
  "customer-admin-profile": "profile",
  "customer-admin-search": "search",
  "customer-admin-settings": "settings",
  "customer-admin-support-contact": "support-contact",
  "customer-admin-support-report-issue": "support-report-issue",
  "customer-admin-team": "team",
  "customer-admin-usage": "usage",
};

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
  membershipRole?: CustomerMembershipRole | null;
  organizationContextStatus?: "active" | "pending" | null;
  plan: string;
  roles: readonly FrontendAccessRole[];
  routes: readonly PortalRouteDefinition[];
}): VerifyForGoodResolvedNavigationSection[] {
  const audience = resolvePortalNavigationAudience(params.roles);
  const sections = filterNavigationSections(
    buildPortalNavigationSections(params.routes, audience),
    {
      plan: params.plan,
      roles: params.roles,
    },
  );

  return filterResolvedNavigationSectionsByMembershipRole({
    audience,
    membershipRole: params.membershipRole ?? null,
    organizationContextStatus: params.organizationContextStatus ?? null,
    sections,
  });
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

export function resolveCustomerUserPortalPane(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}): CustomerUserPortalPane {
  const navAlias = resolvePortalNavigationAlias(params.currentHash);

  if (navAlias && customerUserPaneByAlias[navAlias]) {
    return customerUserPaneByAlias[navAlias];
  }

  switch (params.currentRoute.key) {
    case "dashboard":
      return "dashboard";
    case "workspace":
      return "search-ein";
    case "api-access":
      return "automation-general";
    case "settings":
      return "profile";
    default:
      return "dashboard";
  }
}

export function resolveCustomerAdminPortalPane(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}): CustomerAdminPortalPane {
  const navAlias = resolvePortalNavigationAlias(params.currentHash);

  if (navAlias && customerAdminPaneByAlias[navAlias]) {
    return customerAdminPaneByAlias[navAlias];
  }

  switch (params.currentRoute.key) {
    case "dashboard":
      return "home";
    case "search":
      return "search";
    case "team":
      return "team";
    case "support":
      return "support-contact";
    case "workspace":
      return "search";
    case "billing":
      return "billing";
    case "usage":
    case "usage-billing":
      return "usage";
    case "api-access":
      return "api";
    case "settings":
      return "settings";
    default:
      return "home";
  }
}

export function resolvePortalProfileNavigationTarget(params: {
  audience: PortalNavigationAudience;
  routes: readonly PortalRouteDefinition[];
}): { href: string; label: string } | undefined {
  const routeByKey = new Map(params.routes.map((route) => [route.key, route] as const));
  const settingsRoute = routeByKey.get("settings");

  if (!settingsRoute) {
    return undefined;
  }

  if (params.audience === "customer_user") {
    return {
      href: `${settingsRoute.hash}?nav=customer-user-profile`,
      label: "Open profile",
    };
  }

  if (params.audience === "customer_admin") {
    return {
      href: `${settingsRoute.hash}?nav=customer-admin-profile`,
      label: "Open profile",
    };
  }

  const suffix = params.audience.replaceAll("_", "-");

  return {
    href: `${settingsRoute.hash}?nav=${suffix}-settings`,
    label: "Profile & preferences",
  };
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

export function resolveCanonicalCustomerAdminHash(params: {
  currentHash: string;
  currentRoute: PortalRouteDefinition;
}): string | null {
  const alias = resolvePortalNavigationAlias(params.currentHash);

  switch (params.currentRoute.key) {
    case "dashboard":
      return alias === "customer-admin-home" ? "#/dashboard" : null;
    case "search":
      return "#/search";
    case "team":
      return "#/team";
    case "support":
      if (alias === "customer-admin-support-report-issue") {
        return "#/support?nav=customer-admin-support-report-issue";
      }

      return "#/support?nav=customer-admin-support-contact";
    case "billing":
      return "#/billing";
    case "usage":
      return "#/usage";
    case "api-access":
      return alias === "customer-admin-api" ? "#/api-access" : null;
    case "settings":
      if (alias === "customer-admin-settings") {
        return "#/settings";
      }

      if (alias === "customer-admin-profile") {
        return "#/settings?nav=customer-admin-profile";
      }

      return null;
    case "workspace":
      if (alias === "customer-admin-team") {
        return "#/team";
      }

      return "#/search";
    case "usage-billing":
      if (alias === "customer-admin-usage") {
        return "#/usage";
      }

      return "#/billing";
    default:
      return null;
  }
}

function navigationItem(
  routeByKey: Map<PortalRouteDefinition["key"], PortalRouteDefinition>,
  routeKey: PortalProtectedRouteKey,
  itemKey: string,
  label: string,
  options?: {
    allowedPlans?: readonly PlanCode[];
    helpText?: string;
    icon?: ReactNode;
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
    icon: options?.icon,
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
          key: "customer-admin",
          label: "",
          items: [
            {
              key: "customer-admin-workspace",
              label: "Organization",
              helpText:
                "Day-to-day home and search areas for your organization.",
              children: [
                navigationItem(
                  routeByKey,
                  "dashboard",
                  "customer-admin-home",
                  "Home",
                  {
                    helpText:
                      "Recent activity and the main organization home view.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "search",
                  "customer-admin-search",
                  "Search",
                  {
                    helpText: "Search and review nonprofit organizations.",
                    icon: createElement(IconSearch, {
                      size: 18,
                      stroke: 1.7,
                    }),
                  },
                ),
              ],
            },
            {
              key: "customer-admin-account",
              label: "Account",
              helpText:
                "Commercial, API, and settings controls for account owners.",
              children: [
                navigationItem(
                  routeByKey,
                  "team",
                  "customer-admin-team",
                  "Team",
                  {
                    helpText: "Team access and organization details.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "billing",
                  "customer-admin-billing",
                  "Billing",
                  {
                    helpText:
                      "Plan, billing actions, and subscription controls.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "usage",
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
                  "API Keys",
                  {
                    allowedPlans: ["growth", "pro", "enterprise"],
                    helpText: "Create and manage API keys for your organization.",
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
                    helpText: "Manage organization settings and preferences.",
                  },
                ),
              ],
            },
            {
              key: "customer-admin-support",
              label: "Support",
              helpText:
                "Contact support and report issues without mixing support into organization settings.",
              children: [
                navigationItem(
                  routeByKey,
                  "support",
                  "customer-admin-support-contact",
                  "Contact Support",
                  {
                    helpText:
                      "Support contact details and helpful product links.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "support",
                  "customer-admin-support-report-issue",
                  "Report An Issue",
                  {
                    helpText:
                      "Send support requests and product recommendations.",
                  },
                ),
              ],
            },
          ],
        },
      ];
    case "customer_user":
      return [
        {
          key: "customer-user",
          label: "",
          items: [
            navigationItem(
              routeByKey,
              "dashboard",
              "customer-user-dashboard",
              "Dashboard",
              {
                helpText:
                  "Review operational activity, recent verifications, and alerts.",
                icon: createElement(IconDashboard, { size: 18, stroke: 1.7 }),
              },
            ),
            {
              key: "customer-user-search",
              label: "Search",
              helpText:
                "Discover organizations by EIN or address from one place.",
              icon: createElement(IconSearch, { size: 18, stroke: 1.7 }),
              children: [
                navigationItem(
                  routeByKey,
                  "workspace",
                  "customer-user-search-ein",
                  "By EIN",
                  {
                    helpText: "Run an exact lookup using a 9-digit EIN.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "workspace",
                  "customer-user-search-address",
                  "By Address",
                  {
                    helpText:
                      "Find organizations with address details.",
                  },
                ),
              ],
            },
            {
              key: "customer-user-automation",
              label: "Automation",
              helpText:
                "Control enforcement, API keys, and OAuth credentials for automation.",
              icon: createElement(IconSettingsAutomation, {
                size: 18,
                stroke: 1.7,
              }),
              children: [
                navigationItem(
                  routeByKey,
                  "api-access",
                  "customer-user-automation-general",
                  "General",
                  {
                    helpText:
                      "Manage hard-stop enforcement for automated verification traffic.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "api-access",
                  "customer-user-automation-api",
                  "API Key",
                  {
                    helpText:
                      "Create and manage API keys for direct integrations.",
                  },
                ),
                navigationItem(
                  routeByKey,
                  "api-access",
                  "customer-user-automation-oauth",
                  "OAuth",
                  {
                    helpText:
                      "Manage generated OAuth client credentials for server-to-server access.",
                  },
                ),
              ],
            },
          ],
        },
      ];
  }
}

function resolvePortalNavigationAlias(currentHash: string): string | null {
  const query = String(currentHash || "").split("?")[1];
  const params = new URLSearchParams(query);
  const nav = params.get("nav");

  return nav?.trim() || null;
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
