import type { PlanCode } from "@charity-status/shared-types";
import type { VerifyForGoodNavigationSection } from "@charity-status/shared-ui";
import {
  IconAdjustments,
  IconCreditCard,
  IconChartBar,
  IconHeadset,
  IconKey,
  IconLayoutDashboard,
  IconLifebuoy,
  IconLock,
  IconMessageReport,
  IconRobot,
  IconSearch,
  IconServer2,
  IconSettings,
  IconStack2,
  IconUsers,
  type IconProps,
} from "@tabler/icons-react";
import type { ComponentType } from "react";
import type { PortalNavigationAudience } from "./portalNavigation";
import type { PortalPageKey, PortalRouteDefinition } from "./portalRoutes";

type RouteMap = {
  get(page: PortalPageKey): PortalRouteDefinition | undefined;
};

type TablerIconComponent = ComponentType<IconProps>;

const NAV_ICON_SIZE = 20;
const NAV_ICON_STROKE = 1.75;

function navIcon(IconComponent: TablerIconComponent) {
  return <IconComponent aria-hidden="true" size={NAV_ICON_SIZE} stroke={NAV_ICON_STROKE} />;
}

function item(
  routes: RouteMap,
  page: PortalPageKey,
  key: string,
  label: string,
  options?: {
    allowedPlans?: readonly PlanCode[];
    helpText?: string;
    icon?: TablerIconComponent;
  },
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
    icon: options?.icon ? navIcon(options.icon) : undefined,
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
            item(routes, "dashboard", "developer-overview", "Dashboard", {
              icon: IconLayoutDashboard,
            }),
            item(routes, "organizations", "developer-tenants", "Search Nonprofits", {
              icon: IconSearch,
            }),
            item(routes, "billing", "developer-plans", "Plans", {
              icon: IconStack2,
            }),
          ],
        },
        {
          key: "controls",
          label: "Controls",
          items: [
            item(routes, "usage", "developer-audit", "Usage", {
              icon: IconChartBar,
            }),
            item(routes, "automation-api-key", "developer-system", "System", {
              icon: IconServer2,
            }),
            item(
              routes,
              "settings-organization",
              "developer-feature-flags",
              "Settings",
              { icon: IconSettings },
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
            item(routes, "dashboard", "portal-admin-dashboard", "Dashboard", {
              icon: IconLayoutDashboard,
            }),
            item(
              routes,
              "organizations",
              "portal-admin-customers",
              "Search Nonprofits",
              { icon: IconSearch },
            ),
            item(routes, "team", "portal-admin-support", "Team", {
              icon: IconUsers,
            }),
          ],
        },
        {
          key: "account",
          label: "Account",
          items: [
            item(routes, "billing", "portal-admin-subscriptions", "Billing", {
              icon: IconCreditCard,
            }),
            item(routes, "usage", "portal-admin-reports", "Usage", {
              icon: IconChartBar,
            }),
            item(
              routes,
              "settings-organization",
              "portal-admin-settings",
              "Settings",
              { icon: IconSettings },
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
            item(routes, "dashboard", "customer-admin-home", "Dashboard", {
              icon: IconLayoutDashboard,
            }),
            item(
              routes,
              "organizations",
              "customer-admin-organizations",
              "Search Nonprofits",
              { icon: IconSearch },
            ),
            item(routes, "team", "customer-admin-team", "Team", {
              icon: IconUsers,
            }),
            {
              key: "customer-admin-support",
              label: "Support",
              helpText:
                "Contact support and report issues without mixing support into organization settings.",
              icon: navIcon(IconLifebuoy),
              children: [
                item(
                  routes,
                  "support-contact",
                  "customer-admin-support-contact",
                  "Contact Support",
                  { icon: IconHeadset },
                ),
                item(
                  routes,
                  "support-report-issue",
                  "customer-admin-support-report-issue",
                  "Feedback",
                  { icon: IconMessageReport },
                ),
              ],
            },
          ],
        },
        {
          key: "account",
          label: "Account",
          items: [
            item(routes, "billing", "customer-admin-billing", "Billing", {
              icon: IconCreditCard,
            }),
            item(routes, "usage", "customer-admin-usage", "Usage", {
              icon: IconChartBar,
            }),
            item(routes, "automation-api-key", "customer-admin-api", "API Keys", {
              allowedPlans: ["growth", "pro", "enterprise"],
              icon: IconKey,
            }),
            item(
              routes,
              "settings-organization",
              "customer-admin-settings",
              "Settings",
              { icon: IconSettings },
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
            item(routes, "dashboard", "customer-user-dashboard", "Dashboard", {
              icon: IconLayoutDashboard,
            }),
            item(
              routes,
              "organizations",
              "customer-user-organizations",
              "Search Nonprofits",
              { icon: IconSearch },
            ),
            {
              key: "customer-user-automation",
              label: "Automation",
              helpText: "Manage automation behavior and integration access.",
              icon: navIcon(IconRobot),
              children: [
                item(
                  routes,
                  "automation-general",
                  "customer-user-automation-general",
                  "General",
                  { icon: IconAdjustments },
                ),
                item(
                  routes,
                  "automation-api-key",
                  "customer-user-automation-api",
                  "API Keys",
                  { icon: IconKey },
                ),
                item(
                  routes,
                  "automation-oauth",
                  "customer-user-automation-oauth",
                  "OAuth",
                  { icon: IconLock },
                ),
              ],
            },
          ],
        },
      ];
  }
}
