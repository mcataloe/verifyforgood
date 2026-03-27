import { defineEndpoint } from "./routes";

export const authEndpoints = {
  login: defineEndpoint("POST", "/auth/login", {
    name: "authLogin",
  }),
  me: defineEndpoint("GET", "/auth/me", {
    name: "authMe",
  }),
  oauthToken: defineEndpoint("POST", "/oauth/token", {
    name: "oauthToken",
  }),
  register: defineEndpoint("POST", "/auth/register", {
    name: "authRegister",
  }),
} as const;

export const publicEndpoints = {
  plans: defineEndpoint("GET", "/plans", {
    name: "publicPlans",
  }),
} as const;

export const organizationEndpoints = {
  create: defineEndpoint("POST", "/organizations", {
    name: "createOrganization",
  }),
  currentInvitations: defineEndpoint("POST", "/organizations/current/invitations", {
    name: "currentOrganizationInvitations",
  }),
  currentMembers: defineEndpoint("GET", "/organizations/current/members", {
    name: "currentOrganizationMembers",
  }),
  currentMember: defineEndpoint(
    "PATCH",
    "/organizations/current/members/{memberId}",
    {
      name: "currentOrganizationMember",
    },
  ),
  deleteCurrentMember: defineEndpoint(
    "DELETE",
    "/organizations/current/members/{memberId}",
    {
      name: "deleteCurrentOrganizationMember",
    },
  ),
  settings: defineEndpoint("GET", "/organization/settings", {
    name: "organizationSettings",
  }),
  updateSettings: defineEndpoint("PUT", "/organization/settings", {
    name: "updateOrganizationSettings",
  }),
} as const;

export const billingEndpoints = {
  checkoutSession: defineEndpoint(
    "POST",
    "/organization/billing/checkout-session",
    {
      name: "billingCheckoutSession",
    },
  ),
  planChange: defineEndpoint("POST", "/organization/billing/plan-change", {
    name: "billingPlanChange",
  }),
  portalSession: defineEndpoint(
    "POST",
    "/organization/billing/portal-session",
    {
      name: "billingPortalSession",
    },
  ),
  subscription: defineEndpoint("GET", "/organization/billing/subscription", {
    name: "billingSubscription",
  }),
} as const;

export const nonprofitEndpoints = {
  filings: defineEndpoint("GET", "/nonprofit/{ein}/filings", {
    name: "nonprofitFilings",
  }),
  lookup: defineEndpoint("GET", "/nonprofit/{ein}", {
    name: "nonprofitLookup",
  }),
  search: defineEndpoint("GET", "/nonprofits/search", {
    name: "nonprofitSearch",
  }),
  sources: defineEndpoint("GET", "/nonprofits/{ein}/sources", {
    name: "nonprofitSources",
  }),
} as const;

export const verificationEndpoints = {
  verify: defineEndpoint("POST", "/verify", {
    name: "verification",
  }),
  verifyBatch: defineEndpoint("POST", "/verify/batch", {
    name: "verificationBatch",
  }),
} as const;

export const apiEndpoints = {
  auth: authEndpoints,
  billing: billingEndpoints,
  nonprofits: nonprofitEndpoints,
  organization: organizationEndpoints,
  public: publicEndpoints,
  verification: verificationEndpoints,
} as const;
