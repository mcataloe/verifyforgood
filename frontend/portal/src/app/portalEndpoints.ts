import { buildApiUrl } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";

export interface PortalEndpoints {
  billingCheckout: string;
  billingPortal: string;
  billingPlanChange: string;
  billingSubscription: string;
  organizationSettings: string;
  oauthToken: string;
}

export function portalEndpoints(runtimeConfig: FrontendRuntimeConfig): PortalEndpoints {
  return {
    billingCheckout: buildApiUrl("/organization/billing/checkout-session", runtimeConfig),
    billingPortal: buildApiUrl("/organization/billing/portal-session", runtimeConfig),
    billingPlanChange: buildApiUrl("/organization/billing/plan-change", runtimeConfig),
    billingSubscription: buildApiUrl("/organization/billing/subscription", runtimeConfig),
    organizationSettings: buildApiUrl("/organization/settings", runtimeConfig),
    oauthToken: buildApiUrl("/oauth/token", runtimeConfig),
  };
}
