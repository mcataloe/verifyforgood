import { createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { OrganizationContextValue } from "../organization";
import type {
  PortalOrganization,
  PortalOrganizationSessionScope,
} from "../organization/portalOrganization";

type PortalApiRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

interface CreatePortalApiClientOptions {
  accessToken?: string | null;
  context?: Pick<OrganizationContextValue, "activeOrganization"> | null;
  fetchImpl?: typeof fetch;
  organization?: Pick<PortalOrganization, "account_id" | "workspace_id"> | null;
  runtimeConfig: PortalApiRuntimeConfig;
  session: Pick<PortalOrganizationSessionScope, "account_id" | "workspace_id">;
}

export function createPortalApiClient({
  accessToken,
  context,
  fetchImpl,
  organization,
  runtimeConfig,
  session,
}: CreatePortalApiClientOptions): ApiClient {
  const activeScope = context?.activeOrganization ?? organization ?? session;

  return createApiClient({
    credentials: "include",
    fetchImpl,
    headersProvider: async () => ({
      ...(accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : {}),
      "X-Portal-Account-Id": activeScope.account_id,
      "X-Portal-Workspace-Id": activeScope.workspace_id,
    }),
    runtimeConfig,
  });
}
