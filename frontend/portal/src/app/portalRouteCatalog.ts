import type { PortalRouteDefinition } from "./portalRoutes";

export const portalPublicRoutes: PortalRouteDefinition[] = [
  { access: "public", key: "home", page: "home", label: "Home", hash: "#/", description: "Review portal entry points." },
  { access: "public", key: "sign-in", page: "sign-in", label: "Sign In", hash: "#/sign-in", description: "Sign in to the customer portal." },
  { access: "public", key: "register", page: "register", label: "Register", hash: "#/register", description: "Create a customer portal account." },
];

export const organizationOnboardingPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "onboarding-organization", page: "onboarding-organization", label: "Create Organization", hash: "#/onboarding/organization", description: "Create the first organization context.",
};
export const dashboardPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "dashboard", page: "dashboard", label: "Dashboard", hash: "#/dashboard", description: "Review recent activity and next actions.",
};
export const organizationsPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "workspace", page: "organizations", label: "Search Nonprofits", hash: "#/organizations", description: "Search nonprofit records and open source-backed profiles.",
};
export const nonprofitSearchPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "search", page: "organizations", label: "Search Nonprofits", hash: "#/search", description: "Search nonprofit records and open source-backed profiles.",
};
export const teamPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "workspace", page: "team", label: "Team", hash: "#/team", description: "Manage organization membership and workspace access.",
};
export const supportContactPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "support", page: "support-contact", label: "Contact Support", hash: "#/support", description: "Contact support and review helpful product links.",
};
export const supportReportIssuePortalRoute: PortalRouteDefinition = {
  access: "protected", key: "support", page: "support-report-issue", label: "Feedback", hash: "#/support/report-issue", description: "Send support requests and product recommendations.",
};
export const automationGeneralPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "api-access", page: "automation-general", label: "Automation", hash: "#/automation", description: "Review automation behavior and integration access.",
};
export const automationApiKeyPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "api-access", page: "automation-api-key", label: "API Keys", hash: "#/automation/api-keys", description: "Manage organization API keys.",
};
export const automationOauthPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "api-access", page: "automation-oauth", label: "OAuth", hash: "#/automation/oauth", description: "Review OAuth client access.",
};
export const billingPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "usage-billing", page: "billing", label: "Billing", hash: "#/billing", description: "Review subscription and billing state.",
};
export const usagePortalRoute: PortalRouteDefinition = {
  access: "protected", key: "usage-billing", page: "usage", label: "Usage", hash: "#/usage", description: "Review request usage and plan limits.",
};
export const settingsProfilePortalRoute: PortalRouteDefinition = {
  access: "protected", key: "settings", page: "settings-profile", label: "Profile", hash: "#/settings/profile", description: "Manage profile and appearance preferences.",
};
export const settingsOrganizationPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "settings", page: "settings-organization", label: "Organization Settings", hash: "#/settings/organization", description: "Manage organization settings and integration defaults.",
};
export const helpPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "help", page: "help", label: "Help", hash: "#/help", description: "Get help using the VerifyForGood portal.",
};
export const helpDocumentationPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "help", page: "help-documentation", label: "Documentation", hash: "#/help/documentation", description: "Read product documentation.",
};
export const comparePlansPortalRoute: PortalRouteDefinition = {
  access: "protected", key: "usage-billing", page: "compare-plans", label: "Compare Plans", hash: "#/billing/compare-plans", description: "Compare plan features, cost, and API limits.",
};

export const portalProtectedRoutes: PortalRouteDefinition[] = [
  organizationOnboardingPortalRoute,
  dashboardPortalRoute,
  nonprofitSearchPortalRoute,
  organizationsPortalRoute,
  teamPortalRoute,
  supportContactPortalRoute,
  supportReportIssuePortalRoute,
  automationGeneralPortalRoute,
  automationApiKeyPortalRoute,
  automationOauthPortalRoute,
  billingPortalRoute,
  usagePortalRoute,
  settingsProfilePortalRoute,
  settingsOrganizationPortalRoute,
  helpPortalRoute,
  helpDocumentationPortalRoute,
  comparePlansPortalRoute,
];

export const legacyPortalAliases: Record<string, string> = {
  "#/dashboard?nav=customer-admin-home": "#/dashboard",
  "#/dashboard?nav=customer-user-dashboard": "#/dashboard",
  "#/dashboard?nav=developer-overview": "#/dashboard",
  "#/dashboard?nav=portal-admin-dashboard": "#/dashboard",
  "#/workspace": "#/search",
  "#/workspace?nav=customer-user-search-ein": "#/search",
  "#/workspace?nav=customer-user-search-address": "#/search",
  "#/workspace?nav=developer-tenants": "#/organizations",
  "#/workspace?nav=portal-admin-customers": "#/organizations",
  "#/workspace?nav=customer-admin-team": "#/team",
  "#/workspace?nav=portal-admin-support": "#/team",
  "#/support": "#/support",
  "#/support?nav=customer-admin-support-contact": "#/support",
  "#/support?nav=customer-admin-support-report-issue": "#/support/report-issue",
  "#/api-access": "#/automation",
  "#/api-access?nav=customer-user-automation-general": "#/automation",
  "#/api-access?nav=customer-user-automation-api": "#/automation/api-keys",
  "#/api-access?nav=customer-admin-api": "#/automation/api-keys",
  "#/api-access?nav=developer-system": "#/automation/api-keys",
  "#/api-access?nav=customer-user-automation-oauth": "#/automation/oauth",
  "#/usage-billing": "#/billing",
  "#/usage-billing?nav=customer-admin-billing": "#/billing",
  "#/usage-billing?nav=developer-plans": "#/billing",
  "#/usage-billing?nav=portal-admin-subscriptions": "#/billing",
  "#/usage-billing?nav=customer-admin-usage": "#/usage",
  "#/usage-billing?nav=portal-admin-reports": "#/usage",
  "#/settings": "#/settings/profile",
  "#/settings?nav=customer-user-profile": "#/settings/profile",
  "#/settings?nav=customer-admin-settings": "#/settings/organization",
  "#/settings?nav=developer-feature-flags": "#/settings/organization",
  "#/settings?nav=developer-audit": "#/settings/organization",
  "#/settings?nav=portal-admin-settings": "#/settings/organization",
};
