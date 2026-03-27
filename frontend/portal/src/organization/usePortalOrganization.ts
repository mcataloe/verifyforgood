import type { ApiClient } from "@charity-status/shared-api";
import { createContext, useContext } from "react";
import type { PortalOrganizationMembership } from "../app/portalSession";
import type { PortalOrganization } from "./portalOrganization";

export type PortalOrganizationStatus = "loading" | "ready";
export type PortalOrganizationMembersStatus = "idle" | "loading" | "ready";

export interface PortalOrganizationMemberSummary {
  created_at: string;
  email: string | null;
  full_name: string | null;
  role: string;
  status: string;
  updated_at: string;
  user_id: string;
}

export interface PortalOrganizationContextValue {
  activeOrganization: PortalOrganization;
  apiClient: ApiClient;
  currentMembership: PortalOrganizationMembership | null;
  members: PortalOrganizationMemberSummary[];
  membersStatus: PortalOrganizationMembersStatus;
  refreshMembers: () => Promise<PortalOrganizationMemberSummary[]>;
  setMembers: (members: PortalOrganizationMemberSummary[]) => void;
  setActiveOrganization: (organization: PortalOrganization) => void;
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
