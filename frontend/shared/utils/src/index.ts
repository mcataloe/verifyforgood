import type { FrontendSurface } from "@charity-status/shared-types";

export function formatSurfaceLabel(surface: FrontendSurface): string {
  return surface === "marketing" ? "Marketing app" : "Customer portal";
}
