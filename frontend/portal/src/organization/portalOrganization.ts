import { apiEndpoints, createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type {
  PortalActiveOrganizationRecord,
  PortalAuthenticatedSession,
} from "../app/portalSession";

const PORTAL_ACTIVE_ORGANIZATION_STORAGE_KEY =
  "verifyforgood.portal.organization.active";

type PortalOrganizationRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

export interface PortalOrganizationSettingsDocument {
  account_id?: string | null;
  billing?: {
    allowOverage?: boolean;
    monthlyRequestCap?: number | null;
  };
  source?: "default" | "stored";
  updated_at?: string | null;
  workspace_id?: string | null;
}

export interface PortalOrganization {
  account_id: string;
  billing_allow_overage: boolean | null;
  billing_monthly_request_cap: number | null;
  organization_name: string;
  scope_source:
    | "active_organization"
    | "backend_settings"
    | "session_fallback"
    | "session_mock";
  settings_source: "default" | "mock" | "stored";
  updated_at: string | null;
  workspace_id: string;
}

export interface PortalOrganizationSessionScope {
  account_id: string;
  auth_method: PortalAuthenticatedSession["auth_method"];
  organization_context_status: PortalAuthenticatedSession["organization_context_status"];
  organization_name: string;
  workspace_id: string;
}

export interface LoadActivePortalOrganizationOptions {
  apiClient: ApiClient;
  session: PortalOrganizationSessionScope;
}

export interface PortalOrganizationCreateRequest {
  name: string;
  slug?: string;
}

export interface PortalOrganizationCreateResponse {
  account_id: string;
  membership: {
    role: string;
    status: string;
    user_id: string;
  };
  organization_id: string;
  organization_name: string;
  slug: string;
  workspace_id: string;
}

interface CreatePortalOrganizationClientOptions {
  accessToken: string;
  fetchImpl?: typeof fetch;
  runtimeConfig: PortalOrganizationRuntimeConfig;
}

export interface PortalOrganizationClient {
  createOrganization(
    request: PortalOrganizationCreateRequest,
  ): Promise<PortalOrganizationCreateResponse>;
}

export function createSessionPortalOrganization(
  session: PortalOrganizationSessionScope,
  scopeSource: PortalOrganization["scope_source"] = "session_mock",
): PortalOrganization {
  return {
    account_id: session.account_id,
    billing_allow_overage: null,
    billing_monthly_request_cap: null,
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
  if (session.organization_context_status === "pending") {
    return createSessionPortalOrganization(session, "session_mock");
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
      billing_monthly_request_cap:
        typeof settings.billing?.monthlyRequestCap === "number" &&
        Number.isInteger(settings.billing.monthlyRequestCap) &&
        settings.billing.monthlyRequestCap > 0
          ? settings.billing.monthlyRequestCap
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

export function createPortalOrganizationClient({
  accessToken,
  fetchImpl,
  runtimeConfig,
}: CreatePortalOrganizationClientOptions): PortalOrganizationClient {
  const apiClient = createApiClient({
    fetchImpl,
    headersProvider: async () => ({
      Authorization: `Bearer ${accessToken}`,
    }),
    runtimeConfig,
  });

  return {
    createOrganization(request) {
      return apiClient.post<
        PortalOrganizationCreateResponse,
        PortalOrganizationCreateRequest
      >(apiEndpoints.organization.create, {
        body: request,
      });
    },
  };
}

export function readStoredActiveOrganization():
  | PortalActiveOrganizationRecord
  | null {
  const storage = resolveStorage();
  if (!storage) {
    return null;
  }

  const raw = storage.getItem(PORTAL_ACTIVE_ORGANIZATION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    return isPortalActiveOrganizationRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeStoredActiveOrganization(
  record: PortalActiveOrganizationRecord,
): PortalActiveOrganizationRecord {
  const storage = resolveStorage();
  if (storage) {
    storage.setItem(
      PORTAL_ACTIVE_ORGANIZATION_STORAGE_KEY,
      JSON.stringify(record),
    );
  }

  return record;
}

export function clearStoredActiveOrganization() {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.removeItem(PORTAL_ACTIVE_ORGANIZATION_STORAGE_KEY);
}

export function createPortalActiveOrganizationRecord(
  response: PortalOrganizationCreateResponse,
): PortalActiveOrganizationRecord {
  return {
    account_id: response.account_id,
    membership: response.membership,
    organization_id: response.organization_id,
    organization_name: response.organization_name,
    slug: response.slug,
    workspace_id: response.workspace_id,
  };
}

function resolveStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

function isPortalActiveOrganizationRecord(
  value: unknown,
): value is PortalActiveOrganizationRecord {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const membership = candidate.membership;
  return (
    typeof candidate.account_id === "string" &&
    typeof candidate.organization_id === "string" &&
    typeof candidate.organization_name === "string" &&
    typeof candidate.slug === "string" &&
    typeof candidate.workspace_id === "string" &&
    !!membership &&
    typeof membership === "object" &&
    typeof (membership as Record<string, unknown>).role === "string" &&
    typeof (membership as Record<string, unknown>).status === "string" &&
    typeof (membership as Record<string, unknown>).user_id === "string"
  );
}
