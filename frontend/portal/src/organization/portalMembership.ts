import { apiEndpoints, type ApiClient, resolvePathTemplate } from "@charity-status/shared-api";
import type {
  PortalOrganizationMemberSummary,
} from "./usePortalOrganization";

export interface PortalInvitationCreateRequest {
  email: string;
  role: "admin" | "user";
}

export interface PortalInvitationCreateResponse {
  email: string;
  invitation_id: string;
  organization_id: string;
  role: string;
  status: string;
  token: string;
}

export interface PortalOrganizationInvitationSummary {
  accepted_at: string | null;
  created_at: string;
  email: string;
  expires_at: string;
  invitation_id: string;
  invited_by_user_id: string | null;
  role: string;
  status: "accepted" | "expired" | "pending";
}

export interface PortalMemberUpdateRequest {
  role?: "admin" | "user";
  status?: "active" | "invited" | "suspended";
}

export interface PortalMemberRemovalResponse {
  organization_id: string;
  removed_member_id: string;
}

export interface PortalMembershipClient {
  inviteMember(
    request: PortalInvitationCreateRequest,
  ): Promise<PortalInvitationCreateResponse>;
  listInvitations(): Promise<PortalOrganizationInvitationSummary[]>;
  listMembers(): Promise<PortalOrganizationMemberSummary[]>;
  removeMember(memberId: string): Promise<PortalMemberRemovalResponse>;
  updateMember(
    memberId: string,
    request: PortalMemberUpdateRequest,
  ): Promise<PortalOrganizationMemberSummary>;
}

export function createPortalMembershipClient(
  apiClient: ApiClient,
): PortalMembershipClient {
  return {
    inviteMember(request) {
      return apiClient.post<
        PortalInvitationCreateResponse,
        PortalInvitationCreateRequest
      >(apiEndpoints.organization.currentInvitations, {
        body: request,
      });
    },
    async listInvitations() {
      const payload = await apiClient.get<{ items: PortalOrganizationInvitationSummary[] }>(
        apiEndpoints.organization.currentInvitations,
      );
      return payload.items;
    },
    async listMembers() {
      const payload = await apiClient.get<{ items: PortalOrganizationMemberSummary[] }>(
        apiEndpoints.organization.currentMembers,
      );
      return payload.items;
    },
    removeMember(memberId) {
      return apiClient.delete<PortalMemberRemovalResponse>(
        resolvePathTemplate(apiEndpoints.organization.deleteCurrentMember.path, {
          memberId,
        }),
      );
    },
    updateMember(memberId, request) {
      return apiClient.patch<
        PortalOrganizationMemberSummary,
        PortalMemberUpdateRequest
      >(
        resolvePathTemplate(apiEndpoints.organization.currentMember.path, {
          memberId,
        }),
        {
          body: request,
        },
      );
    },
  };
}
