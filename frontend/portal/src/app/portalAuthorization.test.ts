import { describe, expect, it } from "vitest";
import { resolveRouteAuthorization } from "./portalAuthorization";
import { resolvePortalRoute } from "./portalRoutes";

describe("portalAuthorization", () => {
  it("allows admins to access admin-only customer routes", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_admin",
        currentHash: "#/usage",
        currentRoute: resolvePortalRoute("#/usage"),
        membershipRole: "admin",
      }),
    ).toEqual({
      allowed: true,
      redirectHash: null,
    });
  });

  it("denies non-admin customer admins on admin-only routes", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_admin",
        currentHash: "#/usage",
        currentRoute: resolvePortalRoute("#/usage"),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: false,
      redirectHash: "#/dashboard?nav=customer-admin-home",
    });
  });

  it("allows non-admin customer admins onto user-level routes", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_admin",
        currentHash: "#/team",
        currentRoute: resolvePortalRoute("#/team"),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: true,
      redirectHash: null,
    });
  });

  it("does not apply membership-role gating to other audiences", () => {
    expect(
      resolveRouteAuthorization({
        audience: "portal_admin",
        currentHash: "#/api-access?nav=customer-user-automation-api",
        currentRoute: resolvePortalRoute(
          "#/api-access?nav=customer-user-automation-api",
        ),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: true,
      redirectHash: null,
    });
  });

  it("allows customer users on customer-user route aliases", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_user",
        currentHash: "#/api-access?nav=customer-user-automation-api",
        currentRoute: resolvePortalRoute(
          "#/api-access?nav=customer-user-automation-api",
        ),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: true,
      redirectHash: null,
    });
  });

  it("denies customer users who manually enter customer-admin route aliases", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_user",
        currentHash: "#/api-access?nav=customer-admin-api",
        currentRoute: resolvePortalRoute("#/api-access?nav=customer-admin-api"),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: false,
      redirectHash: null,
    });
  });

  it("denies customer users who manually enter customer-admin route surfaces", () => {
    expect(
      resolveRouteAuthorization({
        audience: "customer_user",
        currentHash: "#/billing",
        currentRoute: resolvePortalRoute("#/billing"),
        membershipRole: "user",
      }),
    ).toEqual({
      allowed: false,
      redirectHash: null,
    });
  });
});
