import { describe, expect, it } from "vitest";
import { FRONTEND_ACCESS_ROLE } from "@charity-status/shared-types";
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
      "operations",
      "admin",
    ]);
    expect(sections[0]?.items[0]).toMatchObject({
      href: "#/dashboard",
      key: "dashboard",
      label: "Dashboard",
    });
    expect(sections[1]?.items[2]).toMatchObject({
      href: "#/usage-billing",
      key: "usage-billing",
      label: "Billing",
    });
  });

  it("filters admin-only items out for customer users", () => {
    const sections = resolvePortalNavigation({
      plan: "growth",
      roles: [FRONTEND_ACCESS_ROLE.customerUser],
      routes: portalProtectedRoutes,
    });
    const keys = sections.flatMap((section) => section.items).map((item) => item.key);

    expect(keys).toEqual(["dashboard"]);
  });
});
