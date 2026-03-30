import { useEffect, useMemo, useState } from "react";
import { normalizePortalError } from "../lib/portalError";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalSupportService,
  type PortalOrganizationSupportContext,
  type PortalSupportRequestInput,
  type PortalSupportRequestReceipt,
  type PortalSupportService,
} from "./portalSupport";

export interface PortalSupportController {
  clearReceipt: () => void;
  context: PortalOrganizationSupportContext | null;
  error: string | null;
  isLoading: boolean;
  isSubmitting: boolean;
  receipt: PortalSupportRequestReceipt | null;
  reload: () => Promise<void>;
  submit: (input: PortalSupportRequestInput) => Promise<void>;
}

export function usePortalSupport(
  serviceFactory?: (
    organization: ReturnType<typeof usePortalOrganization>,
  ) => PortalSupportService,
): PortalSupportController {
  const organization = usePortalOrganization();
  const [context, setContext] = useState<PortalOrganizationSupportContext | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [receipt, setReceipt] = useState<PortalSupportRequestReceipt | null>(null);

  const service = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalSupportService(organization.apiClient),
    [organization, serviceFactory],
  );

  useEffect(() => {
    let isCancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const nextContext = await service.getSupportContext();
        if (!isCancelled) {
          setContext(nextContext);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setError(
            normalizePortalError(
              caughtError,
              "Support details could not be loaded.",
            ),
          );
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
  }, [service]);

  return {
    clearReceipt: () => setReceipt(null),
    context,
    error,
    isLoading,
    isSubmitting,
    receipt,
    reload: async () => {
      setIsLoading(true);
      setError(null);
      try {
        setContext(await service.getSupportContext());
      } catch (caughtError) {
        setError(
          normalizePortalError(
            caughtError,
            "Support details could not be loaded.",
          ),
        );
      } finally {
        setIsLoading(false);
      }
    },
    submit: async (input) => {
      setIsSubmitting(true);
      setError(null);
      setReceipt(null);
      try {
        setReceipt(await service.submitSupportRequest(input));
      } catch (caughtError) {
        setError(
          normalizePortalError(
            caughtError,
            "Support request could not be submitted.",
          ),
        );
        throw caughtError;
      } finally {
        setIsSubmitting(false);
      }
    },
  };
}
