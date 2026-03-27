import type { ApiClient } from "@charity-status/shared-api";
import { createContext, useContext } from "react";
import type { PortalOrganizationMembership } from "../app/portalSession";
import type { PortalOrganization } from "./portalOrganization";

export type OrganizationStatus = "loading" | "ready";
export type OrganizationMembersStatus = "idle" | "loading" | "ready";
export type OrganizationSelectionStatus = "active" | "pending";

export interface OrganizationMemberSummary {
  created_at: string;
  email: string | null;
  full_name: string | null;
  role: string;
  status: string;
  updated_at: string;
  user_id: string;
}

export interface OrganizationContextValue {
  activeOrganization: PortalOrganization;
  apiClient: ApiClient;
  currentMembership: PortalOrganizationMembership | null;
  isTenantReady: boolean;
  members: OrganizationMemberSummary[];
  membersStatus: OrganizationMembersStatus;
  refresh: () => Promise<void>;
  refreshMembers: () => Promise<OrganizationMemberSummary[]>;
  selectionStatus: OrganizationSelectionStatus;
  setActiveOrganization: (organization: PortalOrganization) => void;
  setMembers: (members: OrganizationMemberSummary[]) => void;
  status: OrganizationStatus;
}

export const OrganizationContext =
  createContext<OrganizationContextValue | null>(null);

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error("useOrganization must be used inside OrganizationProvider.");
  }

  return context;
}
