import type { ApiClient } from "@charity-status/shared-api";
import { createContext, useContext } from "react";
import type { PortalOrganization } from "./portalOrganization";

export type PortalOrganizationStatus = "loading" | "ready";

export interface PortalOrganizationContextValue {
  activeOrganization: PortalOrganization;
  apiClient: ApiClient;
  refresh: () => Promise<void>;
  status: PortalOrganizationStatus;
}

export const PortalOrganizationContext =
  createContext<PortalOrganizationContextValue | null>(null);

export function usePortalOrganization() {
  const context = useContext(PortalOrganizationContext);
  if (!context) {
    throw new Error(
      "usePortalOrganization must be used inside PortalOrganizationProvider.",
    );
  }

  return context;
}
