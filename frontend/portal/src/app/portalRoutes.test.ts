import { describe, expect, it } from "vitest";
import {
  consumePortalReturnTo,
  defaultProtectedPortalRoute,
  rememberPortalReturnTo,
  resolvePortalRoute,
  signInPortalRoute,
} from "./portalRoutes";

describe("portal route resolution", () => {
  it("preserves canonical protected hashes", () => {
    expect(resolvePortalRoute("#/dashboard")).toMatchObject({
      hash: "#/dashboard",
      key: "dashboard",
    });
    expect(resolvePortalRoute("#/usage-billing")).toMatchObject({
      hash: "#/usage-billing",
      key: "usage-billing",
    });
  });

  it("ignores query parameters when resolving routes", () => {
    expect(resolvePortalRoute("#/usage-billing?tab=invoices")).toMatchObject({
      hash: "#/usage-billing",
      key: "usage-billing",
    });
  });

  it("falls back to the default protected route for unknown or empty hashes", () => {
    expect(resolvePortalRoute("")).toBe(defaultProtectedPortalRoute);
    expect(resolvePortalRoute("#/missing")).toBe(defaultProtectedPortalRoute);
  });

  it("continues resolving the public sign-in boundary directly", () => {
    expect(resolvePortalRoute("#/sign-in")).toBe(signInPortalRoute);
  });

  it("preserves navigation query aliases in remembered return routes", () => {
    window.sessionStorage.clear();

    rememberPortalReturnTo("#/usage-billing?nav=customer-admin-usage");

    expect(consumePortalReturnTo()).toBe(
      "#/usage-billing?nav=customer-admin-usage",
    );
  });
});
