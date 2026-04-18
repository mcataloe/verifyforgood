import { useState } from "react";
import {
  DataTable,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Panel,
  StatusBadge,
  type DataTableColumn,
  type DataTableFilterDefinition,
} from "@charity-status/shared-ui";
import { Button, Group, Text } from "@mantine/core";
import {
  DetailPageLayout,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  PortalNonprofitDetailView,
  summaryStatus,
} from "./PortalNonprofitDetailView";
import {
  usePortalNonprofitSearch,
  type PortalNonprofitSearchHistoryEntry,
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
];

const recentSearchColumns: DataTableColumn<PortalNonprofitSearchHistoryEntry>[] = [
  {
    key: "query",
    header: "Query",
    sortable: true,
    render: (row) => row.query,
    sortValue: (row) => row.query,
  },
  {
    key: "search-mode",
    header: "Search method",
    sortable: true,
    render: (row) => (row.searchMode === "ein" ? "EIN lookup" : "Name search"),
    sortValue: (row) => row.searchMode,
  },
  {
    key: "outcome",
    header: "Outcome",
    sortable: true,
    render: (row) => describeRecentSearchOutcome(row),
    sortValue: (row) => describeRecentSearchOutcome(row),
  },
  {
    key: "searched-at",
    header: "Searched",
    sortable: true,
    render: (row) => formatSearchTimestamp(row.searchedAt),
    sortValue: (row) => row.searchedAt,
  },
];

export function NonprofitSearchPanel({
  controller,
}: NonprofitSearchPanelProps) {
  const organization = usePortalOrganization();
  const defaultController = usePortalNonprofitSearch();
  const search = controller ?? defaultController;
  const [query, setQuery] = useState("");
  const stateFilters = Array.from(
    new Set(search.results.map((row) => row.state).filter(Boolean)),
  )
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({
      label: value,
      value,
    }));
  const filterDefinitions: DataTableFilterDefinition<PortalNonprofitSearchSummary>[] =
    [
      ...resultFilters,
      ...(stateFilters.length
        ? [
            {
              key: "state",
              label: "State",
              options: stateFilters,
              getValue: (row: PortalNonprofitSearchSummary) => row.state,
            },
          ]
        : []),
    ];
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const runSearchForQuery = (nextQuery: string) => {
    const trimmedQuery = nextQuery.trim();
    setQuery(nextQuery);

    if (!trimmedQuery) {
      setValidationMessage("Enter an EIN or organization name to search.");
      return;
    }

    setValidationMessage(null);
    void search.runSearch(trimmedQuery);
  };

  return (
    <DetailPageLayout>
      <SectionBlock>
        <Panel
          title="Nonprofit verification search"
          subtitle="Search by EIN for an exact lookup or by organization name to review matching nonprofits."
        >
          <p>
            Search and review nonprofit records for{" "}
            <strong>{organization.activeOrganization.organization_name}</strong>.
          </p>

          <form
            className="portal-form portal-form--detail"
            onSubmit={(event) => {
              event.preventDefault();
              runSearchForQuery(query);
            }}
          >
            <label className="portal-form__field">
              <span>Search query</span>
              <input
                aria-label="Search query"
                className="portal-form__input"
                name="query"
                onChange={(event) => {
                  if (validationMessage) {
                    setValidationMessage(null);
                  }
                  setQuery(event.target.value);
                }}
                placeholder="12-3456789 or Helping Hands Foundation"
                type="text"
                value={query}
              />
            </label>

            {validationMessage ? (
              <p className="portal-feedback portal-feedback--error">
                {validationMessage}
              </p>
            ) : null}

            <div className="portal-form__actions">
              <button
                className="portal-shell__action portal-shell__action--primary"
                disabled={search.isLoading}
                type="submit"
              >
                {search.isLoading ? "Searching..." : "Search nonprofit"}
              </button>
            </div>
          </form>
        </Panel>
      </SectionBlock>

      {search.error ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <ErrorState
              description={search.error}
              title="Nonprofit lookup unavailable"
            />
          </SectionBlock>
        </>
      ) : null}

      {search.isLoading ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <LoadingSkeleton
              description="Fetching nonprofit results."
              title="Loading nonprofit results"
              variant="table"
            />
          </SectionBlock>
        </>
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "ein" &&
      !search.detail ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <EmptyState
              description="Try another EIN or switch to a name-based search if you are still narrowing the candidate organization."
              title="No nonprofit found"
            />
          </SectionBlock>
        </>
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "name" &&
      search.results.length === 0 ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <EmptyState
              description="Try broadening the organization name or run an exact EIN lookup for a more deterministic result."
              title="No nonprofit matches"
            />
          </SectionBlock>
        </>
      ) : null}

      {search.results.length > 0 ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <Panel
              title="Search results"
              subtitle="Refine the results and open the organization you want to review."
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
                filterDefinitions={filterDefinitions}
                getSearchText={(row) =>
                  `${row.name} ${row.ein} ${row.state} ${row.irsStatus}`
                }
                rows={search.results}
                searchPlaceholder="Refine search results"
              />
              {search.hasMoreResults ? (
                <Group justify="space-between" mt="md" wrap="wrap">
                  <Text c="dimmed" fz="sm">
                    More matching results are available for this search.
                  </Text>
                  <Button
                    loading={search.isLoadingMore}
                    onClick={() => {
                      void search.loadMoreResults();
                    }}
                    variant="light"
                  >
                    Load more results
                  </Button>
                </Group>
              ) : null}
            </Panel>
          </SectionBlock>
        </>
      ) : null}

      {search.detail ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <PortalNonprofitDetailView detail={search.detail} />
          </SectionBlock>
        </>
      ) : null}

      {search.recentSearches.length > 0 ? (
        <>
          <SectionDivider />
          <SectionBlock>
            <Panel
              title="Recent searches"
              subtitle="Review earlier nonprofit searches and rerun one with a single click."
            >
              <DataTable
                ariaLabel="Recent nonprofit searches"
                columns={[
                  ...recentSearchColumns,
                  {
                    key: "actions",
                    header: "Action",
                    render: (row) => (
                      <button
                        className="portal-shell__action"
                        disabled={search.isLoading}
                        onClick={() => {
                          runSearchForQuery(row.query);
                        }}
                        type="button"
                      >
                        Run again
                      </button>
                    ),
                  },
                ]}
                pageSize={5}
                rows={search.recentSearches}
                searchPlaceholder="Filter recent searches"
              />
            </Panel>
          </SectionBlock>
        </>
      ) : null}
    </DetailPageLayout>
  );
}

function describeRecentSearchOutcome(
  row: PortalNonprofitSearchHistoryEntry,
): string {
  if (row.outcome === "match_found") {
    return "1 nonprofit found";
  }
  if (row.outcome === "no_match") {
    return "No nonprofit found";
  }
  if (row.outcome === "results_loaded") {
    return `${row.resultsCount ?? 0} matches loaded`;
  }
  if (row.outcome === "no_results") {
    return "No matches found";
  }
  return "Search failed";
}

function formatSearchTimestamp(value: string): string {
  const parsedValue = Date.parse(value);
  if (Number.isNaN(parsedValue)) {
    return value;
  }

  return new Date(parsedValue).toLocaleString();
}
