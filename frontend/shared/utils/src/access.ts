import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
} from "@charity-status/shared-types";

export function hasRole(
  roles: readonly FrontendAccessRole[],
  role: FrontendAccessRole,
): boolean {
  return roles.includes(role);
}

export function hasAnyRole(
  roles: readonly FrontendAccessRole[],
  requiredRoles: readonly FrontendAccessRole[],
): boolean {
  return requiredRoles.some((role) => hasRole(roles, role));
}

export function hasAllRoles(
  roles: readonly FrontendAccessRole[],
  requiredRoles: readonly FrontendAccessRole[],
): boolean {
  return requiredRoles.every((role) => hasRole(roles, role));
}

export function isDeveloper(roles: readonly FrontendAccessRole[]): boolean {
  return hasRole(roles, FRONTEND_ACCESS_ROLE.developer);
}

export function isPortalAdmin(roles: readonly FrontendAccessRole[]): boolean {
  return hasRole(roles, FRONTEND_ACCESS_ROLE.portalAdmin);
}

export function isCustomerAdmin(roles: readonly FrontendAccessRole[]): boolean {
  return hasRole(roles, FRONTEND_ACCESS_ROLE.customerAdmin);
}

export function isCustomerUser(roles: readonly FrontendAccessRole[]): boolean {
  return hasRole(roles, FRONTEND_ACCESS_ROLE.customerUser);
}
