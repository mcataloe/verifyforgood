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
    expect(sections[1]?.items[1]).toMatchObject({
      href: "#/api-access",
      key: "api-access",
      label: "API",
      helpText:
        "Self-serve API credentials and token access. Available on Growth and higher plans.",
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

  it("keeps discoverable plan-gated items locked for lower plans", () => {
    const sections = resolvePortalNavigation({
      plan: "free",
      roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
      routes: portalProtectedRoutes,
    });
    const apiItem = sections
      .flatMap((section) => section.items)
      .find((item) => item.key === "api-access");

    expect(apiItem).toMatchObject({
      key: "api-access",
      label: "API",
      visibilityState: "locked",
    });
    expect(apiItem?.href).toBeUndefined();
  });
});
