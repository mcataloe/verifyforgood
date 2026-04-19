import { useCallback, useEffect, useMemo, useState } from "react";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalApiKeyService,
  type CreatePortalApiKeyInput,
  type PortalApiKeyService,
  type PortalApiKeySummary,
  type UpdatePortalApiKeyInput,
} from "./apiKeys";
import { normalizePortalError } from "../lib/portalError";

export interface PortalApiKeysState {
  createKey: (input: CreatePortalApiKeyInput) => Promise<void>;
  dismissSecret: () => void;
  error: string | null;
  implementation: string | null;
  isCreating: boolean;
  isLoading: boolean;
  isRevokingKeyId: string | null;
  isUpdatingKeyId: string | null;
  items: PortalApiKeySummary[];
  refresh: () => Promise<void>;
  revokeKey: (keyId: string) => Promise<void>;
  updateKey: (keyId: string, input: UpdatePortalApiKeyInput) => Promise<void>;
  visibleSecret: {
    key: PortalApiKeySummary;
    secret: string;
  } | null;
}

export function usePortalApiKeys(
  options?: {
    enabled?: boolean;
  },
  serviceFactory?: (
    service: ReturnType<typeof usePortalOrganization>,
  ) => PortalApiKeyService,
): PortalApiKeysState {
  const organization = usePortalOrganization();
  const enabled = options?.enabled ?? true;
  const [items, setItems] = useState<PortalApiKeySummary[]>([]);
  const [implementation, setImplementation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(enabled);
  const [isCreating, setIsCreating] = useState(false);
  const [isRevokingKeyId, setIsRevokingKeyId] = useState<string | null>(null);
  const [isUpdatingKeyId, setIsUpdatingKeyId] = useState<string | null>(null);
  const [visibleSecret, setVisibleSecret] =
    useState<PortalApiKeysState["visibleSecret"]>(null);

  const apiKeyService = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalApiKeyService({
        apiClient: organization.apiClient,
      }),
    [organization, serviceFactory],
  );

  const refresh = useCallback(async () => {
    if (!enabled) {
      setIsLoading(false);
      setItems([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await apiKeyService.listKeys();
      setItems(result.items);
      setImplementation(result.implementation);
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
    } finally {
      setIsLoading(false);
    }
  }, [apiKeyService, enabled]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createKey = async (input: CreatePortalApiKeyInput) => {
    setIsCreating(true);
    setError(null);

    try {
      const result = await apiKeyService.createKey(input);
      setItems((currentItems) => [result.api_key, ...currentItems]);
      setImplementation(result.implementation);
      setVisibleSecret({
        key: result.api_key,
        secret: result.secret,
      });
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
    } finally {
      setIsCreating(false);
    }
  };

  const revokeKey = async (keyId: string) => {
    setIsRevokingKeyId(keyId);
    setError(null);

    try {
      const revokedKey = await apiKeyService.revokeKey(keyId);
      setItems((currentItems) =>
        currentItems.map((item) => (item.key_id === keyId ? revokedKey : item)),
      );
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
    } finally {
      setIsRevokingKeyId(null);
    }
  };

  const updateKey = async (keyId: string, input: UpdatePortalApiKeyInput) => {
    setIsUpdatingKeyId(keyId);
    setError(null);

    try {
      const updatedKey = await apiKeyService.updateKey(keyId, input);
      setItems((currentItems) =>
        currentItems.map((item) => (item.key_id === keyId ? updatedKey : item)),
      );
      setVisibleSecret((currentVisibleSecret) =>
        currentVisibleSecret?.key.key_id === keyId
          ? {
              ...currentVisibleSecret,
              key: updatedKey,
            }
          : currentVisibleSecret,
      );
    } catch (caughtError) {
      setError(normalizeErrorMessage(caughtError));
      throw caughtError;
    } finally {
      setIsUpdatingKeyId(null);
    }
  };

  return {
    createKey,
    dismissSecret: () => {
      setVisibleSecret(null);
    },
    error,
    implementation,
    isCreating,
    isLoading,
    isRevokingKeyId,
    isUpdatingKeyId,
    items,
    refresh,
    revokeKey,
    updateKey,
    visibleSecret,
  };
}

function normalizeErrorMessage(error: unknown): string {
  return normalizePortalError(
    error,
    "The API credential action failed. Try again.",
  );
}
