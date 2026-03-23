import {
  createMockPortalSession,
  type PortalAuthenticatedSession,
} from "../app/portalSession";
import {
  FRONTEND_ACCESS_ROLE,
  isFrontendAccessRole,
} from "@charity-status/shared-types";

const PORTAL_SESSION_STORAGE_KEY = "verifyforgood.portal.auth.session";

export type PortalSignInMethod = "google" | "microsoft" | "password";

export interface PortalSignInRequest {
  email?: string;
  method: PortalSignInMethod;
  password?: string;
}

export interface PortalAuthClient {
  getSession(): Promise<PortalAuthenticatedSession | null>;
  signIn(request?: PortalSignInRequest): Promise<PortalAuthenticatedSession>;
  signOut(): Promise<void>;
}

export function createMockPortalAuthClient(): PortalAuthClient {
  return {
    async getSession() {
      return readStoredPortalSession();
    },
    async signIn(request) {
      const session = createMockPortalSession({
        email: request?.email,
        provider: request?.method ?? "password",
        roles: [FRONTEND_ACCESS_ROLE.customerUser],
      });
      writeStoredPortalSession(session);
      return session;
    },
    async signOut() {
      clearStoredPortalSession();
    },
  };
}

function readStoredPortalSession(): PortalAuthenticatedSession | null {
  const storage = resolveStorage();
  if (!storage) {
    return null;
  }

  const raw = storage.getItem(PORTAL_SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    return isPortalAuthenticatedSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function writeStoredPortalSession(session: PortalAuthenticatedSession) {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.setItem(PORTAL_SESSION_STORAGE_KEY, JSON.stringify(session));
}

function clearStoredPortalSession() {
  const storage = resolveStorage();
  if (!storage) {
    return;
  }

  storage.removeItem(PORTAL_SESSION_STORAGE_KEY);
}

function resolveStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

function isPortalAuthenticatedSession(
  value: unknown,
): value is PortalAuthenticatedSession {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  const user = candidate.user;
  return (
    typeof candidate.account_id === "string" &&
    typeof candidate.workspace_id === "string" &&
    typeof candidate.organization_name === "string" &&
    typeof candidate.plan === "string" &&
    typeof candidate.auth_method === "string" &&
    Array.isArray(candidate.roles) &&
    candidate.roles.every((role) => isFrontendAccessRole(role)) &&
    Array.isArray(candidate.scopes) &&
    candidate.scopes.every((scope) => typeof scope === "string") &&
    Boolean(user) &&
    typeof user === "object" &&
    typeof (user as Record<string, unknown>).display_name === "string" &&
    typeof (user as Record<string, unknown>).email === "string" &&
    typeof (user as Record<string, unknown>).subject_id === "string"
  );
}
