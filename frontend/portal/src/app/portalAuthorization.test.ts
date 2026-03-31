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

  it("redirects non-admin customer admins away from admin-only routes", () => {
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
});
