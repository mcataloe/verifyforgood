export const FRONTEND_ACCESS_ROLES = [
  "developer",
  "portal_admin",
  "customer_admin",
  "customer_user",
] as const;

export type FrontendAccessRole = (typeof FRONTEND_ACCESS_ROLES)[number];

export const FRONTEND_ACCESS_ROLE = {
  customerAdmin: "customer_admin",
  customerUser: "customer_user",
  developer: "developer",
  portalAdmin: "portal_admin",
} as const satisfies Record<string, FrontendAccessRole>;

export function isFrontendAccessRole(
  value: unknown,
): value is FrontendAccessRole {
  return (
    typeof value === "string" &&
    FRONTEND_ACCESS_ROLES.includes(value as FrontendAccessRole)
  );
}
