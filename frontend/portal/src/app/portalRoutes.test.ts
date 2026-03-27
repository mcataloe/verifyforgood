import { describe, expect, it } from "vitest";
import {
  consumePortalReturnTo,
  defaultProtectedPortalRoute,
  organizationOnboardingPortalRoute,
  rememberPortalReturnTo,
  registerPortalRoute,
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
    expect(resolvePortalRoute("#/onboarding/organization")).toMatchObject({
      hash: "#/onboarding/organization",
      key: "onboarding-organization",
    });
  });

  it("ignores query parameters when resolving routes", () => {
    expect(resolvePortalRoute("#/usage-billing?tab=invoices")).toMatchObject({
      hash: "#/usage-billing",
      key: "usage-billing",
    });
  });

  it("falls back to the default protected route for unknown or empty hashes", () => {
    expect(resolvePortalRoute("")).toStrictEqual(defaultProtectedPortalRoute);
    expect(resolvePortalRoute("#/missing")).toStrictEqual(
      defaultProtectedPortalRoute,
    );
  });

  it("continues resolving the public sign-in boundary directly", () => {
    expect(resolvePortalRoute("#/sign-in")).toStrictEqual(signInPortalRoute);
    expect(resolvePortalRoute("#/register")).toStrictEqual(registerPortalRoute);
  });

  it("preserves navigation query aliases in remembered return routes", () => {
    window.sessionStorage.clear();

    rememberPortalReturnTo("#/usage-billing?nav=customer-admin-usage");

    expect(consumePortalReturnTo()).toBe(
      "#/usage-billing?nav=customer-admin-usage",
    );
  });

  it("keeps onboarding routes as protected return targets", () => {
    window.sessionStorage.clear();

    rememberPortalReturnTo(organizationOnboardingPortalRoute.hash);

    expect(consumePortalReturnTo()).toBe(
      organizationOnboardingPortalRoute.hash,
    );
  });

  it("does not store public auth routes as protected return targets", () => {
    window.sessionStorage.clear();

    rememberPortalReturnTo("#/register");

    expect(consumePortalReturnTo()).toBe(defaultProtectedPortalRoute.hash);
  });
});
