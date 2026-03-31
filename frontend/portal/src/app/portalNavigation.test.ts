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
  it("builds customer-admin sections from canonical protected route hashes", () => {
    const sections = buildPortalNavigationSections(
      portalProtectedRoutes,
      "customer_admin",
    );

    expect(sections.map((section) => section.key)).toEqual(["customer-admin"]);
    expect(sections[0]?.items[0]).toMatchObject({
      key: "customer-admin-workspace",
      label: "Workspace",
    });
    expect(sections[0]?.items[0]?.children?.[0]).toMatchObject({
      href: "#/dashboard?nav=customer-admin-home",
      key: "customer-admin-home",
      label: "Home",
    });
    expect(sections[0]?.items[0]?.children?.[1]).toMatchObject({
      href: "#/search?nav=customer-admin-search",
      key: "customer-admin-search",
      label: "Search",
    });
    expect(sections[0]?.items[1]?.children?.[2]).toMatchObject({
      href: "#/api-access?nav=customer-admin-api",
      key: "customer-admin-api",
      label: "API",
    });
  });

  it("chooses one navigation audience per session instead of merging role menus", () => {
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

  it("keeps customer-user navigation focused on the current home/search surface", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      }),
    ).toEqual([
      {
        items: ["Dashboard", "Search", "Automation"],
        label: "",
      },
    ]);
  });

  it("maps customer admins to the workspace and account information architecture", () => {
    expect(
      summarizeSections({
        membershipRole: "admin",
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Workspace", "Account"],
        label: "",
      },
    ]);
  });

  it("maps portal admins to the operations and subscriptions information architecture", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard", "Customers", "Support"],
        label: "Operations",
      },
      {
        items: ["Subscriptions", "Reports"],
        label: "Revenue",
      },
      {
        items: ["Settings"],
        label: "Configure",
      },
    ]);
  });

  it("maps developers to the platform-oriented information architecture", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.developer],
      }),
    ).toEqual([
      {
        items: ["Overview", "Tenants", "Plans"],
        label: "Build",
      },
      {
        items: ["Feature Flags", "Audit", "System"],
        label: "Controls",
      },
    ]);
  });

  it("keeps sparse role outputs stable without empty placeholder sections", () => {
    const sections = resolvePortalNavigation({
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerUser],
      routes: portalProtectedRoutes,
    });

    expect(sections).toHaveLength(1);
    expect(sections[0]?.label).toBe("");
    expect(sections[0]?.items[1]?.children?.map((item) => item.label)).toEqual([
      "By EIN",
      "By Address",
    ]);
    expect(sections[0]?.items[2]?.children?.map((item) => item.label)).toEqual([
      "General",
      "API Key",
      "OAuth",
    ]);
  });

  it("keeps discoverable plan-gated API access locked for lower-tier customer admins", () => {
    const sections = resolvePortalNavigation({
      membershipRole: "admin",
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    const accountBranch = sections[0]?.items.find(
      (item) => item.key === "customer-admin-account",
    );
    const apiItem = accountBranch?.children?.find(
      (item) => item.key === "customer-admin-api",
    );

    expect(accountBranch?.label).toBe("Account");
    expect(apiItem).toMatchObject({
      key: "customer-admin-api",
      label: "API",
      visibilityState: "locked",
    });
    expect(apiItem?.href).toBeUndefined();
  });

  it("resolves the active navigation item from the current hash alias before falling back to the base route", () => {
    const sections = resolvePortalNavigation({
      membershipRole: "admin",
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });

    expect(
      resolveActivePortalNavigationKey({
        currentHash: "#/usage?nav=customer-admin-usage",
        currentRoute: resolvePortalRoute("#/usage?nav=customer-admin-usage"),
        navigationSections: sections,
      }),
    ).toBe("customer-admin-usage");
    expect(
      resolveActivePortalNavigationKey({
        currentHash: "#/billing",
        currentRoute: resolvePortalRoute("#/billing"),
        navigationSections: sections,
      }),
    ).toBe("customer-admin-billing");
  });

  it("removes admin-only customer navigation items when the membership role is user", () => {
    expect(
      summarizeSections({
        membershipRole: "user",
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Workspace"],
        label: "",
      },
    ]);
  });
});

function summarizeSections(params: {
  membershipRole?: "admin" | "user" | null;
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
