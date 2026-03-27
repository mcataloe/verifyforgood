import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type OrganizationContext,
} from "@charity-status/shared-types";

export interface PortalIdentityUser {
  email: string;
  full_name: string | null;
  user_id: string;
}

export interface PortalSessionUser {
  display_name: string;
  email: string;
  subject_id: string;
}

export interface PortalAuthenticatedSession extends OrganizationContext {
  account_id: string;
  auth_method: "mock_browser_session" | "portal_browser_session";
  billing_status: "active" | "stubbed" | "trialing";
  issued_at: string;
  organization_name: string;
  plan: string;
  roles: FrontendAccessRole[];
  scopes: string[];
  user: PortalSessionUser;
  workspace_id: string;
}

export interface PortalStoredAuthRecord {
  access_token: string;
  token_type: "Bearer";
  user: PortalIdentityUser;
}

const PORTAL_SESSION_COMPATIBILITY_DEFAULTS = {
  account_id: "acct_portal_pending",
  billing_status: "stubbed" as const,
  organization_name: "Organization setup pending",
  plan: "growth",
  roles: [FRONTEND_ACCESS_ROLE.customerAdmin] as FrontendAccessRole[],
  scopes: ["portal:access"],
  workspace_id: "ws_portal_pending",
};

type CreateMockPortalSessionOptions = {
  email?: string;
  provider?: "google" | "microsoft" | "password";
  roles?: FrontendAccessRole[];
};

export function createMockPortalSession(
  options: CreateMockPortalSessionOptions = {},
): PortalAuthenticatedSession {
  const email = options.email?.trim().toLowerCase() || "alex.operator@example.org";
  const providerLabel =
    options.provider === "google"
      ? "Google"
      : options.provider === "microsoft"
        ? "Microsoft"
        : "Portal";

  return {
    account_id: "acct_verifyforgood_demo",
    auth_method: "mock_browser_session",
    billing_status: "active",
    issued_at: "2026-03-20T00:00:00Z",
    organization_name: "VerifyForGood Demo Workspace",
    plan: "growth",
    roles: options.roles ?? [FRONTEND_ACCESS_ROLE.customerAdmin],
    scopes: [
      "portal:access",
      "settings:read",
      "settings:write",
      "billing:read",
      "api-access:read",
    ],
    user: {
      display_name: deriveMockDisplayName(email, providerLabel),
      email,
      subject_id: "user_verifyforgood_demo",
    },
    workspace_id: "ws_verifyforgood_demo",
  };
}

export function createPortalCompatibilitySession(
  user: PortalIdentityUser,
): PortalAuthenticatedSession {
  return {
    account_id: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.account_id,
    auth_method: "portal_browser_session",
    billing_status: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.billing_status,
    issued_at: new Date().toISOString(),
    organization_name: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.organization_name,
    plan: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.plan,
    roles: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.roles,
    scopes: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.scopes,
    user: {
      display_name: resolvePortalDisplayName(user),
      email: user.email,
      subject_id: user.user_id,
    },
    workspace_id: PORTAL_SESSION_COMPATIBILITY_DEFAULTS.workspace_id,
  };
}

function deriveMockDisplayName(email: string, providerLabel: string) {
  const localPart = email.split("@")[0] || "operator";
  const words = localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment[0]?.toUpperCase() + segment.slice(1));

  return words.length ? words.join(" ") : `${providerLabel} User`;
}

function resolvePortalDisplayName(user: PortalIdentityUser) {
  const fullName = user.full_name?.trim();
  if (fullName) {
    return fullName;
  }

  return deriveMockDisplayName(user.email, "Portal");
}
