import { useState } from "react";
import {
  DataTable,
  EmptyState,
  ErrorState,
  Grid,
  LoadingSkeleton,
  Panel,
  StatusBadge,
  type DataTableColumn,
  type DataTableFilterDefinition,
} from "@charity-status/shared-ui";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  PortalNonprofitDetailView,
  summaryStatus,
} from "./PortalNonprofitDetailView";
import {
  usePortalNonprofitSearch,
  type PortalNonprofitSearchController,
} from "./usePortalNonprofitSearch";
import type { PortalNonprofitSearchSummary } from "./nonprofitSearch";

interface NonprofitSearchPanelProps {
  controller?: PortalNonprofitSearchController;
}

const resultColumns: DataTableColumn<PortalNonprofitSearchSummary>[] = [
  {
    key: "name",
    header: "Organization",
    sortable: true,
    render: (row) => row.name,
    sortValue: (row) => row.name,
  },
  {
    key: "ein",
    header: "EIN",
    sortable: true,
    render: (row) => row.ein,
    sortValue: (row) => row.ein,
  },
  {
    key: "state",
    header: "State",
    sortable: true,
    render: (row) => row.state,
    sortValue: (row) => row.state,
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusBadge status={summaryStatus(row)} />,
    sortValue: (row) => summaryStatus(row),
    sortable: true,
  },
];

const resultFilters: DataTableFilterDefinition<PortalNonprofitSearchSummary>[] = [
  {
    key: "status",
    label: "Status",
    options: [
      { label: "Verified", value: "verified" },
      { label: "Pending", value: "pending" },
      { label: "Flagged", value: "flagged" },
      { label: "Inactive", value: "inactive" },
    ],
    getValue: (row) => summaryStatus(row),
  },
  {
    key: "state",
    label: "State",
    options: [
      { label: "California", value: "CA" },
      { label: "Illinois", value: "IL" },
      { label: "New York", value: "NY" },
      { label: "Texas", value: "TX" },
    ],
    getValue: (row) => row.state,
  },
];

export function NonprofitSearchPanel({
  controller,
}: NonprofitSearchPanelProps) {
  const organization = usePortalOrganization();
  const defaultController = usePortalNonprofitSearch();
  const search = controller ?? defaultController;
  const [query, setQuery] = useState("");

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Nonprofit verification search"
        subtitle="Search by EIN for an exact lookup or by organization name for a lightweight listing."
      >
        <p>
          This is the portal&apos;s core product interaction. Requests run
          through the organization-scoped portal API client for{" "}
          <strong>{organization.activeOrganization.organization_name}</strong>.
        </p>

        <form
          className="portal-form"
          onSubmit={(event) => {
            event.preventDefault();
            void search.runSearch(query);
          }}
        >
          <label className="portal-form__field">
            <span>Search query</span>
            <input
              aria-label="Search query"
              className="portal-form__input"
              name="query"
              onChange={(event) => {
                setQuery(event.target.value);
              }}
              placeholder="12-3456789 or Helping Hands Foundation"
              type="text"
              value={query}
            />
          </label>

          <div className="portal-form__actions">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={search.isLoading || !query.trim()}
              type="submit"
            >
              {search.isLoading ? "Searching..." : "Search nonprofit"}
            </button>
          </div>
        </form>

        <dl className="portal-shell__details">
          <div>
            <dt>Search mode</dt>
            <dd>{search.searchMode ?? "Not run yet"}</dd>
          </div>
          <div>
            <dt>Last query</dt>
            <dd>{search.lastQuery || "None"}</dd>
          </div>
          <div>
            <dt>Workspace</dt>
            <dd>{organization.activeOrganization.workspace_id}</dd>
          </div>
        </dl>
      </Panel>

      {search.error ? (
        <ErrorState
          description={search.error}
          title="Nonprofit lookup unavailable"
        />
      ) : null}

      {search.isLoading ? (
        <LoadingSkeleton
          description="Waiting on the backend nonprofit endpoints."
          title="Loading nonprofit results"
          variant="table"
        />
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "ein" &&
      !search.detail ? (
        <EmptyState
          description="Try another EIN or switch to a name-based search if you are still narrowing the candidate organization."
          title="No nonprofit found"
        />
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "name" &&
      search.results.length === 0 ? (
        <EmptyState
          description="Try broadening the organization name or run an exact EIN lookup for a more deterministic result."
          title="No nonprofit matches"
        />
      ) : null}

      {search.results.length > 0 ? (
        <Panel
          title="Search results"
          subtitle="Refine the result set and open an entity detail view from the shared review layout."
        >
          <DataTable
            columns={[
              ...resultColumns,
              {
                key: "actions",
                header: "Actions",
                render: (row) => (
                  <button
                    className="portal-shell__action"
                    onClick={() => {
                      void search.viewResultDetail(row.ein);
                    }}
                    type="button"
                  >
                    View details
                  </button>
                ),
              },
            ]}
            filterDefinitions={resultFilters}
            getSearchText={(row) =>
              `${row.name} ${row.ein} ${row.state} ${row.irsStatus}`
            }
            rows={search.results}
            searchPlaceholder="Refine search results"
          />
        </Panel>
      ) : null}

      {search.detail ? (
        <PortalNonprofitDetailView detail={search.detail} />
      ) : null}
    </Grid>
  );
}
