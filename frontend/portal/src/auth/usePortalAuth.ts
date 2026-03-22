import { useEffect, useMemo, useState } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  createMockPortalAuthClient,
  type PortalAuthClient,
  type PortalSignInRequest,
} from "./portalAuthClient";

export type PortalAuthStatus = "authenticated" | "loading" | "unauthenticated";

interface PortalAuthState {
  isBusy: boolean;
  session: PortalAuthenticatedSession | null;
  status: PortalAuthStatus;
}

const defaultPortalAuthClient = createMockPortalAuthClient();

export function usePortalAuth(
  authClient: PortalAuthClient = defaultPortalAuthClient,
) {
  const resolvedAuthClient = useMemo(() => authClient, [authClient]);
  const [authState, setAuthState] = useState<PortalAuthState>({
    isBusy: true,
    session: null,
    status: "loading",
  });

  useEffect(() => {
    let isCancelled = false;

    const loadSession = async () => {
      const session = await resolvedAuthClient.getSession();
      if (isCancelled) {
        return;
      }

      setAuthState({
        isBusy: false,
        session,
        status: session ? "authenticated" : "unauthenticated",
      });
    };

    void loadSession();

    return () => {
      isCancelled = true;
    };
  }, [resolvedAuthClient]);

  const signIn = async (request?: PortalSignInRequest) => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    const session = await resolvedAuthClient.signIn(request);
    setAuthState({
      isBusy: false,
      session,
      status: "authenticated",
    });
    return session;
  };

  const signOut = async () => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    await resolvedAuthClient.signOut();
    setAuthState({
      isBusy: false,
      session: null,
      status: "unauthenticated",
    });
  };

  return {
    ...authState,
    signIn,
    signOut,
  };
}
