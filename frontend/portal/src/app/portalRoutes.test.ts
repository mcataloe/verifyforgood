import { describe, expect, it, vi } from "vitest";
import {
  buildOrganizationPortalHash,
  consumePortalReturnTo,
  defaultPortalRoute,
  defaultProtectedPortalRoute,
  homePortalRoute,
  organizationOnboardingPortalRoute,
  rememberPortalReturnTo,
  registerPortalRoute,
  resolvePortalRoute,
  signInPortalRoute,
  navigateToPortalRoute,
} from "./portalRoutes";

describe("portal route resolution", () => {
  it("resolves canonical task routes", () => {
    expect(resolvePortalRoute("#/dashboard")).toMatchObject({
      hash: "#/dashboard",
      key: "dashboard",
      page: "dashboard",
    });
    expect(resolvePortalRoute("#/billing")).toMatchObject({
      hash: "#/billing",
      key: "usage-billing",
      page: "billing",
    });
    expect(resolvePortalRoute("#/organizations")).toMatchObject({
      hash: "#/organizations",
      key: "workspace",
      page: "organizations",
    });
  });

  it("resolves shareable organization detail sections", () => {
    expect(
      resolvePortalRoute("#/organizations/123456789/sources"),
    ).toMatchObject({
      hash: "#/organizations/123456789/sources",
      key: "workspace",
      page: "organization-detail",
      params: { ein: "123456789" },
      section: "sources",
    });
    expect(buildOrganizationPortalHash("12-3456789", "filings")).toBe(
      "#/organizations/123456789/filings",
    );
  });

  it("normalizes legacy route aliases", () => {
    expect(
      resolvePortalRoute("#/usage-billing?nav=customer-admin-usage"),
    ).toMatchObject({ hash: "#/usage", page: "usage" });
    expect(
      resolvePortalRoute("#/workspace?nav=customer-admin-team"),
    ).toMatchObject({ hash: "#/team", page: "team" });
    expect(resolvePortalRoute("#/api-access")).toMatchObject({
      hash: "#/automation",
      page: "automation-general",
    });
  });

  it("returns an honest not-found route for unknown hashes", () => {
    expect(resolvePortalRoute("#/missing")).toMatchObject({
      hash: "#/missing",
      page: "not-found",
    });
    expect(resolvePortalRoute("")).toStrictEqual(defaultProtectedPortalRoute);
  });

  it("continues resolving public routes directly", () => {
    expect(resolvePortalRoute("#/sign-in")).toStrictEqual(signInPortalRoute);
    expect(resolvePortalRoute("#/register")).toStrictEqual(registerPortalRoute);
  });

  it("stores canonical return routes instead of query aliases", () => {
    window.sessionStorage.clear();
    rememberPortalReturnTo("#/usage-billing?nav=customer-admin-usage");
    expect(consumePortalReturnTo()).toBe("#/usage");
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

  it("can replace the current hash for canonical route rewrites", () => {
    const replaceState = vi.spyOn(window.history, "replaceState");
    window.history.pushState(null, "", "#/usage-billing");

    navigateToPortalRoute("#/billing", { replace: true });

    expect(window.location.hash).toBe("#/billing");
    expect(replaceState).toHaveBeenCalledWith(
      window.history.state,
      "",
      `${window.location.pathname}${window.location.search}#/billing`,
    );
    replaceState.mockRestore();
  });
});
