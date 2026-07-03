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
    header: "Nonprofit",
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
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );
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

  const runSearchForQuery = (nextQuery: string) => {
    const trimmedQuery = nextQuery.trim();
    setQuery(nextQuery);

    if (!trimmedQuery) {
      setValidationMessage("Enter an EIN or organization name to search.");
      return;
    }

    const normalizedEin = normalizeEinQuery(trimmedQuery);
    if (normalizedEin && onOpenDetail) {
      setValidationMessage(null);
      onOpenDetail(normalizedEin);
      return;
    }

    setValidationMessage(null);
    void search.runSearch(trimmedQuery);
  };

  if (!onOpenDetail && search.isDetailOpen && search.detail) {
    return (
      <PortalNonprofitDetailView
        detail={search.detail}
        onBackToSearch={search.closeDetail}
      />
    );
  }

  return (
    <DetailPageLayout>
      <SectionBlock>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            runSearchForQuery(query);
          }}
        >
          <Stack gap="md" maw={540}>
            <TextInput
              aria-label="Search query"
              label="Search query"
              name="query"
              onChange={(event) => {
                if (validationMessage) {
                  setValidationMessage(null);
                }
                setQuery(event.target.value);
              }}
              placeholder="12-3456789 or Helping Hands Foundation"
              value={query}
            />

            {validationMessage ? (
              <PortalNotice tone="error">
                <p>{validationMessage}</p>
              </PortalNotice>
            ) : null}

            <PortalActionGroup>
              <Button
                disabled={search.isLoading}
                loading={search.isLoading}
                type="submit"
              >
                {search.isLoading ? "Searching..." : "Search nonprofit"}
              </Button>
            </PortalActionGroup>
          </Stack>
        </form>
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
                      <Button
                        onClick={() => {
                          if (onOpenDetail) onOpenDetail(row.ein);
                          else void search.viewResultDetail(row.ein);
                        }}
                        size="xs"
                        type="button"
                        variant="light"
                      >
                        View details
                      </Button>
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
                      <Button
                        disabled={search.isLoading}
                        onClick={() => {
                          runSearchForQuery(row.query);
                        }}
                        size="xs"
                        type="button"
                        variant="light"
                      >
                        Run again
                      </Button>
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
