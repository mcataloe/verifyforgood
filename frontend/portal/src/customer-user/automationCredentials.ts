import type { PortalOrganization } from "../organization/portalOrganization";

export interface CustomerUserApiKeyRecord {
  createdAt: string;
  createdBy: string;
  expiresAt: string;
  id: string;
  keyValue: string;
  name: string;
}

export interface CustomerUserOAuthClientRecord {
  clientId: string;
  clientSecret: string;
  createdAt: string;
  createdBy: string;
  expiresAt: string;
  id: string;
  name: string;
}

export interface CreateCustomerUserCredentialInput {
  createdBy: string;
  expiresAt: string;
  name: string;
}

export interface CustomerUserApiKeyService {
  createKey(
    input: CreateCustomerUserCredentialInput,
  ): Promise<CustomerUserApiKeyRecord>;
  deleteKey(id: string): Promise<void>;
  listKeys(): Promise<CustomerUserApiKeyRecord[]>;
}

export interface CustomerUserOAuthService {
  createClient(
    input: CreateCustomerUserCredentialInput,
  ): Promise<CustomerUserOAuthClientRecord>;
  deleteClient(id: string): Promise<void>;
  listClients(): Promise<CustomerUserOAuthClientRecord[]>;
}

export function createCustomerUserApiKeyService({
  organization,
  storage = window.localStorage,
}: {
  organization: PortalOrganization;
  storage?: Storage;
}): CustomerUserApiKeyService {
  return {
    async createKey(input) {
      const record: CustomerUserApiKeyRecord = {
        createdAt: new Date().toISOString(),
        createdBy: normalizeName(input.createdBy),
        expiresAt: input.expiresAt,
        id: `api_${createRandomToken(12)}`,
        keyValue: `vfg_${createRandomToken(8)}_${createRandomToken(20)}`,
        name: normalizeName(input.name, "Portal API key"),
      };

      const records = readRecords<CustomerUserApiKeyRecord>(
        storage,
        buildStorageKey("api_keys", organization),
      );
      writeRecords(storage, buildStorageKey("api_keys", organization), [
        record,
        ...records,
      ]);

      return record;
    },
    async deleteKey(id) {
      const records = readRecords<CustomerUserApiKeyRecord>(
        storage,
        buildStorageKey("api_keys", organization),
      );
      writeRecords(
        storage,
        buildStorageKey("api_keys", organization),
        records.filter((record) => record.id !== id),
      );
    },
    async listKeys() {
      return readRecords<CustomerUserApiKeyRecord>(
        storage,
        buildStorageKey("api_keys", organization),
      );
    },
  };
}

export function createCustomerUserOAuthService({
  organization,
  storage = window.localStorage,
}: {
  organization: PortalOrganization;
  storage?: Storage;
}): CustomerUserOAuthService {
  return {
    async createClient(input) {
      const record: CustomerUserOAuthClientRecord = {
        clientId: `client_${createRandomToken(16)}`,
        clientSecret: `secret_${createRandomToken(28)}`,
        createdAt: new Date().toISOString(),
        createdBy: normalizeName(input.createdBy),
        expiresAt: input.expiresAt,
        id: `oauth_${createRandomToken(12)}`,
        name: normalizeName(input.name, "Portal OAuth client"),
      };

      const records = readRecords<CustomerUserOAuthClientRecord>(
        storage,
        buildStorageKey("oauth_clients", organization),
      );
      writeRecords(storage, buildStorageKey("oauth_clients", organization), [
        record,
        ...records,
      ]);

      return record;
    },
    async deleteClient(id) {
      const records = readRecords<CustomerUserOAuthClientRecord>(
        storage,
        buildStorageKey("oauth_clients", organization),
      );
      writeRecords(
        storage,
        buildStorageKey("oauth_clients", organization),
        records.filter((record) => record.id !== id),
      );
    },
    async listClients() {
      return readRecords<CustomerUserOAuthClientRecord>(
        storage,
        buildStorageKey("oauth_clients", organization),
      );
    },
  };
}

function buildStorageKey(
  suffix: string,
  organization: Pick<PortalOrganization, "account_id" | "workspace_id">,
) {
  return `verifyforgood.portal.customerUser.${suffix}.${organization.account_id}.${organization.workspace_id}`;
}

function createRandomToken(length: number) {
  const token =
    globalThis.crypto?.randomUUID?.().replaceAll("-", "") ??
    Math.random().toString(16).slice(2).repeat(4);

  return token.slice(0, length);
}

function normalizeName(value: string, fallback = "Credential") {
  return String(value || "").trim() || fallback;
}

function readRecords<T>(storage: Storage, key: string): T[] {
  const raw = storage.getItem(key);

  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as T[]) : [];
  } catch {
    return [];
  }
}

function writeRecords<T>(storage: Storage, key: string, records: T[]) {
  storage.setItem(key, JSON.stringify(records));
}
