import { apiEndpoints } from "@charity-status/shared-api";
import { useState } from "react";
import { normalizePortalError } from "../lib/portalError";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { usePortalAuth } from "../auth/usePortalAuth";

export interface PortalOrganizationDeletionController {
  deleteOrganization: (input: { slug: string }) => Promise<boolean>;
  error: string | null;
  isDeleting: boolean;
  organizationName: string;
  organizationSlug: string | null;
}

export function usePortalOrganizationDeletion(): PortalOrganizationDeletionController {
  const auth = usePortalAuth();
  const organization = usePortalOrganization();
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  return {
    deleteOrganization: async ({ slug }) => {
      setIsDeleting(true);
      setError(null);

      try {
        await organization.apiClient.requestData<
          {
            deleted: boolean;
            organization: {
              organization_id: string;
            };
          },
          { slug: string }
        >(apiEndpoints.organization.deleteCurrent, {
          body: {
            slug,
          },
          method: "DELETE",
        });
        auth.removeOrganization(organization.activeOrganization.organization_id ?? "");
        return true;
      } catch (caughtError) {
        setError(
          normalizePortalError(
            caughtError,
            "The organization could not be deleted.",
          ),
        );
        return false;
      } finally {
        setIsDeleting(false);
      }
    },
    error,
    isDeleting,
    organizationName: organization.activeOrganization.organization_name,
    organizationSlug: organization.activeOrganization.slug ?? null,
  };
}
