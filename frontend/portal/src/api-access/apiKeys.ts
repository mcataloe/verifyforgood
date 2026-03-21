import type { ApiClient } from "@charity-status/shared-api";
import type { PortalOrganization } from "../organization/portalOrganization";

type PortalApiKeyStatus = "active" | "revoked";

interface StoredPortalApiKeyRecord {
  account_id: string;
  created_at: string;
  key_id: string;
  key_prefix: string;
  label: string;
  last_used_at: string | null;
  scopes: string[];
  status: PortalApiKeyStatus;
  workspace_id: string;
}

export type PortalApiKeySummary = StoredPortalApiKeyRecord;

export interface CreatePortalApiKeyInput {
  label: string;
  scopes: string[];
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

export type PortalApiKeyServiceImplementation =
  | "backend"
  | "mock_local_control_plane_gap";

export interface PortalApiKeyService {
  createKey(input: CreatePortalApiKeyInput): Promise<CreatePortalApiKeyResult>;
  implementation: PortalApiKeyServiceImplementation;
  listKeys(): Promise<ListPortalApiKeysResult>;
  revokeKey(keyId: string): Promise<PortalApiKeySummary>;
}

interface CreatePortalApiKeyServiceOptions {
  apiClient: ApiClient;
  organization: PortalOrganization;
  storage?: Storage;
}

const DEFAULT_SCOPES = ["verify:read"] as const;

export function createPortalApiKeyService({
  apiClient,
  organization,
  storage,
}: CreatePortalApiKeyServiceOptions): PortalApiKeyService {
  void apiClient;

  return createMockPortalApiKeyService({
    organization,
    storage,
  });
}

export function createMockPortalApiKeyService({
  organization,
  storage = window.localStorage,
}: {
  organization: PortalOrganization;
  storage?: Storage;
}): PortalApiKeyService {
  const implementation: PortalApiKeyServiceImplementation =
    "mock_local_control_plane_gap";

  return {
    implementation,
    async createKey(input) {
      const keyId = `key_${createRandomToken(32)}`;
      const secret = `csk_${createRandomToken(16)}.${createRandomToken(24)}`;
      const record: StoredPortalApiKeyRecord = {
        account_id: organization.account_id,
        created_at: new Date().toISOString(),
        key_id: keyId,
        key_prefix: secret.slice(0, 14),
        label: normalizeLabel(input.label),
        last_used_at: null,
        scopes: normalizeScopes(input.scopes),
        status: "active",
        workspace_id: organization.workspace_id,
      };

      const existingRecords = readStoredKeys(storage, organization);
      writeStoredKeys(storage, organization, [record, ...existingRecords]);

      return {
        api_key: record,
        implementation,
        secret,
      };
    },
    async listKeys() {
      return {
        implementation,
        items: readStoredKeys(storage, organization),
      };
    },
    async revokeKey(keyId) {
      const existingRecords = readStoredKeys(storage, organization);
      const nextRecords = existingRecords.map((record) =>
        record.key_id === keyId
          ? { ...record, status: "revoked" as const }
          : record,
      );
      const revokedRecord = nextRecords.find(
        (record) => record.key_id === keyId,
      );
      if (!revokedRecord) {
        throw new Error(`API key not found: ${keyId}`);
      }

      writeStoredKeys(storage, organization, nextRecords);
      return revokedRecord;
    },
  };
}

export function defaultPortalApiKeyScopes(): string[] {
  return [...DEFAULT_SCOPES];
}

function readStoredKeys(
  storage: Storage,
  organization: Pick<PortalOrganization, "account_id" | "workspace_id">,
): StoredPortalApiKeyRecord[] {
  const rawValue = storage.getItem(storageKey(organization));
  if (!rawValue) {
    return [];
  }

  try {
    const parsedValue = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsedValue)) {
      return [];
    }

    return parsedValue
      .filter(isStoredPortalApiKeyRecord)
      .sort((left, right) => right.created_at.localeCompare(left.created_at));
  } catch {
    return [];
  }
}

function writeStoredKeys(
  storage: Storage,
  organization: Pick<PortalOrganization, "account_id" | "workspace_id">,
  records: StoredPortalApiKeyRecord[],
): void {
  storage.setItem(storageKey(organization), JSON.stringify(records));
}

function storageKey(
  organization: Pick<PortalOrganization, "account_id" | "workspace_id">,
): string {
  return `verifyforgood.portal.apiKeys.${organization.account_id}.${organization.workspace_id}`;
}

function normalizeLabel(value: string): string {
  return String(value || "").trim() || "Portal API key";
}

function normalizeScopes(scopes: string[]): string[] {
  const normalizedScopes = scopes
    .map((scope) => String(scope || "").trim())
    .filter(Boolean);

  return normalizedScopes.length > 0
    ? normalizedScopes
    : defaultPortalApiKeyScopes();
}

function createRandomToken(length: number): string {
  const token =
    globalThis.crypto?.randomUUID?.().replaceAll("-", "") ??
    Math.random().toString(16).slice(2).repeat(4);
  return token.slice(0, length);
}

function isStoredPortalApiKeyRecord(
  value: unknown,
): value is StoredPortalApiKeyRecord {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<StoredPortalApiKeyRecord>;
  return (
    typeof candidate.account_id === "string" &&
    typeof candidate.created_at === "string" &&
    typeof candidate.key_id === "string" &&
    typeof candidate.key_prefix === "string" &&
    typeof candidate.label === "string" &&
    Array.isArray(candidate.scopes) &&
    typeof candidate.status === "string" &&
    typeof candidate.workspace_id === "string"
  );
}
