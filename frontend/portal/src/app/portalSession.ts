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

export function createMockPortalSession(): PortalAuthenticatedSession {
  return {
    account_id: "acct_verifyforgood_demo",
    auth_method: "mock_browser_session",
    billing_status: "active",
    issued_at: "2026-03-20T00:00:00Z",
    organization_name: "VerifyForGood Demo Workspace",
    plan: "growth",
    roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
    scopes: [
      "portal:access",
      "settings:read",
      "settings:write",
      "billing:read",
      "api-access:read",
    ],
    user: {
      display_name: "Alex Operator",
      email: "alex.operator@example.org",
      subject_id: "user_verifyforgood_demo",
    },
    workspace_id: "ws_verifyforgood_demo",
  };
}
