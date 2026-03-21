import { apiEndpoints, buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface MarketingEndpoints {
  filings: string;
  nonprofitSearch: string;
  nonprofitVerify: string;
  oauthToken: string;
  sources: string;
}

export function marketingEndpoints(
  runtimeConfig: FrontendRuntimeConfig,
): MarketingEndpoints {
  return {
    filings: buildApiUrl(apiEndpoints.nonprofits.filings, runtimeConfig),
    nonprofitSearch: buildApiUrl(apiEndpoints.nonprofits.search, runtimeConfig),
    nonprofitVerify: buildApiUrl(
      apiEndpoints.verification.verify,
      runtimeConfig,
    ),
    oauthToken: buildApiUrl(apiEndpoints.auth.oauthToken, runtimeConfig),
    sources: buildApiUrl(apiEndpoints.nonprofits.sources, runtimeConfig),
  };
}
