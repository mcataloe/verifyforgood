import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import { type PropsWithChildren, useEffect, useMemo, useState } from "react";
import { createPortalApiClient } from "../app/portalApiClient";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  createSessionPortalOrganization,
  loadActivePortalOrganization,
  type LoadActivePortalOrganizationOptions,
  type PortalOrganization,
  type PortalOrganizationSessionScope,
} from "./portalOrganization";
import {
  PortalOrganizationContext,
  type PortalOrganizationMemberSummary,
  type PortalOrganizationStatus,
} from "./usePortalOrganization";
import { createPortalMembershipClient } from "./portalMembership";

interface PortalOrganizationProviderProps extends PropsWithChildren {
  accessToken?: string | null;
  fetchImpl?: typeof fetch;
  organizationLoader?: (
    options: LoadActivePortalOrganizationOptions,
  ) => Promise<PortalOrganization>;
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;
  session: PortalAuthenticatedSession;
}

export function PortalOrganizationProvider({
  accessToken,
  children,
  fetchImpl,
  organizationLoader = loadActivePortalOrganization,
  runtimeConfig,
  session,
}: PortalOrganizationProviderProps) {
  const sessionScope = useMemo<PortalOrganizationSessionScope>(
    () => ({
      account_id: session.account_id,
      auth_method: session.auth_method,
      organization_context_status: session.organization_context_status,
      organization_name: session.organization_name,
      workspace_id: session.workspace_id,
    }),
    [
      session.account_id,
      session.auth_method,
      session.organization_context_status,
      session.organization_name,
      session.workspace_id,
    ],
  );
  const runtimeScope = useMemo(
    () => ({
      apiBaseUrl: runtimeConfig.apiBaseUrl,
      apiVersion: runtimeConfig.apiVersion,
    }),
    [runtimeConfig.apiBaseUrl, runtimeConfig.apiVersion],
  );
  const sessionOrganization = useMemo(
    () => createSessionPortalOrganization(sessionScope),
    [sessionScope],
  );
  const [activeOrganization, setActiveOrganization] =
    useState<PortalOrganization>(sessionOrganization);
  const [status, setStatus] = useState<PortalOrganizationStatus>(
    sessionScope.auth_method === "portal_browser_session" ? "loading" : "ready",
  );
  const [members, setMembersState] = useState<PortalOrganizationMemberSummary[]>(
    [],
  );
  const [membersStatus, setMembersStatus] = useState<"idle" | "loading" | "ready">(
    "idle",
  );

  const loaderClient = useMemo(
    () =>
      createPortalApiClient({
        accessToken,
        fetchImpl,
        runtimeConfig: runtimeScope,
        session: sessionScope,
      }),
    [accessToken, fetchImpl, runtimeScope, sessionScope],
  );
  const apiClient = useMemo(
    () =>
      createPortalApiClient({
        accessToken,
        fetchImpl,
        organization: activeOrganization,
        runtimeConfig: runtimeScope,
        session: sessionScope,
      }),
    [accessToken, activeOrganization, fetchImpl, runtimeScope, sessionScope],
  );
  const membershipClient = useMemo(
    () => createPortalMembershipClient(apiClient),
    [apiClient],
  );

  useEffect(() => {
    setActiveOrganization(sessionOrganization);
    setStatus(
      sessionScope.auth_method === "portal_browser_session"
        ? "loading"
        : "ready",
    );
    setMembersState([]);
    setMembersStatus("idle");
  }, [sessionOrganization, sessionScope]);

  useEffect(() => {
    let isCancelled = false;

    const loadOrganization = async () => {
      const organization = await organizationLoader({
        apiClient: loaderClient,
        session: sessionScope,
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
  }, [loaderClient, organizationLoader, sessionScope]);

  const refresh = async () => {
    setStatus("loading");
    const organization = await organizationLoader({
      apiClient: loaderClient,
      session: sessionScope,
    });
    setActiveOrganization(organization);
    setStatus("ready");
  };

  const setMembers = (nextMembers: PortalOrganizationMemberSummary[]) => {
    setMembersState(nextMembers);
    setMembersStatus("ready");
  };

  const refreshMembers = async () => {
    setMembersStatus("loading");
    const nextMembers = await membershipClient.listMembers();
    setMembers(nextMembers);
    return nextMembers;
  };

  const currentMembership =
    members.find((member) => member.user_id === session.user.subject_id)
      ? {
          role:
            members.find((member) => member.user_id === session.user.subject_id)
              ?.role ?? "",
          status:
            members.find((member) => member.user_id === session.user.subject_id)
              ?.status ?? "",
          user_id: session.user.subject_id,
        }
      : session.organization_membership;

  return (
    <PortalOrganizationContext.Provider
      value={{
        activeOrganization,
        apiClient,
        currentMembership,
        members,
        membersStatus,
        refresh,
        refreshMembers,
        setMembers,
        setActiveOrganization,
        status,
      }}
    >
      {children}
    </PortalOrganizationContext.Provider>
  );
}
