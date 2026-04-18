import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";

export interface PortalOrganizationSupportContext {
  support_contact: {
    brand_name: string;
    homepage_url: string;
    support_email: string;
    support_mailto: string;
  };
  account_context: {
    account_id: string | null;
    contact_email: string | null;
    current_plan: string | null;
    membership_role: string | null;
    organization_id: string | null;
    organization_name: string | null;
    workspace_id: string | null;
  };
  issue_reporting: {
    delivery_mode: "recorded_only";
    honesty_notice: string;
    urgent_contact_notice: string;
  };
  product_links: {
    api_access_hash: string;
    billing_hash: string;
    homepage_url: string;
    usage_hash: string;
  };
}

export interface PortalSupportRequestInput {
  category:
    | "account_access"
    | "billing"
    | "api"
    | "data_quality"
    | "nonprofit_access"
    | "recommendation"
    | "settings"
    | "other";
  context?: {
    current_route_hash?: string | null;
    user_agent?: string | null;
  };
  description: string;
  reply_email?: string | null;
  subject: string;
}

export interface PortalSupportRequestReceipt {
  delivery_mode: "recorded_only";
  status: "received";
  submitted_at: string;
  support_email: string;
  support_request_id: string;
}

export interface PortalSupportService {
  getSupportContext: () => Promise<PortalOrganizationSupportContext>;
  submitSupportRequest: (
    input: PortalSupportRequestInput,
  ) => Promise<PortalSupportRequestReceipt>;
}

export function createPortalSupportService(
  apiClient: ApiClient,
): PortalSupportService {
  return {
    getSupportContext() {
      return apiClient.get<PortalOrganizationSupportContext>(
        apiEndpoints.organization.support,
      );
    },
    submitSupportRequest(input) {
      return apiClient.post<
        PortalSupportRequestReceipt,
        PortalSupportRequestInput
      >(apiEndpoints.organization.supportRequests, {
        body: input,
      });
    },
  };
}
