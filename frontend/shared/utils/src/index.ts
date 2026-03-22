import type { FrontendSurface } from "@charity-status/shared-types";
export {
  hasAllRoles,
  hasAnyRole,
  hasRole,
  isCustomerAdmin,
  isCustomerUser,
  isDeveloper,
  isPortalAdmin,
} from "./access";

export function formatSurfaceLabel(surface: FrontendSurface): string {
  if (surface === "marketing") {
    return "Marketing app";
  }
  if (surface === "portal") {
    return "Customer portal";
  }
  return "Documentation app";
}
