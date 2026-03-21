import { createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type {
  PortalOrganization,
  PortalOrganizationSessionScope,
} from "../organization/portalOrganization";

type PortalApiRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

interface CreatePortalApiClientOptions {
  fetchImpl?: typeof fetch;
  organization?: Pick<PortalOrganization, "account_id" | "workspace_id"> | null;
  runtimeConfig: PortalApiRuntimeConfig;
  session: Pick<PortalOrganizationSessionScope, "account_id" | "workspace_id">;
}

export function createPortalApiClient({
  fetchImpl,
  organization,
  runtimeConfig,
  session,
}: CreatePortalApiClientOptions): ApiClient {
  const activeScope = organization ?? session;

  return createApiClient({
    fetchImpl,
    headersProvider: async () => ({
      "X-Portal-Account-Id": activeScope.account_id,
      "X-Portal-Workspace-Id": activeScope.workspace_id,
    }),
    runtimeConfig,
  });
}
