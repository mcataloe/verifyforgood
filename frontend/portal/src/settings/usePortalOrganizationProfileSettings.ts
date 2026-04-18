import { apiEndpoints } from "@charity-status/shared-api";
import { useState } from "react";
import { normalizePortalError } from "../lib/portalError";
import { usePortalAuth } from "../auth/usePortalAuth";
import {
  mapSettingsToPortalOrganization,
  type PortalOrganizationSettingsDocument,
} from "../organization/portalOrganization";
import { usePortalOrganization } from "../organization/usePortalOrganization";

export interface PortalOrganizationProfileSettings {
  contactEmail: string;
  displayName: string;
  slug: string | null;
  updatedAt: string | null;
}

export interface SavePortalOrganizationProfileSettingsInput {
  contactEmail: string;
  displayName: string;
  slug: string;
}

export interface PortalOrganizationProfileSettingsController {
  clearNotice: () => void;
  error: string | null;
  isLoading: boolean;
  isSaving: boolean;
  notice: string | null;
  save: (input: SavePortalOrganizationProfileSettingsInput) => Promise<void>;
  settings: PortalOrganizationProfileSettings;
}

export function usePortalOrganizationProfileSettings(): PortalOrganizationProfileSettingsController {
  const auth = usePortalAuth();
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
        const settings = await organization.apiClient.put<
          PortalOrganizationSettingsDocument,
          {
            organization: {
              contactEmail: string | null;
              displayName: string;
              slug: string;
            };
          }
        >(apiEndpoints.organization.updateSettings, {
          body: {
            organization: {
              contactEmail: input.contactEmail.trim() || null,
              displayName: input.displayName,
              slug: input.slug.trim(),
            },
          },
        });
        const nextOrganization = mapSettingsToPortalOrganization({
          session: {
            account_id: organization.activeOrganization.account_id,
            auth_method: "portal_browser_session",
            organization_context_status: organization.selectionStatus,
            organization_name: organization.activeOrganization.organization_name,
            workspace_id: organization.activeOrganization.workspace_id,
          },
          settings,
        });
        organization.setActiveOrganization(nextOrganization);
        if (organization.currentMembership && nextOrganization.organization_id) {
          auth.applyOrganization({
            account_id: nextOrganization.account_id,
            membership: {
              role: organization.currentMembership.role,
              status: organization.currentMembership.status,
              user_id: organization.currentMembership.user_id,
            },
            organization_id: nextOrganization.organization_id,
            organization_name: nextOrganization.organization_name,
            slug:
              nextOrganization.slug ??
              organization.activeOrganization.slug ??
              "",
            workspace_id: nextOrganization.workspace_id,
          });
        }
        setNotice("Organization profile saved.");
      } catch (caughtError) {
        setError(
          normalizePortalError(
            caughtError,
            "Organization profile could not be saved.",
          ),
        );
      } finally {
        setIsSaving(false);
      }
    },
    settings: {
      contactEmail: organization.activeOrganization.contact_email ?? "",
      displayName: organization.activeOrganization.organization_name,
      slug: organization.activeOrganization.slug ?? null,
      updatedAt:
        organization.activeOrganization.organization_updated_at ??
        organization.activeOrganization.updated_at,
    },
  };
}
