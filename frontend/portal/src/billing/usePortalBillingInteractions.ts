import { useMemo, useState } from "react";
import type { BillingInteractions } from "./billingInteractions";
import { createBackendBillingInteractions } from "./billingInteractions";
import { normalizePortalError } from "../lib/portalError";
import { usePortalOrganization } from "../organization/usePortalOrganization";

export interface PortalBillingInteractionsController extends BillingInteractions {
  clearError: () => void;
  error: string | null;
  isPending: boolean;
}

export function usePortalBillingInteractions(
  override?: BillingInteractions,
): PortalBillingInteractionsController {
  const organization = usePortalOrganization();
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const interactions = useMemo(
    () => override ?? createBackendBillingInteractions(organization.apiClient),
    [organization.apiClient, override],
  );

  return {
    clearError: () => setError(null),
    error,
    isPending,
    async cancelSubscription(input) {
      setIsPending(true);
      setError(null);
      try {
        return await interactions.cancelSubscription(input);
      } catch (caughtError) {
        const message = normalizePortalError(
          caughtError,
          "The billing action could not be completed.",
        );
        setError(message);
        throw caughtError;
      } finally {
        setIsPending(false);
      }
    },
    async createSubscription(input) {
      setIsPending(true);
      setError(null);
      try {
        return await interactions.createSubscription(input);
      } catch (caughtError) {
        const message = normalizePortalError(
          caughtError,
          "The billing action could not be completed.",
        );
        setError(message);
        throw caughtError;
      } finally {
        setIsPending(false);
      }
    },
    async updatePlan(input) {
      setIsPending(true);
      setError(null);
      try {
        return await interactions.updatePlan(input);
      } catch (caughtError) {
        const message = normalizePortalError(
          caughtError,
          "The billing action could not be completed.",
        );
        setError(message);
        throw caughtError;
      } finally {
        setIsPending(false);
      }
    },
  };
}
