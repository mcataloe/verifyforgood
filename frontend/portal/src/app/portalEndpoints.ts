import { apiEndpoints, buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface PortalEndpoints {
  authLogin: string;
  authMe: string;
  authRegister: string;
  billingCheckout: string;
  billingPortal: string;
  billingPlanChange: string;
  billingSubscription: string;
  nonprofitFilings: string;
  nonprofitLookup: string;
  nonprofitSearch: string;
  organizationCreate: string;
  organizationActivity?: string;
  organizationDeleteCurrent: string;
  organizationSettings: string;
  organizationSupport?: string;
  organizationSupportRequests?: string;
  organizationUsage?: string;
  oauthToken: string;
}

export function portalEndpoints(
  runtimeConfig: FrontendRuntimeConfig,
): PortalEndpoints {
  return {
    authLogin: buildApiUrl(apiEndpoints.auth.login, runtimeConfig),
    authMe: buildApiUrl(apiEndpoints.auth.me, runtimeConfig),
    authRegister: buildApiUrl(apiEndpoints.auth.register, runtimeConfig),
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
    organizationCreate: buildApiUrl(
      apiEndpoints.organization.create,
      runtimeConfig,
    ),
    organizationActivity: buildApiUrl(
      apiEndpoints.organization.activity,
      runtimeConfig,
    ),
    organizationDeleteCurrent: buildApiUrl(
      apiEndpoints.organization.deleteCurrent,
      runtimeConfig,
    ),
    organizationSettings: buildApiUrl(
      apiEndpoints.organization.settings,
      runtimeConfig,
    ),
    organizationSupport: buildApiUrl(
      apiEndpoints.organization.support,
      runtimeConfig,
    ),
    organizationSupportRequests: buildApiUrl(
      apiEndpoints.organization.supportRequests,
      runtimeConfig,
    ),
    organizationUsage: buildApiUrl(
      apiEndpoints.organization.usage,
      runtimeConfig,
    ),
    oauthToken: buildApiUrl(apiEndpoints.auth.oauthToken, runtimeConfig),
  };
}
