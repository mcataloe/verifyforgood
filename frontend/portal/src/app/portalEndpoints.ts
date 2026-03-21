import { apiEndpoints, buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface PortalEndpoints {
  billingCheckout: string;
  billingPortal: string;
  billingPlanChange: string;
  billingSubscription: string;
  nonprofitFilings: string;
  nonprofitLookup: string;
  nonprofitSearch: string;
  organizationSettings: string;
  oauthToken: string;
}

export function portalEndpoints(
  runtimeConfig: FrontendRuntimeConfig,
): PortalEndpoints {
  return {
    billingCheckout: buildApiUrl(
      apiEndpoints.billing.checkoutSession,
      runtimeConfig,
    ),
    billingPortal: buildApiUrl(
      apiEndpoints.billing.portalSession,
      runtimeConfig,
    ),
    billingPlanChange: buildApiUrl(
      apiEndpoints.billing.planChange,
      runtimeConfig,
    ),
    billingSubscription: buildApiUrl(
      apiEndpoints.billing.subscription,
      runtimeConfig,
    ),
    nonprofitFilings: buildApiUrl(
      apiEndpoints.nonprofits.filings,
      runtimeConfig,
    ),
    nonprofitLookup: buildApiUrl(apiEndpoints.nonprofits.lookup, runtimeConfig),
    nonprofitSearch: buildApiUrl(apiEndpoints.nonprofits.search, runtimeConfig),
    organizationSettings: buildApiUrl(
      apiEndpoints.organization.settings,
      runtimeConfig,
    ),
    oauthToken: buildApiUrl(apiEndpoints.auth.oauthToken, runtimeConfig),
  };
}
