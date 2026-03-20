import type { FrontendSurface } from "@charity-status/shared-types";

export function formatSurfaceLabel(surface: FrontendSurface): string {
  if (surface === "marketing") {
    return "Marketing app";
  }
  if (surface === "portal") {
    return "Customer portal";
  }
  return "Documentation app";
}
