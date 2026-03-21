import { createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { PortalOrganization } from "../organization/portalOrganization";
import type { PortalAuthenticatedSession } from "./portalSession";

type PortalApiRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

interface CreatePortalApiClientOptions {
  fetchImpl?: typeof fetch;
  organization?: Pick<PortalOrganization, "account_id" | "workspace_id"> | null;
  runtimeConfig: PortalApiRuntimeConfig;
  session: PortalAuthenticatedSession;
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
