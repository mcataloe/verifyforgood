import { createContext, useContext } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type {
  PortalLoginRequest,
  PortalRegisterRequest,
} from "./portalAuthClient";

export type PortalAuthStatus = "authenticated" | "loading" | "unauthenticated";

export interface PortalAuthContextValue {
  accessToken: string | null;
  isBusy: boolean;
  login: (request: PortalLoginRequest) => Promise<PortalAuthenticatedSession>;
  register: (
    request: PortalRegisterRequest,
  ) => Promise<PortalAuthenticatedSession>;
  session: PortalAuthenticatedSession | null;
  signOut: () => Promise<void>;
  status: PortalAuthStatus;
}

export const PortalAuthContext = createContext<PortalAuthContextValue | null>(
  null,
);

export function usePortalAuth() {
  const context = useContext(PortalAuthContext);
  if (!context) {
    throw new Error("usePortalAuth must be used inside PortalAuthProvider.");
  }

  return context;
}
