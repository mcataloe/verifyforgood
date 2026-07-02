import { useState } from "react";
import {
  DataTable,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  Panel,
  type DataTableColumn,
  type DataTableFilterDefinition,
} from "@charity-status/shared-ui";
import { Button, Group, Stack, Text, TextInput } from "@mantine/core";
import {
  DetailPageLayout,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { PortalNotice } from "../components/feedback";
import { PortalActionGroup } from "../components/PortalPrimitives";
import { PortalNonprofitDetailView } from "./PortalNonprofitDetailView";
import {
  usePortalNonprofitSearch,
  type PortalNonprofitSearchHistoryEntry,
  type PortalNonprofitSearchController,
} from "./usePortalNonprofitSearch";
import {
  normalizeEinQuery,
  type PortalNonprofitSearchSummary,
} from "./nonprofitSearch";

interface NonprofitSearchPanelProps {
  controller?: PortalNonprofitSearchController;
  onOpenDetail?: (ein: string) => void;
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
    key: "irs-status",
    header: "IRS status",
    render: (row) => `IRS status: ${row.irsStatus}`,
    sortValue: (row) => row.irsStatus,
    sortable: true,
  },
];

const resultFilters: DataTableFilterDefinition<PortalNonprofitSearchSummary>[] =
  [
    {
      key: "irs-status",
      label: "IRS status",
      options: [
        { label: "Active", value: "active" },
        { label: "Inactive", value: "inactive" },
        { label: "Unavailable", value: "unavailable" },
      ],
      getValue: (row) => row.irsStatus.toLowerCase(),
    },
  ];

const recentSearchColumns: DataTableColumn<PortalNonprofitSearchHistoryEntry>[] =
  [
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
      render: (row) =>
        row.searchMode === "ein" ? "EIN lookup" : "Name search",
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
  onOpenDetail,
}: NonprofitSearchPanelProps) {
  const defaultController = usePortalNonprofitSearch();
  const search = controller ?? defaultController;
  const [query, setQuery] = useState("");
  const stateFilters = Array.from(
    new Set(search.results.map((row) => row.state).filter(Boolean)),
  )
    .sort((left, right) => left.localeCompare(right))
    .map((value) => ({ label: value, value }));
  const filterDefinitions: DataTableFilterDefinition<PortalNonprofitSearchSummary>[] = [
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

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Search nonprofit records"
        subtitle="Use a nine-digit EIN for an exact profile or an organization name to review candidates."
      >
        <p>
          Searches use the current organization scope for{" "}
          <strong>{organization.activeOrganization.organization_name}</strong>.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const normalizedEin = normalizeEinQuery(query);
            if (normalizedEin && onOpenDetail) {
              onOpenDetail(normalizedEin);
              return;
            }
            void search.runSearch(query);
          }}
        >
          <label className="portal-form__field">
            <span>Organization name or EIN</span>
            <input
              aria-label="Organization name or EIN"
              className="portal-form__input"
              name="query"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="12-3456789 or Helping Hands Foundation"
              value={query}
            />
          </label>
          <div className="portal-form__actions">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={search.isLoading || !query.trim()}
              type="submit"
            >
              {search.isLoading ? "Searching..." : "Search organizations"}
            </button>
          </div>
        </form>
      </Panel>

      {search.error ? (
        <ErrorState description={search.error} title="Search unavailable" />
      ) : null}
      {search.isLoading ? (
        <LoadingSkeleton
          description="Waiting for nonprofit source records."
          title="Loading results"
          variant="table"
        />
      ) : null}
      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "ein" &&
      !search.detail ? (
        <EmptyState
          description="Check the EIN or search by organization name."
          title="No nonprofit record found"
        />
      ) : null}
      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "name" &&
      search.results.length === 0 ? (
        <EmptyState
          description="Broaden the organization name or use an exact EIN."
          title="No matching records"
        />
      ) : null}

      {search.results.length > 0 ? (
        <Panel
          title="Search results"
          subtitle="Open a result on its own shareable organization route."
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
                      if (onOpenDetail) onOpenDetail(row.ein);
                      else void search.viewResultDetail(row.ein);
                    }}
                    variant="light"
                  >
                    Open profile
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
                More matching source records are available.
              </Text>
              <Button
                loading={search.isLoadingMore}
                onClick={() => void search.loadMoreResults()}
                variant="light"
              >
                Load more results
              </Button>
            </Group>
          ) : null}
        </Panel>
      ) : null}

      {!onOpenDetail && search.detail ? (
        <PortalNonprofitDetailView detail={search.detail} />
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
