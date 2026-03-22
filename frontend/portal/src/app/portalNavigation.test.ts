import { describe, expect, it } from "vitest";
import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
} from "@charity-status/shared-types";
import {
  buildPortalNavigationSections,
  resolvePortalNavigation,
  resolvePortalNavigationAudience,
} from "./portalNavigation";
import { portalProtectedRoutes } from "./portalRoutes";

describe("portal navigation config", () => {
  it("builds customer-admin sections from canonical protected route hashes", () => {
    const sections = buildPortalNavigationSections(
      portalProtectedRoutes,
      "customer_admin",
    );

    expect(sections.map((section) => section.key)).toEqual([
      "workspace",
      "account",
    ]);
    expect(sections[0]?.items[0]).toMatchObject({
      href: "#/dashboard",
      key: "dashboard",
      label: "Home",
    });
    expect(sections[1]?.items[1]).toMatchObject({
      href: "#/api-access",
      key: "api-access",
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
        items: ["Home"],
        label: "Work",
      },
    ]);
  });

  it("maps customer admins to the workspace and account information architecture", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Home", "Team"],
        label: "Workspace",
      },
      {
        items: ["Billing", "API", "Settings"],
        label: "Account",
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
        items: ["Dashboard", "Customers"],
        label: "Operations",
      },
      {
        items: ["Subscriptions"],
        label: "Commercial",
      },
      {
        items: ["Settings"],
        label: "Admin",
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
        items: ["Overview", "Tenants"],
        label: "Platform",
      },
      {
        items: ["System"],
        label: "System",
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
    expect(sections[0]?.label).toBe("Work");
  });

  it("keeps discoverable plan-gated API access locked for lower-tier customer admins", () => {
    const sections = resolvePortalNavigation({
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    const accountSection = sections.find((section) => section.key === "account");
    const apiItem = accountSection?.items.find((item) => item.key === "api-access");

    expect(accountSection?.label).toBe("Account");
    expect(apiItem).toMatchObject({
      key: "api-access",
      label: "API",
      visibilityState: "locked",
    });
    expect(apiItem?.href).toBeUndefined();
  });
});

function summarizeSections(params: {
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
