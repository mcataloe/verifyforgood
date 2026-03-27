import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { OrganizationProvider } from "./OrganizationProvider";
import {
  loadActivePortalOrganization,
  type LoadActivePortalOrganizationOptions,
  type PortalOrganization,
} from "./portalOrganization";

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
  return (
    <OrganizationProvider
      accessToken={accessToken}
      fetchImpl={fetchImpl}
      organizationLoader={organizationLoader}
      runtimeConfig={runtimeConfig}
      session={session}
    >
      {children}
    </OrganizationProvider>
  );
}
