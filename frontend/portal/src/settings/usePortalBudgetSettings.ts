import { apiEndpoints } from "@charity-status/shared-api";
import { useState } from "react";
import { normalizePortalError } from "../lib/portalError";
import { usePortalOrganization } from "../organization/usePortalOrganization";

export interface PortalBudgetSettings {
  allowOverage: boolean;
  monthlyRequestCap: number | null;
  updatedAt: string | null;
}

export interface SavePortalBudgetSettingsInput {
  allowOverage: boolean;
  monthlyRequestCap: number | null;
}

export interface PortalBudgetSettingsController {
  clearNotice: () => void;
  error: string | null;
  isLoading: boolean;
  isSaving: boolean;
  notice: string | null;
  save: (input: SavePortalBudgetSettingsInput) => Promise<void>;
  settings: PortalBudgetSettings;
}

export function usePortalBudgetSettings(): PortalBudgetSettingsController {
  const organization = usePortalOrganization();
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  return {
    clearNotice: () => setNotice(null),
    error,
    isLoading: organization.status === "loading",
    isSaving,
    notice,
    save: async (input) => {
      setIsSaving(true);
      setError(null);
      setNotice(null);

      try {
        await organization.apiClient.put(
          apiEndpoints.organization.updateSettings,
          {
            body: {
              billing: {
                allowOverage: input.allowOverage,
                monthlyRequestCap: input.monthlyRequestCap,
              },
            },
          },
        );
        await organization.refresh();
        setNotice("Budget controls saved.");
      } catch (caughtError) {
        setError(
          normalizePortalError(
            caughtError,
            "Budget controls could not be saved.",
          ),
        );
      } finally {
        setIsSaving(false);
      }
    },
    settings: {
      allowOverage:
        organization.activeOrganization.billing_allow_overage ?? true,
      monthlyRequestCap:
        organization.activeOrganization.billing_monthly_request_cap,
      updatedAt: organization.activeOrganization.updated_at,
    },
  };
}
