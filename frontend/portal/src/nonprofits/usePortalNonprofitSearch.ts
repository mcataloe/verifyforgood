import { useCallback, useMemo, useState } from "react";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalNonprofitSearchService,
  looksLikeEinQuery,
  type PortalNonprofitDetail,
  type PortalNonprofitSearchPage,
  type PortalNonprofitSearchService,
  type PortalNonprofitSearchSummary,
} from "./nonprofitSearch";
import { normalizePortalError } from "../lib/portalError";

export interface PortalNonprofitSearchController {
  closeDetail: () => void;
  detail: PortalNonprofitDetail | null;
  error: string | null;
  hasSearched: boolean;
  hasMoreResults: boolean;
  isDetailOpen: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  lastQuery: string;
  recentSearches: PortalNonprofitSearchHistoryEntry[];
  loadMoreResults: () => Promise<void>;
  results: PortalNonprofitSearchSummary[];
  runSearch: (query: string) => Promise<void>;
  searchMode: "ein" | "name" | null;
  viewResultDetail: (ein: string) => Promise<void>;
}

export interface PortalNonprofitSearchHistoryEntry {
  id: string;
  outcome:
    | "match_found"
    | "no_match"
    | "results_loaded"
    | "no_results"
    | "failed";
  query: string;
  resultsCount: number | null;
  searchMode: "ein" | "name";
  searchedAt: string;
}

export function usePortalNonprofitSearch(
  serviceFactory?: (
    organization: ReturnType<typeof usePortalOrganization>,
  ) => PortalNonprofitSearchService,
): PortalNonprofitSearchController {
  const organization = usePortalOrganization();
  const [detail, setDetail] = useState<PortalNonprofitDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [hasMoreResults, setHasMoreResults] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<
    PortalNonprofitSearchHistoryEntry[]
  >([]);
  const [results, setResults] = useState<PortalNonprofitSearchSummary[]>([]);
  const [searchMode, setSearchMode] = useState<"ein" | "name" | null>(null);

  const service = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalNonprofitSearchService(organization.apiClient),
    [organization, serviceFactory],
  );

  const runSearch = useCallback(
    async (query: string) => {
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        return;
      }
      const inferredSearchMode: "ein" | "name" = looksLikeEinQuery(trimmedQuery)
        ? "ein"
        : "name";

      setHasSearched(true);
      setIsLoading(true);
      setIsLoadingMore(false);
      setError(null);
      setLastQuery(trimmedQuery);
      setNextCursor(null);
      setHasMoreResults(false);

      try {
        if (inferredSearchMode === "ein") {
          const nonprofitDetail = await service.lookupByEin(trimmedQuery);
          setDetail(nonprofitDetail);
          setResults([]);
          setIsDetailOpen(nonprofitDetail !== null);
          setSearchMode("ein");
          setRecentSearches((current) =>
            prependSearchHistory(current, {
              outcome: nonprofitDetail ? "match_found" : "no_match",
              query: trimmedQuery,
              resultsCount: nonprofitDetail ? 1 : 0,
              searchMode: "ein",
            }),
          );
          if (!nonprofitDetail) {
            setError(null);
          }
          return;
        }

        const searchResults = await service.searchByName(trimmedQuery);
        setDetail(null);
        setIsDetailOpen(false);
        setResults(searchResults.items);
        setNextCursor(searchResults.nextCursor);
        setHasMoreResults(Boolean(searchResults.nextCursor));
        setSearchMode("name");
        setRecentSearches((current) =>
          prependSearchHistory(current, {
            outcome: searchResults.items.length ? "results_loaded" : "no_results",
            query: trimmedQuery,
            resultsCount: searchResults.items.length,
            searchMode: "name",
          }),
        );
      } catch (caughtError) {
        setDetail(null);
        setIsDetailOpen(false);
        setResults([]);
        setNextCursor(null);
        setHasMoreResults(false);
        setError(normalizeErrorMessage(caughtError));
        setRecentSearches((current) =>
          prependSearchHistory(current, {
            outcome: "failed",
            query: trimmedQuery,
            resultsCount: null,
            searchMode: inferredSearchMode,
          }),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [service],
  );

  const viewResultDetail = useCallback(
    async (ein: string) => {
      setIsLoading(true);
      setError(null);

      try {
        const nonprofitDetail = await service.lookupByEin(ein);
        setDetail(nonprofitDetail);
        setIsDetailOpen(nonprofitDetail !== null);
        if (!nonprofitDetail) {
          setError("No nonprofit detail was returned for that EIN.");
        }
      } catch (caughtError) {
        setError(normalizeErrorMessage(caughtError));
      } finally {
        setIsLoading(false);
      }
    },
    [service],
  );

  const loadMoreResults = useCallback(async () => {
    if (!lastQuery || !nextCursor || searchMode !== "name") {
      return;
    }

    setIsLoadingMore(true);
    setError(null);

    try {
      const searchResults: PortalNonprofitSearchPage = await service.searchByName(
        lastQuery,
        {
          cursor: nextCursor,
        },
      );
      setResults((current) => [...current, ...searchResults.items]);
      setNextCursor(searchResults.nextCursor);
      setHasMoreResults(Boolean(searchResults.nextCursor));
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
    } finally {
      setIsLoadingMore(false);
    }
  }, [lastQuery, nextCursor, searchMode, service]);

  const closeDetail = useCallback(() => {
    setIsDetailOpen(false);
    setError(null);
  }, []);

  return {
    closeDetail,
    detail,
    error,
    hasSearched,
    hasMoreResults,
    isDetailOpen,
    isLoading,
    isLoadingMore,
    lastQuery,
    recentSearches,
    loadMoreResults,
    results,
    runSearch,
    searchMode,
    viewResultDetail,
  };
}

function normalizeErrorMessage(error: unknown): string {
  return normalizePortalError(error, "The nonprofit lookup failed. Try again.");
}

function prependSearchHistory(
  current: PortalNonprofitSearchHistoryEntry[],
  input: Omit<PortalNonprofitSearchHistoryEntry, "id" | "searchedAt">,
): PortalNonprofitSearchHistoryEntry[] {
  return [
    {
      ...input,
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      searchedAt: new Date().toISOString(),
    },
    ...current,
  ].slice(0, 10);
}
