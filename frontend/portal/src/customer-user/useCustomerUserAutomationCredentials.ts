import { useCallback, useEffect, useMemo, useState } from "react";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  createCustomerUserApiKeyService,
  createCustomerUserOAuthService,
  type CreateCustomerUserCredentialInput,
  type CustomerUserApiKeyRecord,
  type CustomerUserOAuthClientRecord,
} from "./automationCredentials";

export function useCustomerUserApiKeys(createdBy: string) {
  const organization = usePortalOrganization();
  const service = useMemo(
    () =>
      createCustomerUserApiKeyService({
        organization: organization.activeOrganization,
      }),
    [organization.activeOrganization],
  );
  const [items, setItems] = useState<CustomerUserApiKeyRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setItems(await service.listKeys());
    setIsLoading(false);
  }, [service]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createItem = async (input: Omit<CreateCustomerUserCredentialInput, "createdBy">) => {
    const created = await service.createKey({ ...input, createdBy });
    setItems((current) => [created, ...current]);
  };

  const deleteItem = async (id: string) => {
    await service.deleteKey(id);
    setItems((current) => current.filter((item) => item.id !== id));
  };

  return {
    createItem,
    deleteItem,
    isLoading,
    items,
    refresh,
  };
}

export function useCustomerUserOAuthClients(createdBy: string) {
  const organization = usePortalOrganization();
  const service = useMemo(
    () =>
      createCustomerUserOAuthService({
        organization: organization.activeOrganization,
      }),
    [organization.activeOrganization],
  );
  const [items, setItems] = useState<CustomerUserOAuthClientRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setItems(await service.listClients());
    setIsLoading(false);
  }, [service]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createItem = async (input: Omit<CreateCustomerUserCredentialInput, "createdBy">) => {
    const created = await service.createClient({ ...input, createdBy });
    setItems((current) => [created, ...current]);
  };

  const deleteItem = async (id: string) => {
    await service.deleteClient(id);
    setItems((current) => current.filter((item) => item.id !== id));
  };

  return {
    createItem,
    deleteItem,
    isLoading,
    items,
    refresh,
  };
}
