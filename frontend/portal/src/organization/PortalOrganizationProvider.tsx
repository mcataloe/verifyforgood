import type { ApiClient } from "@charity-status/shared-api";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { createPortalApiClient } from "../app/portalApiClient";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  createSessionPortalOrganization,
  loadActivePortalOrganization,
  type LoadActivePortalOrganizationOptions,
  type PortalOrganization,
} from "./portalOrganization";

export type PortalOrganizationStatus = "loading" | "ready";

interface PortalOrganizationContextValue {
  activeOrganization: PortalOrganization;
  apiClient: ApiClient;
  refresh: () => Promise<void>;
  status: PortalOrganizationStatus;
}

interface PortalOrganizationProviderProps extends PropsWithChildren {
  fetchImpl?: typeof fetch;
  organizationLoader?: (
    options: LoadActivePortalOrganizationOptions,
  ) => Promise<PortalOrganization>;
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;
  session: PortalAuthenticatedSession;
}

const PortalOrganizationContext =
  createContext<PortalOrganizationContextValue | null>(null);

export function PortalOrganizationProvider({
  children,
  fetchImpl,
  organizationLoader = loadActivePortalOrganization,
  runtimeConfig,
  session,
}: PortalOrganizationProviderProps) {
  const sessionOrganization = useMemo(
    () => createSessionPortalOrganization(session),
    [session.account_id, session.organization_name, session.workspace_id],
  );
  const [activeOrganization, setActiveOrganization] =
    useState<PortalOrganization>(sessionOrganization);
  const [status, setStatus] = useState<PortalOrganizationStatus>(
    session.auth_method === "portal_browser_session" ? "loading" : "ready",
  );

  const loaderClient = useMemo(
    () =>
      createPortalApiClient({
        fetchImpl,
        runtimeConfig,
        session,
      }),
    [
      fetchImpl,
      runtimeConfig.apiBaseUrl,
      runtimeConfig.apiVersion,
      session.account_id,
      session.auth_method,
      session.organization_name,
      session.workspace_id,
    ],
  );
  const apiClient = useMemo(
    () =>
      createPortalApiClient({
        fetchImpl,
        organization: activeOrganization,
        runtimeConfig,
        session,
      }),
    [
      activeOrganization.account_id,
      activeOrganization.organization_name,
      activeOrganization.workspace_id,
      fetchImpl,
      runtimeConfig.apiBaseUrl,
      runtimeConfig.apiVersion,
      session.account_id,
      session.auth_method,
      session.organization_name,
      session.workspace_id,
    ],
  );

  useEffect(() => {
    setActiveOrganization(sessionOrganization);
    setStatus(
      session.auth_method === "portal_browser_session" ? "loading" : "ready",
    );
  }, [
    session.auth_method,
    session.account_id,
    session.organization_name,
    session.workspace_id,
    sessionOrganization,
  ]);

  useEffect(() => {
    let isCancelled = false;

    const loadOrganization = async () => {
      const organization = await organizationLoader({
        apiClient: loaderClient,
        session,
      });
      if (isCancelled) {
        return;
      }

      setActiveOrganization(organization);
      setStatus("ready");
    };

    void loadOrganization();

    return () => {
      isCancelled = true;
    };
  }, [
    loaderClient,
    organizationLoader,
    session.account_id,
    session.auth_method,
    session.organization_name,
    session.workspace_id,
  ]);

  const refresh = async () => {
    setStatus("loading");
    const organization = await organizationLoader({
      apiClient: loaderClient,
      session,
    });
    setActiveOrganization(organization);
    setStatus("ready");
  };

  return (
    <PortalOrganizationContext.Provider
      value={{
        activeOrganization,
        apiClient,
        refresh,
        status,
      }}
    >
      {children}
    </PortalOrganizationContext.Provider>
  );
}

export function usePortalOrganization() {
  const context = useContext(PortalOrganizationContext);
  if (!context) {
    throw new Error(
      "usePortalOrganization must be used inside PortalOrganizationProvider.",
    );
  }

  return context;
}
