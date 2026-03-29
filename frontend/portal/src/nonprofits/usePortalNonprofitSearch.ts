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
  detail: PortalNonprofitDetail | null;
  error: string | null;
  hasSearched: boolean;
  hasMoreResults: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  lastQuery: string;
  loadMoreResults: () => Promise<void>;
  results: PortalNonprofitSearchSummary[];
  runSearch: (query: string) => Promise<void>;
  searchMode: "ein" | "name" | null;
  viewResultDetail: (ein: string) => Promise<void>;
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
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [lastQuery, setLastQuery] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
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

      setHasSearched(true);
      setIsLoading(true);
      setIsLoadingMore(false);
      setError(null);
      setLastQuery(trimmedQuery);
      setNextCursor(null);
      setHasMoreResults(false);

      try {
        if (looksLikeEinQuery(trimmedQuery)) {
          const nonprofitDetail = await service.lookupByEin(trimmedQuery);
          setDetail(nonprofitDetail);
          setResults([]);
          setSearchMode("ein");
          if (!nonprofitDetail) {
            setError(null);
          }
          return;
        }

        const searchResults = await service.searchByName(trimmedQuery);
        setDetail(null);
        setResults(searchResults.items);
        setNextCursor(searchResults.nextCursor);
        setHasMoreResults(Boolean(searchResults.nextCursor));
        setSearchMode("name");
      } catch (caughtError) {
        setDetail(null);
        setResults([]);
        setNextCursor(null);
        setHasMoreResults(false);
        setError(normalizeErrorMessage(caughtError));
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

  return {
    detail,
    error,
    hasSearched,
    hasMoreResults,
    isLoading,
    isLoadingMore,
    lastQuery,
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
