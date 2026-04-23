import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useRef,
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
  type PortalAuthState as PortalAuthClientState,
  type PortalLoginRequest,
  type PortalRegisterRequest,
} from "./portalAuthClient";
import {
  PortalAuthContext,
  type PortalAuthStatus,
} from "./usePortalAuth";
import {
  clearStoredActiveOrganization,
  writeStoredActiveOrganization,
} from "../organization/portalOrganization";

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
  const refreshSessionPromiseRef = useRef<Promise<PortalAuthenticatedSession | null> | null>(
    null,
  );

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
    try {
      const state = await resolvedAuthClient.login(request);
      setAuthState({
        accessToken: state.accessToken,
        availableOrganizations: state.availableOrganizations,
        isBusy: false,
        session: state.session,
        status: "authenticated",
      });
      return state.session;
    } catch (error) {
      setAuthState((currentState) => ({ ...currentState, isBusy: false }));
      throw error;
    }
  };

  const applyAuthClientState = useCallback((state: PortalAuthClientState | null) => {
    if (!state) {
      setAuthState({
        accessToken: null,
        availableOrganizations: [],
        isBusy: false,
        session: null,
        status: "unauthenticated",
      });
      return null;
    }

    setAuthState((currentState) => ({
      ...currentState,
      accessToken: state.accessToken,
      availableOrganizations: state.availableOrganizations,
      isBusy: false,
      session: state.session,
      status: "authenticated",
    }));
    return state.session;
  }, []);

  const refreshSession = useCallback(async () => {
    if (refreshSessionPromiseRef.current) {
      return refreshSessionPromiseRef.current;
    }

    const refreshPromise = resolvedAuthClient
      .refreshSession()
      .then((state) => applyAuthClientState(state))
      .catch((error) => {
        if (isAuthenticationRefreshFailure(error)) {
          setAuthState({
            accessToken: null,
            availableOrganizations: [],
            isBusy: false,
            session: null,
            status: "unauthenticated",
          });
        }
        throw error;
      })
      .finally(() => {
        refreshSessionPromiseRef.current = null;
      });
    refreshSessionPromiseRef.current = refreshPromise;
    return refreshPromise;
  }, [applyAuthClientState, resolvedAuthClient]);

  const register = async (request: PortalRegisterRequest) => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    try {
      const state = await resolvedAuthClient.register(request);
      setAuthState({
        accessToken: state.accessToken,
        availableOrganizations: state.availableOrganizations,
        isBusy: false,
        session: state.session,
        status: "authenticated",
      });
      return state.session;
    } catch (error) {
      setAuthState((currentState) => ({ ...currentState, isBusy: false }));
      throw error;
    }
  };

  const applyOrganization = (organization: PortalActiveOrganizationRecord) => {
    if (!authState.session) {
      throw new Error("An authenticated session is required");
    }

    const persisted = writeStoredActiveOrganization(organization);
    const nextAvailableOrganizations =
      authState.availableOrganizations.some(
        (candidate) =>
          candidate.organization_id === persisted.organization_id,
      )
        ? authState.availableOrganizations.map((candidate) =>
            candidate.organization_id === persisted.organization_id
              ? persisted
              : candidate,
          )
        : [...authState.availableOrganizations, persisted];
    const nextSession = {
      ...authState.session,
      account_id: persisted.account_id,
      organization_context_status: "active" as const,
      organization_membership: persisted.membership,
      organization_name: persisted.organization_name,
      workspace_id: persisted.workspace_id,
    };
    setAuthState((currentState) => ({
      ...currentState,
      availableOrganizations: nextAvailableOrganizations,
      session: nextSession,
      status: "authenticated",
    }));
    return nextSession;
  };

  const removeOrganization = (organizationId: string) => {
    if (!authState.session) {
      throw new Error("An authenticated session is required");
    }

    const remainingOrganizations = authState.availableOrganizations.filter(
      (organization) => organization.organization_id !== organizationId,
    );
    const nextOrganization =
      remainingOrganizations.find(
        (organization) =>
          organization.organization_id !== authState.session?.workspace_id,
      ) ??
      remainingOrganizations[0] ??
      null;

    if (nextOrganization) {
      writeStoredActiveOrganization(nextOrganization);
    } else {
      clearStoredActiveOrganization();
    }

    const nextSession = nextOrganization
      ? {
          ...authState.session,
          account_id: nextOrganization.account_id,
          organization_context_status: "active" as const,
          organization_membership: nextOrganization.membership,
          organization_name: nextOrganization.organization_name,
          workspace_id: nextOrganization.workspace_id,
        }
      : createPortalCompatibilitySession(
          {
            email: authState.session.user.email,
            full_name: authState.session.user.display_name,
            user_id: authState.session.user.subject_id,
          },
          null,
        );
    setAuthState((currentState) => ({
      ...currentState,
      availableOrganizations: remainingOrganizations,
      session: nextSession,
      status: "authenticated",
    }));
    return nextSession;
  };

  const signOut = async () => {
    setAuthState((currentState) => ({ ...currentState, isBusy: true }));
    try {
      await resolvedAuthClient.signOut();
      setAuthState({
        accessToken: null,
        availableOrganizations: [],
        isBusy: false,
        session: null,
        status: "unauthenticated",
      });
    } catch (error) {
      setAuthState((currentState) => ({ ...currentState, isBusy: false }));
      throw error;
    }
  };

  return (
    <PortalAuthContext.Provider
      value={{
        accessToken: authState.accessToken,
        availableOrganizations: authState.availableOrganizations,
        applyOrganization,
        isBusy: authState.isBusy,
        login,
        removeOrganization,
        register,
        refreshSession,
        session: authState.session,
        signOut,
        status: authState.status,
      }}
    >
      {children}
    </PortalAuthContext.Provider>
  );
}

function isAuthenticationRefreshFailure(error: unknown) {
  if (typeof error === "object" && error !== null) {
    const status = (error as { status?: unknown }).status;
    if (status === 401) {
      return true;
    }
  }

  return error instanceof Error && error.message === "Authentication is required";
}
