import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";

export interface PortalOrganizationActivityActor {
  display_name: string | null;
  email: string | null;
  user_id: string | null;
}

export interface PortalOrganizationActivityItem {
  activity_id: string;
  actor: PortalOrganizationActivityActor;
  category: string;
  description: string;
  event_type: string;
  metadata: Record<string, unknown>;
  occurred_at: string;
  target: PortalOrganizationActivityActor;
  title: string;
}

export interface PortalOrganizationActivityPage {
  has_more: boolean;
  items: PortalOrganizationActivityItem[];
  next_cursor: string | null;
}

export interface PortalActivityService {
  listActivity(input?: {
    cursor?: string | null;
    limit?: number;
  }): Promise<PortalOrganizationActivityPage>;
}

export function createPortalActivityService(
  apiClient: ApiClient,
): PortalActivityService {
  return {
    listActivity(input = {}) {
      return apiClient.get<PortalOrganizationActivityPage>(
        apiEndpoints.organization.activity,
        {
          query: {
            ...(input.cursor ? { cursor: input.cursor } : {}),
            ...(typeof input.limit === "number" ? { limit: input.limit } : {}),
          },
        },
      );
    },
  };
}
