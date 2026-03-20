import { buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface DocsEndpoints {
  billingSubscription: string;
  nonprofitLookup: string;
  nonprofitSearch: string;
  oauthToken: string;
  organizationSettings: string;
  verifyBatch: string;
}

export function docsEndpoints(runtimeConfig: FrontendRuntimeConfig): DocsEndpoints {
  return {
    billingSubscription: buildApiUrl("/organization/billing/subscription", runtimeConfig),
    nonprofitLookup: buildApiUrl("/nonprofit/{ein}", runtimeConfig),
    nonprofitSearch: buildApiUrl("/nonprofits/search", runtimeConfig),
    oauthToken: buildApiUrl("/oauth/token", runtimeConfig),
    organizationSettings: buildApiUrl("/organization/settings", runtimeConfig),
    verifyBatch: buildApiUrl("/verify/batch", runtimeConfig),
  };
}
