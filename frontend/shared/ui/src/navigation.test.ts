import { describe, expect, it } from "vitest";
import { FRONTEND_ACCESS_ROLE } from "@charity-status/shared-types";
import { filterNavigationSections } from "./navigation/filterNavigation";
import type { VerifyForGoodNavigationSection } from "./navigation/schema";

const baseSections: VerifyForGoodNavigationSection[] = [
  {
    key: "primary",
    label: "Primary",
    items: [
      {
        key: "dashboard",
        label: "Dashboard",
        href: "#/dashboard",
      },
      {
        key: "settings",
        label: "Settings",
        href: "#/settings",
        allowedRoles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      },
      {
        key: "reports",
        label: "Reports",
        href: "#/reports",
        allowedPlans: ["growth", "pro", "enterprise"],
        visibility: {
          planRestrictedBehavior: "locked",
        },
      },
      {
        key: "benchmarking",
        label: "Benchmarking",
        href: "#/benchmarking",
        allowedPlans: ["pro", "enterprise"],
        visibility: {
          planRestrictedBehavior: "hidden",
        },
      },
      {
        key: "organizations",
        label: "Organizations",
        children: [
          {
            key: "org-list",
            label: "List",
            href: "#/organizations",
            allowedRoles: [FRONTEND_ACCESS_ROLE.customerAdmin],
          },
          {
            key: "org-profile",
            label: "Profile",
            href: "#/organization/profile",
          },
        ],
      },
      {
        key: "admin-group",
        label: "Administration",
        children: [
          {
            key: "billing",
            label: "Billing",
            href: "#/billing",
            allowedRoles: [FRONTEND_ACCESS_ROLE.customerAdmin],
          },
        ],
      },
    ],
  },
];

describe("navigation filtering helpers", () => {
  it("hides role-restricted items when roles do not match", () => {
    const sections = filterNavigationSections(baseSections, {
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerUser],
    });

    expect(flattenKeys(sections)).toContain("dashboard");
    expect(flattenKeys(sections)).not.toContain("settings");
  });

  it("locks plan-restricted items instead of hiding them when configured", () => {
    const sections = filterNavigationSections(baseSections, {
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
    });
    const reports = findItem(sections, "reports");

    expect(reports?.visibilityState).toBe("locked");
    expect(reports?.href).toBeUndefined();
  });

  it("supports hidden plan-restricted items when the schema opts out of discovery", () => {
    const sections = filterNavigationSections(baseSections, {
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
    });

    expect(flattenKeys(sections)).not.toContain("benchmarking");
  });

  it("keeps nested children that remain visible after filtering", () => {
    const sections = filterNavigationSections(baseSections, {
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerUser],
    });
    const organizations = findItem(sections, "organizations");

    expect(organizations?.children?.map((child) => child.key)).toEqual([
      "org-profile",
    ]);
  });

  it("keeps a hidden parent as a visible container when it still has visible children", () => {
    const sections = filterNavigationSections(
      [
        {
          key: "secondary",
          label: "Secondary",
          items: [
            {
              key: "parent",
              label: "Parent",
              allowedRoles: [FRONTEND_ACCESS_ROLE.customerAdmin],
              children: [
                {
                  key: "child",
                  label: "Child",
                  href: "#/child",
                },
              ],
            },
          ],
        },
      ],
      {
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    );
    const parent = findItem(sections, "parent");

    expect(parent?.visibilityState).toBe("visible");
    expect(parent?.href).toBeUndefined();
    expect(parent?.children?.map((child) => child.key)).toEqual(["child"]);
  });

  it("keeps mixed locked and visible children under the same parent", () => {
    const sections = filterNavigationSections(
      [
        {
          key: "secondary",
          label: "Secondary",
          items: [
            {
              key: "analytics",
              label: "Analytics",
              children: [
                {
                  key: "analytics-overview",
                  label: "Overview",
                  href: "#/analytics",
                },
                {
                  key: "analytics-export",
                  label: "Exports",
                  href: "#/analytics/exports",
                  allowedPlans: ["pro", "enterprise"],
                  visibility: {
                    planRestrictedBehavior: "locked",
                  },
                },
                {
                  key: "analytics-admin",
                  label: "Admin",
                  href: "#/analytics/admin",
                  allowedRoles: [FRONTEND_ACCESS_ROLE.customerAdmin],
                },
              ],
            },
          ],
        },
      ],
      {
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      },
    );
    const analytics = findItem(sections, "analytics");

    expect(analytics?.visibilityState).toBe("visible");
    expect(analytics?.children?.map((child) => [child.key, child.visibilityState])).toEqual([
      ["analytics-overview", "visible"],
      ["analytics-export", "locked"],
    ]);
  });
});

function findItem(
  sections: ReturnType<typeof filterNavigationSections>,
  key: string,
) {
  return sections.flatMap((section) => flattenItems(section.items)).find((item) => item.key === key);
}

function flattenItems(
  items: NonNullable<ReturnType<typeof filterNavigationSections>[number]>["items"],
): NonNullable<ReturnType<typeof filterNavigationSections>[number]>["items"] {
  return items.flatMap((item) => [item, ...(item.children ? flattenItems(item.children) : [])]);
}

function flattenKeys(sections: ReturnType<typeof filterNavigationSections>) {
  return sections.flatMap((section) => flattenItems(section.items)).map((item) => item.key);
}
