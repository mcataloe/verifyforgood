import type { PlanCode } from "@charity-status/shared-types";
import type { VerifyForGoodNavigationSection } from "@charity-status/shared-ui";
import type { PortalNavigationAudience } from "./portalNavigation";
import type { PortalPageKey, PortalRouteDefinition } from "./portalRoutes";

type RouteMap = {
  get(page: PortalPageKey): PortalRouteDefinition | undefined;
};

function item(
  routes: RouteMap,
  page: PortalPageKey,
  key: string,
  label: string,
  options?: { allowedPlans?: readonly PlanCode[]; helpText?: string },
) {
  const route = routes.get(page);
  if (!route || route.access !== "protected") {
    throw new Error(`Missing protected portal page "${page}".`);
  }
  return {
    key,
    label,
    href: route.hash,
    helpText: options?.helpText ?? route.description,
    allowedPlans: options?.allowedPlans,
    visibility: {
      planRestrictedBehavior: "locked" as const,
      roleRestrictedBehavior: "hidden" as const,
    },
  };
}

export function buildAudienceNavigationSections(
  routes: RouteMap,
  audience: PortalNavigationAudience,
): VerifyForGoodNavigationSection[] {
  switch (audience) {
    case "developer":
      return [
        {
          key: "build",
          label: "Build",
          items: [
            item(routes, "dashboard", "developer-overview", "Overview"),
            item(routes, "organizations", "developer-tenants", "Organizations"),
            item(routes, "billing", "developer-plans", "Plans"),
          ],
        },
        {
          key: "controls",
          label: "Controls",
          items: [
            item(routes, "usage", "developer-audit", "Usage"),
            item(routes, "automation-api-key", "developer-system", "System"),
            item(
              routes,
              "settings-organization",
              "developer-feature-flags",
              "Settings",
            ),
          ],
        },
      ];
    case "portal_admin":
      return [
        {
          key: "operations",
          label: "Operations",
          items: [
            item(routes, "dashboard", "portal-admin-dashboard", "Dashboard"),
            item(
              routes,
              "organizations",
              "portal-admin-customers",
              "Organizations",
            ),
            item(routes, "team", "portal-admin-support", "Team"),
          ],
        },
        {
          key: "account",
          label: "Account",
          items: [
            item(routes, "billing", "portal-admin-subscriptions", "Billing"),
            item(routes, "usage", "portal-admin-reports", "Usage"),
            item(
              routes,
              "settings-organization",
              "portal-admin-settings",
              "Settings",
            ),
          ],
        },
      ];
    case "customer_admin":
      return [
        {
          key: "workspace",
          label: "Workspace",
          items: [
            item(routes, "dashboard", "customer-admin-home", "Home"),
            item(
              routes,
              "organizations",
              "customer-admin-organizations",
              "Organizations",
            ),
            item(routes, "team", "customer-admin-team", "Team"),
            {
              key: "customer-admin-support",
              label: "Support",
              helpText:
                "Contact support and report issues without mixing support into organization settings.",
              children: [
                item(
                  routes,
                  "support-contact",
                  "customer-admin-support-contact",
                  "Contact Support",
                ),
                item(
                  routes,
                  "support-report-issue",
                  "customer-admin-support-report-issue",
                  "Report An Issue",
                ),
              ],
            },
          ],
        },
        {
          key: "account",
          label: "Account",
          items: [
            item(routes, "billing", "customer-admin-billing", "Billing"),
            item(routes, "usage", "customer-admin-usage", "Usage"),
            item(routes, "automation-api-key", "customer-admin-api", "API Keys", {
              allowedPlans: ["growth", "pro", "enterprise"],
            }),
            item(
              routes,
              "settings-organization",
              "customer-admin-settings",
              "Settings",
            ),
          ],
        },
      ];
    case "customer_user":
      return [
        {
          key: "customer-user",
          label: "",
          items: [
            item(routes, "dashboard", "customer-user-dashboard", "Dashboard"),
            item(
              routes,
              "organizations",
              "customer-user-organizations",
              "Organizations",
            ),
            {
              key: "customer-user-automation",
              label: "Automation",
              helpText: "Manage automation behavior and integration access.",
              children: [
                item(
                  routes,
                  "automation-general",
                  "customer-user-automation-general",
                  "General",
                ),
                item(
                  routes,
                  "automation-api-key",
                  "customer-user-automation-api",
                  "API Keys",
                ),
                item(
                  routes,
                  "automation-oauth",
                  "customer-user-automation-oauth",
                  "OAuth",
                ),
              ],
            },
          ],
        },
      ];
  }
}
