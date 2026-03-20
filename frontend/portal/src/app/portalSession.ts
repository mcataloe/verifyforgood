import type { OrganizationContext } from "@charity-status/shared-types";

export interface PortalSessionStub extends OrganizationContext {
  auth_mode: "api_key_or_oauth";
  billing_status: "active" | "stubbed";
  organization_name: string;
  plan: string;
}

export function getPortalSessionStub(): PortalSessionStub {
  return {
    account_id: "acct_verifyforgood_demo",
    auth_mode: "api_key_or_oauth",
    billing_status: "active",
    organization_name: "VerifyForGood Demo Workspace",
    plan: "growth",
    workspace_id: "ws_verifyforgood_demo",
  };
}
