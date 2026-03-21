import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import type { PortalAuthenticatedSession } from "../app/portalSession";

export interface PortalOrganizationSettingsDocument {
  account_id?: string | null;
  billing?: {
    allowOverage?: boolean;
  };
  source?: "default" | "stored";
  updated_at?: string | null;
  workspace_id?: string | null;
}

export interface PortalOrganization {
  account_id: string;
  billing_allow_overage: boolean | null;
  organization_name: string;
  scope_source: "backend_settings" | "session_fallback" | "session_mock";
  settings_source: "default" | "mock" | "stored";
  updated_at: string | null;
  workspace_id: string;
}

export interface PortalOrganizationSessionScope {
  account_id: string;
  auth_method: PortalAuthenticatedSession["auth_method"];
  organization_name: string;
  workspace_id: string;
}

export interface LoadActivePortalOrganizationOptions {
  apiClient: ApiClient;
  session: PortalOrganizationSessionScope;
}

export function createSessionPortalOrganization(
  session: PortalOrganizationSessionScope,
  scopeSource: PortalOrganization["scope_source"] = "session_mock",
): PortalOrganization {
  return {
    account_id: session.account_id,
    billing_allow_overage: null,
    organization_name: session.organization_name,
    scope_source: scopeSource,
    settings_source: "mock",
    updated_at: null,
    workspace_id: session.workspace_id,
  };
}

export async function loadActivePortalOrganization({
  apiClient,
  session,
}: LoadActivePortalOrganizationOptions): Promise<PortalOrganization> {
  if (session.auth_method === "mock_browser_session") {
    return createSessionPortalOrganization(session);
  }

  try {
    const settings = await apiClient.get<PortalOrganizationSettingsDocument>(
      apiEndpoints.organization.settings,
    );

    return {
      account_id: settings.account_id ?? session.account_id,
      billing_allow_overage:
        typeof settings.billing?.allowOverage === "boolean"
          ? settings.billing.allowOverage
          : null,
      organization_name: session.organization_name,
      scope_source: "backend_settings",
      settings_source: settings.source ?? "default",
      updated_at: settings.updated_at ?? null,
      workspace_id: settings.workspace_id ?? session.workspace_id,
    };
  } catch {
    return createSessionPortalOrganization(session, "session_fallback");
  }
}
