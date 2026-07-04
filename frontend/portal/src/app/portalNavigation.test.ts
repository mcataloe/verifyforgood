import { describe, expect, it } from "vitest";
import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
} from "@charity-status/shared-types";
import {
  buildPortalNavigationSections,
  resolveActivePortalNavigationKey,
  resolvePortalNavigation,
  resolvePortalNavigationAudience,
} from "./portalNavigation";
import { portalProtectedRoutes, resolvePortalRoute } from "./portalRoutes";

describe("portal navigation config", () => {
  it("builds customer-admin links from canonical page hashes", () => {
    const sections = buildPortalNavigationSections(
      portalProtectedRoutes,
      "customer_admin",
    );
    expect(sections.map((section) => section.key)).toEqual([
      "workspace",
      "account",
    ]);
    expect(sections[0]?.items[1]).toMatchObject({
      href: "#/organizations",
      key: "customer-admin-organizations",
      label: "Search Nonprofits",
    });
    expect(sections[1]?.items[2]).toMatchObject({
      href: "#/automation/api-keys",
      key: "customer-admin-api",
      label: "API Keys",
    });
  });

  it("chooses one navigation audience per session", () => {
    expect(
      resolvePortalNavigationAudience([
        FRONTEND_ACCESS_ROLE.developer,
        FRONTEND_ACCESS_ROLE.portalAdmin,
      ]),
    ).toBe("developer");
    expect(
      resolvePortalNavigationAudience([FRONTEND_ACCESS_ROLE.portalAdmin]),
    ).toBe("portal_admin");
    expect(
      resolvePortalNavigationAudience([FRONTEND_ACCESS_ROLE.customerAdmin]),
    ).toBe("customer_admin");
    expect(
      resolvePortalNavigationAudience([FRONTEND_ACCESS_ROLE.customerUser]),
    ).toBe("customer_user");
  });

  it("keeps customer-user navigation task focused", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      }),
    ).toEqual([
      { items: ["Dashboard", "Search Nonprofits", "Automation"], label: "" },
    ]);
  });

  it("maps customer admins to workspace and account tasks", () => {
    expect(
      summarizeSections({
        membershipRole: "admin",
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard", "Search Nonprofits", "Team"],
        label: "Workspace",
      },
      {
        items: ["Billing", "Usage", "API Keys", "Settings"],
        label: "Account",
      },
    ]);
  });

  it("maps portal admins to operations and account tasks", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard", "Search Nonprofits", "Team"],
        label: "Operations",
      },
      { items: ["Billing", "Usage", "Settings"], label: "Account" },
    ]);
  });

  it("maps developers to platform tasks", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.developer],
      }),
    ).toEqual([
      { items: ["Dashboard", "Search Nonprofits", "Plans"], label: "Build" },
      { items: ["Usage", "System", "Settings"], label: "Controls" },
    ]);
  });

  it("keeps nested automation destinations canonical", () => {
    const sections = resolvePortalNavigation({
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerUser],
      routes: portalProtectedRoutes,
    });
    expect(sections).toHaveLength(1);
    expect(sections[0]?.items[2]?.children?.map((item) => item.href)).toEqual([
      "#/automation",
      "#/automation/api-keys",
      "#/automation/oauth",
    ]);
  });

  it("keeps plan-gated API access locked for lower-tier admins", () => {
    const sections = resolvePortalNavigation({
      membershipRole: "admin",
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    const accountSection = sections.find(
      (section) => section.key === "account",
    );
    const apiItem = accountSection?.items.find(
      (item) => item.key === "customer-admin-api",
    );
    expect(apiItem).toMatchObject({
      key: "customer-admin-api",
      label: "API Keys",
      visibilityState: "locked",
    });
    expect(apiItem?.href).toBeUndefined();
  });

  it("resolves active canonical and organization-detail navigation", () => {
    const sections = resolvePortalNavigation({
      membershipRole: "admin",
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    expect(
      resolveActivePortalNavigationKey({
        currentHash: "#/usage",
        currentRoute: resolvePortalRoute("#/usage"),
        navigationSections: sections,
      }),
    ).toBe("customer-admin-usage");
    expect(
      resolveActivePortalNavigationKey({
        currentHash: "#/organizations/123456789/sources",
        currentRoute: resolvePortalRoute("#/organizations/123456789/sources"),
        navigationSections: sections,
      }),
    ).toBe("customer-admin-organizations");
  });

  it("removes admin-only customer navigation for user memberships", () => {
    expect(
      summarizeSections({
        membershipRole: "user",
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard", "Search Nonprofits", "Team"],
        label: "Workspace",
      },
    ]);
  });
});

function summarizeSections(params: {
  membershipRole?: "admin" | "user" | null;
  organizationContextStatus?: "active" | "pending" | null;
  plan: string;
  roles: readonly FrontendAccessRole[];
}) {
  return resolvePortalNavigation({
    ...params,
    routes: portalProtectedRoutes,
  }).map((section) => ({
    label: section.label,
    items: section.items.map((item) => item.label),
  }));
}
