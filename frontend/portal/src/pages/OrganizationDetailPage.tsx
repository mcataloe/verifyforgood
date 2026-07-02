import { EmptyState, ErrorState, LoadingSkeleton } from "@charity-status/shared-ui";
import { useEffect } from "react";
import {
  buildOrganizationPortalHash,
  navigateToPortalRoute,
  organizationsPortalRoute,
  type OrganizationDetailSection,
} from "../app/portalRoutes";
import { PortalNonprofitDetailView } from "../nonprofits/PortalNonprofitDetailView";
import { usePortalNonprofitSearch } from "../nonprofits/usePortalNonprofitSearch";

export function OrganizationDetailPage({
  ein,
  section,
}: {
  ein: string;
  section: OrganizationDetailSection;
}) {
  const search = usePortalNonprofitSearch();
  const loadDetail = search.viewResultDetail;

  useEffect(() => {
    void loadDetail(ein);
  }, [ein, loadDetail]);

  return (
    <div className="portal-dashboard">
      <nav aria-label="Breadcrumb">
        <a href={organizationsPortalRoute.hash}>Organizations</a>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">EIN {ein}</span>
      </nav>
      {search.isLoading ? (
        <LoadingSkeleton
          description="Loading the selected nonprofit record and filing context."
          title="Loading organization profile"
          variant="detail"
        />
      ) : null}
      {search.error ? (
        <ErrorState
          description={search.error}
          title="Organization profile unavailable"
        />
      ) : null}
      {!search.isLoading && !search.error && search.detail ? (
        <PortalNonprofitDetailView
          activeSection={section}
          detail={search.detail}
          onSectionChange={(nextSection) => {
            navigateToPortalRoute(buildOrganizationPortalHash(ein, nextSection));
          }}
        />
      ) : null}
      {!search.isLoading && !search.error && !search.detail ? (
        <EmptyState
          description="Return to organization search and confirm the EIN."
          title="No organization profile found"
        />
      ) : null}
    </div>
  );
}
