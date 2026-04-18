import { describe, expect, it } from "vitest";
import {
  consumePortalReturnTo,
  defaultPortalRoute,
  defaultProtectedPortalRoute,
  homePortalRoute,
  organizationOnboardingPortalRoute,
  rememberPortalReturnTo,
  registerPortalRoute,
  resolvePortalRoute,
  signInPortalRoute,
} from "./portalRoutes";

describe("portal route resolution", () => {
  it("resolves the public portal home directly", () => {
    expect(resolvePortalRoute("#/")).toStrictEqual(homePortalRoute);
  });

  it("preserves canonical protected hashes", () => {
    expect(resolvePortalRoute("#/dashboard")).toMatchObject({
      hash: "#/dashboard",
      key: "dashboard",
    });
    expect(resolvePortalRoute("#/search")).toMatchObject({
      hash: "#/search",
      key: "search",
    });
    expect(resolvePortalRoute("#/team")).toMatchObject({
      hash: "#/team",
      key: "team",
    });
    expect(resolvePortalRoute("#/support")).toMatchObject({
      hash: "#/support",
      key: "support",
    });
    expect(resolvePortalRoute("#/billing")).toMatchObject({
      hash: "#/billing",
      key: "billing",
    });
    expect(resolvePortalRoute("#/usage")).toMatchObject({
      hash: "#/usage",
      key: "usage",
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
    expect(resolvePortalRoute("#/usage?tab=invoices")).toMatchObject({
      hash: "#/usage",
      key: "usage",
    });
  });

  it("falls back to the default public route for unknown or empty hashes", () => {
    expect(resolvePortalRoute("")).toStrictEqual(defaultPortalRoute);
    expect(resolvePortalRoute("#/missing")).toStrictEqual(defaultPortalRoute);
  });

  it("continues resolving the public sign-in boundary directly", () => {
    expect(resolvePortalRoute("#/sign-in")).toStrictEqual(signInPortalRoute);
    expect(resolvePortalRoute("#/register")).toStrictEqual(registerPortalRoute);
  });

  it("preserves navigation query aliases in remembered return routes", () => {
    window.sessionStorage.clear();

    rememberPortalReturnTo("#/usage?nav=customer-admin-usage");

    expect(consumePortalReturnTo()).toBe("#/usage?nav=customer-admin-usage");
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
    rememberPortalReturnTo("#/");

    expect(consumePortalReturnTo()).toBe(defaultProtectedPortalRoute.hash);
  });
});
