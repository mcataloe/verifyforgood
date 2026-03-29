import {
  apiEndpoints,
  resolvePathTemplate,
  type ApiClient,
} from "@charity-status/shared-api";

export type PortalApiKeyStatus = "active" | "revoked";

export interface PortalApiKeySummary {
  created_at: string;
  created_by_user_id: string;
  display_name: string;
  key_id: string;
  last_used_at: string | null;
  organization_id: string;
  status: PortalApiKeyStatus;
}

export interface CreatePortalApiKeyInput {
  display_name: string;
}

export interface CreatePortalApiKeyResult {
  api_key: PortalApiKeySummary;
  implementation: PortalApiKeyServiceImplementation;
  secret: string;
}

export interface ListPortalApiKeysResult {
  implementation: PortalApiKeyServiceImplementation;
  items: PortalApiKeySummary[];
}

export type PortalApiKeyServiceImplementation = "backend";

export interface PortalApiKeyService {
  createKey(input: CreatePortalApiKeyInput): Promise<CreatePortalApiKeyResult>;
  implementation: PortalApiKeyServiceImplementation;
  listKeys(): Promise<ListPortalApiKeysResult>;
  revokeKey(keyId: string): Promise<PortalApiKeySummary>;
}

interface CreatePortalApiKeyServiceOptions {
  apiClient: ApiClient;
}

export function createPortalApiKeyService({
  apiClient,
}: CreatePortalApiKeyServiceOptions): PortalApiKeyService {
  const implementation: PortalApiKeyServiceImplementation = "backend";

  return {
    implementation,
    async createKey(input) {
      const payload = await apiClient.post<
        CreatePortalApiKeyResult,
        CreatePortalApiKeyInput
      >(apiEndpoints.organization.createCurrentApiKey, {
        body: {
          display_name: normalizeDisplayName(input.display_name),
        },
      });

      return {
        ...payload,
        implementation,
      };
    },
    async listKeys() {
      const payload = await apiClient.get<{ items: PortalApiKeySummary[] }>(
        apiEndpoints.organization.currentApiKeys,
      );

      return {
        implementation,
        items: payload.items,
      };
    },
    revokeKey(keyId) {
      return apiClient.delete<PortalApiKeySummary>(
        resolvePathTemplate(apiEndpoints.organization.deleteCurrentApiKey.path, {
          keyId,
        }),
      );
    },
  };
}

function normalizeDisplayName(value: string): string {
  return String(value || "").trim();
}
