import { useEffect, useMemo, useState } from "react";
import {
  createApiClient,
  loadPricingPlanCatalog,
  type ApiClient,
} from "@charity-status/shared-api";
import type {
  FrontendRuntimeConfig,
  PricingPlanMetadata,
} from "@charity-status/shared-types";

export interface MarketingPricingPlansController {
  error: string | null;
  isLoading: boolean;
  plans: PricingPlanMetadata[];
  reload: () => Promise<void>;
}

export function useMarketingPricingPlans(
  runtimeConfig: Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">,
  apiClient?: Pick<ApiClient, "get">,
): MarketingPricingPlansController {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [plans, setPlans] = useState<PricingPlanMetadata[]>([]);

  const client = useMemo(
    () => apiClient ?? createApiClient({ runtimeConfig }),
    [apiClient, runtimeConfig],
  );

  useEffect(() => {
    let isCancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const catalog = await loadPricingPlanCatalog(client);
        if (!isCancelled) {
          setPlans(catalog.plans);
        }
      } catch {
        if (!isCancelled) {
          setError("The pricing catalog could not be loaded.");
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
  }, [client]);

  const reload = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const catalog = await loadPricingPlanCatalog(client);
      setPlans(catalog.plans);
    } catch {
      setError("The pricing catalog could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  };

  return {
    error,
    isLoading,
    plans,
    reload,
  };
}
