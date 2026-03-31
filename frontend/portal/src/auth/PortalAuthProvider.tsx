import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  type PropsWithChildren,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  createPortalCompatibilitySession,
  type PortalActiveOrganizationRecord,
  type PortalAvailableOrganizationRecord,
  type PortalAuthenticatedSession,
} from "../app/portalSession";
import {
  createPortalAuthClient,
  type PortalAuthClient,
  type PortalLoginRequest,
  type PortalRegisterRequest,
} from "./portalAuthClient";
import {
  PortalAuthContext,
  type PortalAuthStatus,
} from "./usePortalAuth";
import { writeStoredActiveOrganization } from "../organization/portalOrganization";

interface PortalAuthProviderProps extends PropsWithChildren {
  authClient?: PortalAuthClient;
  fetchImpl?: typeof fetch;
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;
}

interface PortalAuthState {
  accessToken: string | null;
  availableOrganizations: PortalAvailableOrganizationRecord[];
  isBusy: boolean;
  session: PortalAuthenticatedSession | null;
  status: PortalAuthStatus;
}

export function PortalAuthProvider({
  authClient,
  children,
  fetchImpl,
  runtimeConfig,
}: PortalAuthProviderProps) {
  const resolvedAuthClient = useMemo(
    () =>
      authClient ??
      createPortalAuthClient({
        fetchImpl,
        runtimeConfig,
      }),
    [authClient, fetchImpl, runtimeConfig],
  );
  const [authState, setAuthState] = useState<PortalAuthState>({
    accessToken: null,
    availableOrganizations: [],
    isBusy: true,
    session: null,
    status: "loading",
  });

  useEffect(() => {
    let isCancelled = false;

    const loadSession = async () => {
      try {
        const state = await resolvedAuthClient.getSession();
        if (isCancelled) {
          return;
        }

        setAuthState({
          accessToken: state?.accessToken ?? null,
          availableOrganizations: state?.availableOrganizations ?? [],
          isBusy: false,
          session: state?.session ?? null,
          status: state ? "authenticated" : "unauthenticated",
        });
      } catch {
        if (isCancelled) {
          return;
        }

        setAuthState({
          accessToken: null,
          availableOrganizations: [],
          isBusy: false,
          session: null,
          status: "unauthenticated",
        });
      }
    };

    void loadSession();

    return () => {
      isCancelled = true;
    };
  }, [resolvedAuthClient]);

  const login = async (request: PortalLoginRequest) => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    const state = await resolvedAuthClient.login(request);
    setAuthState({
      accessToken: state.accessToken,
      availableOrganizations: state.availableOrganizations,
      isBusy: false,
      session: state.session,
      status: "authenticated",
    });
    return state.session;
  };

  const register = async (request: PortalRegisterRequest) => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    const state = await resolvedAuthClient.register(request);
    setAuthState({
      accessToken: state.accessToken,
      availableOrganizations: state.availableOrganizations,
      isBusy: false,
      session: state.session,
      status: "authenticated",
    });
    return state.session;
  };

  const applyOrganization = (organization: PortalActiveOrganizationRecord) => {
    if (!authState.session) {
      throw new Error("An authenticated session is required");
    }

    const persisted = writeStoredActiveOrganization(organization);
    const nextSession = createPortalCompatibilitySession(
      {
        email: authState.session.user.email,
        full_name: authState.session.user.display_name,
        user_id: authState.session.user.subject_id,
      },
      persisted,
    );
    const nextAvailableOrganizations =
      authState.availableOrganizations.find(
        (candidate) =>
          candidate.organization_id === persisted.organization_id,
      )
        ? authState.availableOrganizations
        : [...authState.availableOrganizations, persisted];
    setAuthState((currentState) => ({
      ...currentState,
      availableOrganizations: nextAvailableOrganizations,
      session: nextSession,
      status: "authenticated",
    }));
    return nextSession;
  };

  const signOut = async () => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    await resolvedAuthClient.signOut();
    setAuthState({
      accessToken: null,
      availableOrganizations: [],
      isBusy: false,
      session: null,
      status: "unauthenticated",
    });
  };

  return (
    <PortalAuthContext.Provider
      value={{
        accessToken: authState.accessToken,
        availableOrganizations: authState.availableOrganizations,
        applyOrganization,
        isBusy: authState.isBusy,
        login,
        register,
        session: authState.session,
        signOut,
        status: authState.status,
      }}
    >
      {children}
    </PortalAuthContext.Provider>
  );
}
