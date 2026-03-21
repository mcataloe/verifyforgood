import { apiEndpoints, buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface DocsEndpoints {
  billingSubscription: string;
  nonprofitLookup: string;
  nonprofitSearch: string;
  oauthToken: string;
  organizationSettings: string;
  verifyBatch: string;
}

export function docsEndpoints(
  runtimeConfig: FrontendRuntimeConfig,
): DocsEndpoints {
  return {
    billingSubscription: buildApiUrl(
      apiEndpoints.billing.subscription,
      runtimeConfig,
    ),
    nonprofitLookup: buildApiUrl(apiEndpoints.nonprofits.lookup, runtimeConfig),
    nonprofitSearch: buildApiUrl(apiEndpoints.nonprofits.search, runtimeConfig),
    oauthToken: buildApiUrl(apiEndpoints.auth.oauthToken, runtimeConfig),
    organizationSettings: buildApiUrl(
      apiEndpoints.organization.settings,
      runtimeConfig,
    ),
    verifyBatch: buildApiUrl(
      apiEndpoints.verification.verifyBatch,
      runtimeConfig,
    ),
  };
}
