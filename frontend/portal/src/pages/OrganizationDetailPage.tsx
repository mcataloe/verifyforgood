import { EmptyState, ErrorState, LoadingSkeleton } from "@charity-status/shared-ui";
import { useEffect, useState } from "react";
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
  const [requestedEin, setRequestedEin] = useState<string | null>(null);

  useEffect(() => {
    setRequestedEin(ein);
    void loadDetail(ein);
  }, [ein, loadDetail]);

  const isInitialLoad = requestedEin !== ein && !search.error && !search.detail;

  return (
    <div className="portal-dashboard">
      <nav aria-label="Breadcrumb">
        <a href={organizationsPortalRoute.hash}>Organizations</a>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">EIN {ein}</span>
      </nav>
      {search.isLoading || isInitialLoad ? (
        <LoadingSkeleton
          description="Loading the selected nonprofit record and filing context."
          title="Loading organization profile"
          variant="card"
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
      {!search.isLoading && !isInitialLoad && !search.error && !search.detail ? (
        <EmptyState
          description="Return to organization search and confirm the EIN."
          title="No organization profile found"
        />
      ) : null}
    </div>
  );
}
