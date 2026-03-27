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
  OrganizationContext,
  type OrganizationContextValue,
  type OrganizationMemberSummary,
  type OrganizationMembersStatus,
  type OrganizationSelectionStatus,
  type OrganizationStatus,
} from "./useOrganization";
import { createPortalMembershipClient } from "./portalMembership";

interface OrganizationProviderProps extends PropsWithChildren {
  accessToken?: string | null;
  fetchImpl?: typeof fetch;
  organizationLoader?: (
    options: LoadActivePortalOrganizationOptions,
  ) => Promise<PortalOrganization>;
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;
  session: PortalAuthenticatedSession;
}

export function OrganizationProvider({
  accessToken,
  children,
  fetchImpl,
  organizationLoader = loadActivePortalOrganization,
  runtimeConfig,
  session,
}: OrganizationProviderProps) {
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
  const [status, setStatus] = useState<OrganizationStatus>(
    sessionScope.auth_method === "portal_browser_session" ? "loading" : "ready",
  );
  const [members, setMembersState] = useState<OrganizationMemberSummary[]>([]);
  const [membersStatus, setMembersStatus] =
    useState<OrganizationMembersStatus>("idle");

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

  const setMembers = (nextMembers: OrganizationMemberSummary[]) => {
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
  const selectionStatus: OrganizationSelectionStatus =
    session.organization_context_status;

  const value = useMemo<OrganizationContextValue>(
    () => ({
      activeOrganization,
      apiClient,
      currentMembership,
      isTenantReady: selectionStatus === "active" && status === "ready",
      members,
      membersStatus,
      refresh,
      refreshMembers,
      selectionStatus,
      setActiveOrganization,
      setMembers,
      status,
    }),
    [
      activeOrganization,
      apiClient,
      currentMembership,
      members,
      membersStatus,
      selectionStatus,
      status,
    ],
  );

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  );
}
