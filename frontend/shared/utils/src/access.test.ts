import { describe, expect, it } from "vitest";
import {
  FRONTEND_ACCESS_ROLE,
  isFrontendAccessRole,
} from "@charity-status/shared-types";
import {
  hasAllRoles,
  hasAnyRole,
  hasRole,
  isCustomerAdmin,
  isCustomerUser,
  isDeveloper,
  isPortalAdmin,
} from "./access";

describe("shared access helpers", () => {
  const roles = [
    FRONTEND_ACCESS_ROLE.customerAdmin,
    FRONTEND_ACCESS_ROLE.customerUser,
  ] as const;

  it("checks direct membership and compound membership consistently", () => {
    expect(hasRole(roles, FRONTEND_ACCESS_ROLE.customerAdmin)).toBe(true);
    expect(hasRole(roles, FRONTEND_ACCESS_ROLE.portalAdmin)).toBe(false);
    expect(
      hasAnyRole(roles, [
        FRONTEND_ACCESS_ROLE.portalAdmin,
        FRONTEND_ACCESS_ROLE.customerUser,
      ]),
    ).toBe(true);
    expect(
      hasAllRoles(roles, [
        FRONTEND_ACCESS_ROLE.customerAdmin,
        FRONTEND_ACCESS_ROLE.customerUser,
      ]),
    ).toBe(true);
    expect(
      hasAllRoles(roles, [
        FRONTEND_ACCESS_ROLE.customerAdmin,
        FRONTEND_ACCESS_ROLE.developer,
      ]),
    ).toBe(false);
  });

  it("provides role-specific helper checks", () => {
    expect(isDeveloper(roles)).toBe(false);
    expect(isPortalAdmin(roles)).toBe(false);
    expect(isCustomerAdmin(roles)).toBe(true);
    expect(isCustomerUser(roles)).toBe(true);
  });

  it("exposes a canonical runtime role validator", () => {
    expect(isFrontendAccessRole(FRONTEND_ACCESS_ROLE.developer)).toBe(true);
    expect(isFrontendAccessRole("workspace_owner")).toBe(false);
  });
});
