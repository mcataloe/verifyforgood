import { apiEndpoints, createApiClient, type ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  createPortalCompatibilitySession,
  type PortalAvailableOrganizationRecord,
  type PortalAuthenticatedSession,
  type PortalIdentityUser,
  type PortalStoredAuthRecord,
} from "../app/portalSession";
import {
  clearStoredActiveOrganization,
  createPortalActiveOrganizationRecord,
  readStoredActiveOrganization,
  resolveActivePortalOrganization,
  resolveAvailablePortalOrganizations,
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
  available_organizations?: PortalOrganizationCreateResponse[] | null;
  access_token?: string | null;
  organization_context?: PortalOrganizationCreateResponse | null;
  token_type?: "Bearer" | null;
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
  availableOrganizations: PortalAvailableOrganizationRecord[];
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
    credentials: "include",
    fetchImpl,
    runtimeConfig,
  });

  return {
    async getSession() {
      const cookieSession = await hydrateSessionFromCookie(apiClient);
      if (cookieSession) {
        return cookieSession;
      }

      const record = readStoredPortalAuthRecord();
      if (!record) {
        return null;
      }

      return hydrateSessionFromRecord(apiClient, record);
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
      try {
        await apiClient.post(apiEndpoints.auth.logout, {});
      } finally {
        clearStoredActiveOrganization();
        clearStoredPortalAuthRecord();
      }
    },
  };
}

async function hydrateSessionFromCookie(
  apiClient: ApiClient,
): Promise<PortalAuthState | null> {
  try {
    const payload = await apiClient.get<PortalAuthMePayload>(apiEndpoints.auth.me);
    return buildPortalAuthState(payload);
  } catch (error) {
    const status =
      typeof error === "object" && error !== null
        ? (error as { status?: unknown }).status
        : null;
    if (status === 401) {
      return null;
    }
    if (error instanceof Error && error.message === "Authentication is required") {
      return null;
    }
    throw error;
  }
}

async function hydrateSessionFromRecord(
  apiClient: ApiClient,
  record: PortalStoredAuthRecord,
): Promise<PortalAuthState | null> {
  try {
    const payload = await apiClient.get<PortalAuthMePayload>(apiEndpoints.auth.me, {
      headers: {
        Authorization: `${record.token_type} ${record.access_token}`,
      },
    });
    return buildPortalAuthState(payload, record.access_token);
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

function buildPortalAuthState(
  payload: PortalAuthMePayload,
  fallbackAccessToken?: string,
): PortalAuthState {
  const accessToken =
    String(payload.access_token || "").trim() ||
    String(fallbackAccessToken || "").trim();
  if (!accessToken) {
    throw new Error("Authentication is required");
  }
  const refreshedRecord = writeStoredPortalAuthRecord({
    access_token: accessToken,
    token_type: payload.token_type ?? "Bearer",
    user: payload.user,
  });
  const { activeOrganization, availableOrganizations } =
    resolveHydratedOrganizations(payload);
  return {
    accessToken: refreshedRecord.access_token,
    availableOrganizations,
    session: createPortalCompatibilitySession(
      refreshedRecord.user,
      activeOrganization,
    ),
  };
}

function resolveHydratedOrganizations(
  payload: PortalAuthMePayload,
): {
  activeOrganization: PortalAvailableOrganizationRecord | null;
  availableOrganizations: PortalAvailableOrganizationRecord[];
} {
  const organizationContext = payload.organization_context
    ? createPortalActiveOrganizationRecord(payload.organization_context)
    : null;
  const availableOrganizations = resolveAvailablePortalOrganizations({
    availableOrganizations: payload.available_organizations?.map(
      createPortalActiveOrganizationRecord,
    ),
    organizationContext,
  });
  const storedOrganization = readStoredActiveOrganization();
  const activeOrganization = resolveActivePortalOrganization({
    availableOrganizations,
    organizationContext,
    storedOrganization,
  });

  if (activeOrganization) {
    writeStoredActiveOrganization(activeOrganization);
  } else {
    clearStoredActiveOrganization();
  }

  return {
    activeOrganization,
    availableOrganizations,
  };
}

async function requireHydratedSession(
  apiClient: ApiClient,
  record: PortalStoredAuthRecord,
): Promise<PortalAuthState> {
  const state = await hydrateSessionFromRecord(apiClient, record);
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
