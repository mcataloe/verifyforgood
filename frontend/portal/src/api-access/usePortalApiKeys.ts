import { useCallback, useEffect, useMemo, useState } from "react";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createPortalApiKeyService,
  defaultPortalApiKeyScopes,
  type CreatePortalApiKeyInput,
  type PortalApiKeyService,
  type PortalApiKeySummary,
} from "./apiKeys";

export interface PortalApiKeysState {
  createKey: (input: CreatePortalApiKeyInput) => Promise<void>;
  dismissSecret: () => void;
  error: string | null;
  implementation: string | null;
  isCreating: boolean;
  isLoading: boolean;
  isRevokingKeyId: string | null;
  items: PortalApiKeySummary[];
  refresh: () => Promise<void>;
  revokeKey: (keyId: string) => Promise<void>;
  scopesPlaceholder: string;
  visibleSecret: {
    key: PortalApiKeySummary;
    secret: string;
  } | null;
}

export function usePortalApiKeys(
  serviceFactory?: (
    service: ReturnType<typeof usePortalOrganization>,
  ) => PortalApiKeyService,
): PortalApiKeysState {
  const organization = usePortalOrganization();
  const [items, setItems] = useState<PortalApiKeySummary[]>([]);
  const [implementation, setImplementation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isRevokingKeyId, setIsRevokingKeyId] = useState<string | null>(null);
  const [visibleSecret, setVisibleSecret] =
    useState<PortalApiKeysState["visibleSecret"]>(null);

  const apiKeyService = useMemo(
    () =>
      serviceFactory?.(organization) ??
      createPortalApiKeyService({
        apiClient: organization.apiClient,
        organization: organization.activeOrganization,
      }),
    [organization, serviceFactory],
  );

  const refresh = useCallback(async () => {
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
  }, [apiKeyService]);

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
    items,
    refresh,
    revokeKey,
    scopesPlaceholder: defaultPortalApiKeyScopes().join(", "),
    visibleSecret,
  };
}

function normalizeErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "The API credential action failed. Try again.";
}
