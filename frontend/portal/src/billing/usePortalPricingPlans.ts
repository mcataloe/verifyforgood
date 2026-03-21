import { useEffect, useMemo, useState } from "react";
import {
  loadPricingPlanCatalog,
  type ApiClient,
} from "@charity-status/shared-api";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import type { PortalUsageBillingSnapshot } from "./portalUsageBilling";

export interface PortalPricingPlanItem {
  highlighted: boolean;
  isCurrent: boolean;
  isEffective: boolean;
  isPending: boolean;
  plan: PricingPlanMetadata;
}

export interface PortalPricingPlansController {
  error: string | null;
  isLoading: boolean;
  plans: PortalPricingPlanItem[];
  reload: () => Promise<void>;
}

export function usePortalPricingPlans(
  snapshot: PortalUsageBillingSnapshot | null,
  apiClientOverride?: Pick<ApiClient, "get">,
): PortalPricingPlansController {
  const organization = usePortalOrganization();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [plans, setPlans] = useState<PricingPlanMetadata[]>([]);

  const apiClient = useMemo(
    () => apiClientOverride ?? organization.apiClient,
    [apiClientOverride, organization.apiClient],
  );

  useEffect(() => {
    let isCancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const catalog = await loadPricingPlanCatalog(apiClient);
        if (!isCancelled) {
          setPlans(catalog.plans);
        }
      } catch {
        if (!isCancelled) {
          setError("The pricing plan catalog could not be loaded.");
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
  }, [apiClient]);

  const reload = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const catalog = await loadPricingPlanCatalog(apiClient);
      setPlans(catalog.plans);
    } catch {
      setError("The pricing plan catalog could not be loaded.");
    } finally {
      setIsLoading(false);
    }
  };

  return {
    error,
    isLoading,
    plans: plans.map((plan) => ({
      highlighted: Boolean(
        snapshot &&
        (plan.plan_code === snapshot.plan ||
          plan.plan_code === snapshot.effectiveAccessPlan ||
          plan.plan_code === snapshot.pendingDowngradePlan),
      ),
      isCurrent: snapshot?.plan === plan.plan_code,
      isEffective: snapshot?.effectiveAccessPlan === plan.plan_code,
      isPending: snapshot?.pendingDowngradePlan === plan.plan_code,
      plan,
    })),
    reload,
  };
}
