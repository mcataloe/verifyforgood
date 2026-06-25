import { apiEndpoints, createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type {
  PortalActiveOrganizationRecord,
  PortalAvailableOrganizationRecord,
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
  organization?: {
    contactEmail?: string | null;
    createdAt?: string | null;
    displayName?: string | null;
    organizationId?: string | null;
    slug?: string | null;
    updatedAt?: string | null;
  };
  source?: "default" | "stored";
  updated_at?: string | null;
  workspace_id?: string | null;
}

export interface PortalOrganization {
  account_id: string;
  billing_allow_overage: boolean | null;
  billing_monthly_request_cap: number | null;
  contact_email?: string | null;
  created_at?: string | null;
  organization_id?: string | null;
  organization_name: string;
  organization_updated_at?: string | null;
  scope_source:
    | "active_organization"
    | "backend_settings"
    | "session_fallback"
    | "session_mock";
  settings_source: "default" | "mock" | "stored";
  slug?: string | null;
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

export function dedupePortalOrganizations(
  organizations: readonly PortalAvailableOrganizationRecord[],
): PortalAvailableOrganizationRecord[] {
  const seen = new Set<string>();
  const deduped: PortalAvailableOrganizationRecord[] = [];

  for (const organization of organizations) {
    if (seen.has(organization.organization_id)) {
      continue;
    }
    seen.add(organization.organization_id);
    deduped.push(organization);
  }

  return deduped;
}

export function resolveAvailablePortalOrganizations(options: {
  availableOrganizations?: readonly PortalAvailableOrganizationRecord[] | null;
  organizationContext?: PortalActiveOrganizationRecord | null;
}): PortalAvailableOrganizationRecord[] {
  const resolved = dedupePortalOrganizations(options.availableOrganizations ?? []);

  if (!resolved.length && options.organizationContext) {
    return [options.organizationContext];
  }

  return resolved;
}

export function resolveActivePortalOrganization(options: {
  availableOrganizations: readonly PortalAvailableOrganizationRecord[];
  organizationContext?: PortalActiveOrganizationRecord | null;
  storedOrganization?: PortalActiveOrganizationRecord | null;
}): PortalActiveOrganizationRecord | null {
  const matchingStoredOrganization = options.storedOrganization
    ? options.availableOrganizations.find(
        (organization) =>
          organization.organization_id === options.storedOrganization?.organization_id,
      ) ?? null
    : null;

  return matchingStoredOrganization ?? options.organizationContext ?? null;
}

export function createSessionPortalOrganization(
  session: PortalOrganizationSessionScope,
  scopeSource: PortalOrganization["scope_source"] = "session_mock",
): PortalOrganization {
  return {
    account_id: session.account_id,
    billing_allow_overage: null,
    billing_monthly_request_cap: null,
    contact_email: null,
    created_at: null,
    organization_id: session.workspace_id,
    organization_name: session.organization_name,
    organization_updated_at: null,
    scope_source: scopeSource,
    settings_source: "mock",
    slug: null,
    updated_at: null,
    workspace_id: session.workspace_id,
  };
}

export function mapSettingsToPortalOrganization({
  session,
  settings,
}: {
  session: PortalOrganizationSessionScope;
  settings: PortalOrganizationSettingsDocument;
}): PortalOrganization {
  const organization = settings.organization;
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
    contact_email: organization?.contactEmail ?? null,
    created_at: organization?.createdAt ?? null,
    organization_id: organization?.organizationId ?? settings.workspace_id ?? session.workspace_id,
    organization_name:
      organization?.displayName?.trim() || session.organization_name,
    organization_updated_at: organization?.updatedAt ?? null,
    scope_source: "backend_settings",
    settings_source: settings.source ?? "default",
    slug: organization?.slug ?? null,
    updated_at: settings.updated_at ?? null,
    workspace_id: settings.workspace_id ?? session.workspace_id,
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
    return mapSettingsToPortalOrganization({ session, settings });
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
    credentials: "include",
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
