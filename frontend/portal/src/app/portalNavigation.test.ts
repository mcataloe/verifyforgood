import { describe, expect, it } from "vitest";
import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
} from "@charity-status/shared-types";
import {
  buildPortalNavigationSections,
  resolvePortalNavigation,
} from "./portalNavigation";
import { portalProtectedRoutes } from "./portalRoutes";

describe("portal navigation config", () => {
  it("builds grouped navigation from protected route hashes", () => {
    const sections = buildPortalNavigationSections(portalProtectedRoutes);

    expect(sections.map((section) => section.key)).toEqual([
      "review",
      "organization",
      "build",
      "account",
    ]);
    expect(sections[0]?.items[0]).toMatchObject({
      href: "#/dashboard",
      key: "dashboard",
      label: "Dashboard",
    });
    expect(sections[1]?.items[1]).toMatchObject({
      href: "#/settings",
      key: "settings",
      label: "Settings",
    });
  });

  it("keeps customer-user navigation focused on review work", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      }),
    ).toEqual([
      {
        items: ["Dashboard"],
        label: "Review",
      },
    ]);
  });

  it("gives customer admins organization, build, and account controls", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard"],
        label: "Review",
      },
      {
        items: ["Overview", "Settings"],
        label: "Organization",
      },
      {
        items: ["API"],
        label: "Build",
      },
      {
        items: ["Billing"],
        label: "Account",
      },
    ]);
  });

  it("keeps portal admins aligned to the admin-oriented customer information architecture", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
      }),
    ).toEqual([
      {
        items: ["Dashboard"],
        label: "Review",
      },
      {
        items: ["Overview", "Settings"],
        label: "Organization",
      },
      {
        items: ["API"],
        label: "Build",
      },
      {
        items: ["Billing"],
        label: "Account",
      },
    ]);
  });

  it("gives developers a narrower build-oriented navigation set", () => {
    expect(
      summarizeSections({
        plan: "growth",
        roles: [FRONTEND_ACCESS_ROLE.developer],
      }),
    ).toEqual([
      {
        items: ["Dashboard"],
        label: "Review",
      },
      {
        items: ["Overview"],
        label: "Organization",
      },
      {
        items: ["API"],
        label: "Build",
      },
    ]);
  });

  it("keeps discoverable plan-gated items locked for lower plans", () => {
    const sections = resolvePortalNavigation({
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    const buildSection = sections.find((section) => section.key === "build");
    const apiItem = buildSection?.items.find((item) => item.key === "api-access");

    expect(buildSection?.label).toBe("Build");
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
