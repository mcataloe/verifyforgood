import {
  apiEndpoints,
  resolvePathTemplate,
  type ApiClient,
} from "@charity-status/shared-api";

export type PortalApiKeyStatus = "active" | "revoked";

export type PortalApiKeyPermissionLevel = "full_access" | "read_only";

export interface PortalApiKeySummary {
  created_at: string;
  created_by_user_id: string;
  display_name: string;
  description: string;
  key_id: string;
  last_used_at: string | null;
  organization_id: string;
  status: PortalApiKeyStatus;
  permission_level: PortalApiKeyPermissionLevel;
  expires_at: string | null;
  allowed_cidr: string | null;
}

export interface CreatePortalApiKeyInput {
  display_name: string;
  description?: string;
  permission_level?: PortalApiKeyPermissionLevel;
  expires_at?: string;
  allowed_cidr?: string;
}

export interface UpdatePortalApiKeyInput {
  description?: string;
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
  updateKey(
    keyId: string,
    input: UpdatePortalApiKeyInput,
  ): Promise<PortalApiKeySummary>;
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
          description: normalizeDescription(input.description),
          permission_level: input.permission_level,
          expires_at: normalizeOptionalValue(input.expires_at),
          allowed_cidr: normalizeOptionalValue(input.allowed_cidr),
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
    updateKey(keyId, input) {
      return apiClient.patch<PortalApiKeySummary, UpdatePortalApiKeyInput>(
        resolvePathTemplate(apiEndpoints.organization.updateCurrentApiKey.path, {
          keyId,
        }),
        {
          body: {
            display_name: normalizeDisplayName(input.display_name),
            description: normalizeDescription(input.description),
          },
        },
      );
    },
  };
}

function normalizeDisplayName(value: string): string {
  return String(value || "").trim();
}

function normalizeDescription(value: string | undefined): string {
  return String(value || "").trim();
}

function normalizeOptionalValue(value: string | undefined): string | undefined {
  const candidate = String(value || "").trim();
  return candidate || undefined;
}
