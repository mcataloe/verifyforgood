import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type OrganizationContext,
} from "@charity-status/shared-types";

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

function deriveMockDisplayName(email: string, providerLabel: string) {
  const localPart = email.split("@")[0] || "operator";
  const words = localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment[0]?.toUpperCase() + segment.slice(1));

  return words.length ? words.join(" ") : `${providerLabel} User`;
}
