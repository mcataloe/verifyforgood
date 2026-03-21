import type { PricingPlanCatalogResponse } from "@charity-status/shared-types";
import { apiEndpoints } from "./endpoints";
import type { ApiClient } from "./request";

export async function loadPricingPlanCatalog(
  apiClient: Pick<ApiClient, "get">,
): Promise<PricingPlanCatalogResponse> {
  return apiClient.get<PricingPlanCatalogResponse>(apiEndpoints.public.plans);
}
