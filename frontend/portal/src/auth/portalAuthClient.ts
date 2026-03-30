import { apiEndpoints, createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  createPortalCompatibilitySession,
  type PortalAuthenticatedSession,
  type PortalIdentityUser,
  type PortalStoredAuthRecord,
} from "../app/portalSession";
import {
  createPortalActiveOrganizationRecord,
  clearStoredActiveOrganization,
  writeStoredActiveOrganization,
  type PortalOrganizationCreateResponse,
} from "../organization/portalOrganization";

const PORTAL_AUTH_STORAGE_KEY = "verifyforgood.portal.auth.session";

type PortalAuthRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

interface PortalAuthApiSessionPayload {
  access_token: string;
  token_type: "Bearer";
  user: PortalIdentityUser;
}

interface PortalAuthMePayload {
  organization_context?: PortalOrganizationCreateResponse | null;
  user: PortalIdentityUser;
}

export interface PortalLoginRequest {
  email: string;
  password: string;
}

export interface PortalRegisterRequest {
  email: string;
  full_name?: string;
  password: string;
}

export interface PortalAuthState {
  accessToken: string;
  session: PortalAuthenticatedSession;
}

export interface PortalAuthClient {
  getSession(): Promise<PortalAuthState | null>;
  login(request: PortalLoginRequest): Promise<PortalAuthState>;
  register(request: PortalRegisterRequest): Promise<PortalAuthState>;
  signOut(): Promise<void>;
}

interface CreatePortalAuthClientOptions {
  fetchImpl?: typeof fetch;
  runtimeConfig: PortalAuthRuntimeConfig;
}

export function createPortalAuthClient({
  fetchImpl,
  runtimeConfig,
}: CreatePortalAuthClientOptions): PortalAuthClient {
  const apiClient = createApiClient({
    fetchImpl,
    runtimeConfig,
  });

  return {
    async getSession() {
      const record = readStoredPortalAuthRecord();
      if (!record) {
        return null;
      }

      return hydrateSession(apiClient, record);
    },
    async login(request) {
      const payload = await apiClient.post<
        PortalAuthApiSessionPayload,
        PortalLoginRequest
      >(apiEndpoints.auth.login, {
        body: request,
      });
      const record = writeStoredPortalAuthRecord(payload);
      return requireHydratedSession(apiClient, record);
    },
    async register(request) {
      const payload = await apiClient.post<
        PortalAuthApiSessionPayload,
        PortalRegisterRequest
      >(apiEndpoints.auth.register, {
        body: request,
      });
      const record = writeStoredPortalAuthRecord(payload);
      return requireHydratedSession(apiClient, record);
    },
    async signOut() {
      clearStoredActiveOrganization();
      clearStoredPortalAuthRecord();
    },
  };
}

async function hydrateSession(
  apiClient: ApiClient,
  record: PortalStoredAuthRecord,
): Promise<PortalAuthState | null> {
  try {
    const payload = await apiClient.get<PortalAuthMePayload>(apiEndpoints.auth.me, {
      headers: {
        Authorization: `${record.token_type} ${record.access_token}`,
      },
    });
    const refreshedRecord = writeStoredPortalAuthRecord({
      access_token: record.access_token,
      token_type: record.token_type,
      user: payload.user,
    });
    const activeOrganization = payload.organization_context
      ? writeStoredActiveOrganization(
          createPortalActiveOrganizationRecord(payload.organization_context),
        )
      : (clearStoredActiveOrganization(), null);
    return {
      accessToken: refreshedRecord.access_token,
      session: createPortalCompatibilitySession(
        refreshedRecord.user,
        activeOrganization,
      ),
    };
  } catch (error) {
    const status = typeof error === "object" && error !== null ? (error as { status?: unknown }).status : null;
    if (status === 401) {
      clearStoredActiveOrganization();
      clearStoredPortalAuthRecord();
      return null;
    }
    throw error;
  }
}

async function requireHydratedSession(
  apiClient: ApiClient,
  record: PortalStoredAuthRecord,
): Promise<PortalAuthState> {
  const state = await hydrateSession(apiClient, record);
  if (!state) {
    throw new Error("Authentication is required");
  }

  return state;
}

function readStoredPortalAuthRecord(): PortalStoredAuthRecord | null {
  const storage = resolveStorage();
  if (!storage) {
    return null;
  }

  const raw = storage.getItem(PORTAL_AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    return isPortalStoredAuthRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function writeStoredPortalAuthRecord(
  record: PortalStoredAuthRecord,
): PortalStoredAuthRecord {
  const storage = resolveStorage();
  if (storage) {
    storage.setItem(PORTAL_AUTH_STORAGE_KEY, JSON.stringify(record));
  }
  return record;
}

function clearStoredPortalAuthRecord() {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.removeItem(PORTAL_AUTH_STORAGE_KEY);
}

function resolveStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

function isPortalStoredAuthRecord(
  value: unknown,
): value is PortalStoredAuthRecord {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.access_token === "string" &&
    candidate.token_type === "Bearer" &&
    isPortalIdentityUser(candidate.user)
  );
}

function isPortalIdentityUser(value: unknown): value is PortalIdentityUser {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.email === "string" &&
    typeof candidate.user_id === "string" &&
    (typeof candidate.full_name === "string" || candidate.full_name === null || candidate.full_name === undefined)
  );
}
