import { buildApiUrl } from "@charity-status/shared-api";
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
    filings: buildApiUrl("/nonprofit/{ein}/filings", runtimeConfig),
    nonprofitSearch: buildApiUrl("/nonprofits/search", runtimeConfig),
    nonprofitVerify: buildApiUrl("/verify", runtimeConfig),
    oauthToken: buildApiUrl("/oauth/token", runtimeConfig),
    sources: buildApiUrl("/nonprofits/{ein}/sources", runtimeConfig),
  };
}
