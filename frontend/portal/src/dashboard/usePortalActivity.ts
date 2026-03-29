import { useEffect, useMemo, useState } from "react";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalActivityService,
  type PortalActivityService,
  type PortalOrganizationActivityItem,
} from "./portalActivity";
import { normalizePortalError } from "../lib/portalError";

export interface PortalActivityController {
  error: string | null;
  hasMore: boolean;
  isLoading: boolean;
  isLoadingMore: boolean;
  items: PortalOrganizationActivityItem[];
  loadMore: () => Promise<void>;
  reload: () => Promise<void>;
}

export function usePortalActivity(
  options?: {
    enabled?: boolean;
  },
  serviceFactory?: (
    organization: ReturnType<typeof usePortalOrganization>,
  ) => PortalActivityService,
): PortalActivityController {
  const organization = usePortalOrganization();
  const enabled = options?.enabled ?? true;
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [items, setItems] = useState<PortalOrganizationActivityItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const service = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalActivityService(organization.apiClient),
    [organization, serviceFactory],
  );

  useEffect(() => {
    let isCancelled = false;

    if (!enabled) {
      setError(null);
      setHasMore(false);
      setIsLoading(false);
      setIsLoadingMore(false);
      setItems([]);
      setNextCursor(null);
      return () => {
        isCancelled = true;
      };
    }

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const page = await service.listActivity({ limit: 20 });
        if (!isCancelled) {
          setItems(page.items);
          setNextCursor(page.next_cursor);
          setHasMore(page.has_more);
        }
      } catch (caughtError) {
        if (!isCancelled) {
          setError(
            normalizePortalError(
              caughtError,
              "The recent activity feed could not be loaded.",
            ),
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      isCancelled = true;
    };
  }, [enabled, service]);

  const reload = async () => {
    if (!enabled) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const page = await service.listActivity({ limit: 20 });
      setItems(page.items);
      setNextCursor(page.next_cursor);
      setHasMore(page.has_more);
    } catch (caughtError) {
      setError(
        normalizePortalError(
          caughtError,
          "The recent activity feed could not be loaded.",
        ),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const loadMore = async () => {
    if (!enabled || !nextCursor) {
      return;
    }
    setIsLoadingMore(true);
    setError(null);
    try {
      const page = await service.listActivity({
        cursor: nextCursor,
        limit: 20,
      });
      setItems((current) => [...current, ...page.items]);
      setNextCursor(page.next_cursor);
      setHasMore(page.has_more);
    } catch (caughtError) {
      setError(
        normalizePortalError(
          caughtError,
          "The next activity page could not be loaded.",
        ),
      );
    } finally {
      setIsLoadingMore(false);
    }
  };

  return {
    error,
    hasMore,
    isLoading,
    isLoadingMore,
    items,
    loadMore,
    reload,
  };
}
