import { useEffect, useMemo, useState } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalUsageBillingService,
  type PortalUsageBillingService,
  type PortalUsageBillingSnapshot,
} from "./portalUsageBilling";

export interface PortalUsageBillingController {
  error: string | null;
  isLoading: boolean;
  reload: () => Promise<void>;
  snapshot: PortalUsageBillingSnapshot | null;
}

export function usePortalUsageBilling(
  session: PortalAuthenticatedSession,
  serviceFactory?: (
    organization: ReturnType<typeof usePortalOrganization>,
  ) => PortalUsageBillingService,
): PortalUsageBillingController {
  const organization = usePortalOrganization();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [snapshot, setSnapshot] = useState<PortalUsageBillingSnapshot | null>(
    null,
  );

  const service = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalUsageBillingService(organization.apiClient),
    [organization, serviceFactory],
  );

  useEffect(() => {
    let isCancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const nextSnapshot = await service.loadSnapshot({
          organization: organization.activeOrganization,
          session,
        });
        if (!isCancelled) {
          setSnapshot(nextSnapshot);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setError(normalizeErrorMessage(caughtError));
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isCancelled = true;
    };
  }, [organization.activeOrganization, service, session]);

  const reload = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const nextSnapshot = await service.loadSnapshot({
        organization: organization.activeOrganization,
        session,
      });
      setSnapshot(nextSnapshot);
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
    } finally {
      setIsLoading(false);
    }
  };

  return {
    error,
    isLoading,
    reload,
    snapshot,
  };
}

function normalizeErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "The billing summary could not be loaded.";
}
