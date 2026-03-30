import { useEffect, useMemo, useState } from "react";
import {
  ApiRequestError,
  apiEndpoints,
  buildApiUrl,
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
  runtimeConfig: Pick<
    FrontendRuntimeConfig,
    "apiBaseUrl" | "apiVersion" | "environment"
  >,
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
      } catch (error) {
        reportPricingCatalogFailure(error, runtimeConfig);
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
    } catch (error) {
      reportPricingCatalogFailure(error, runtimeConfig);
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

function reportPricingCatalogFailure(
  error: unknown,
  runtimeConfig: Pick<
    FrontendRuntimeConfig,
    "apiBaseUrl" | "apiVersion" | "environment"
  >,
): void {
  if (runtimeConfig.environment !== "development") {
    return;
  }

  const targetUrl = buildApiUrl(apiEndpoints.public.plans, runtimeConfig);
  const apiError = error instanceof ApiRequestError ? error : null;
  let hint: string | null = null;

  if (!runtimeConfig.apiBaseUrl) {
    hint =
      "VITE_API_BASE_URL is unset, so marketing is requesting the plan catalog from the Vite dev origin instead of the API.";
  } else if (apiError?.status === 404) {
    hint =
      "The configured API responded with 404 for GET /v1/plans. Verify the API base URL and deployed route.";
  } else {
    hint =
      "If this request targets the AWS dev API from http://localhost:5174, confirm that CORS_ALLOWED_ORIGINS allows the marketing dev origin.";
  }

  console.error("Marketing pricing catalog request failed", {
    code: apiError?.code ?? null,
    hint,
    requestId: apiError?.requestId ?? null,
    status: apiError?.status ?? null,
    targetUrl,
  });
}
