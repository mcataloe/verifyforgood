import {
  ActionIcon,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import {
  DataTable,
  Panel,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import {
  IconCopy,
  IconEdit,
  IconEye,
  IconEyeOff,
  IconTrash,
} from "@tabler/icons-react";
import { useEffect, useState, type ReactNode } from "react";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import { StackedDetailSections } from "../components/shell";
import { InfoTooltip } from "../components/InfoTooltip";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { usePortalApiKeys, type PortalApiKeysState } from "./usePortalApiKeys";

interface ApiKeyManagerProps {
  controller?: PortalApiKeysState;
}

export function ApiKeyManager({ controller }: ApiKeyManagerProps) {
  const organization = usePortalOrganization();
  const canManageKeys =
    organization.currentMembership?.role === "admin" &&
    organization.currentMembership?.status === "active";
  const defaultController = usePortalApiKeys({
    enabled: canManageKeys,
  });
  const apiKeys = controller ?? defaultController;
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [pendingRevokeKey, setPendingRevokeKey] = useState<
    (typeof apiKeys.items)[number] | null
  >(null);
  const [editingKey, setEditingKey] = useState<
    (typeof apiKeys.items)[number] | null
  >(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [isSecretVisible, setIsSecretVisible] = useState(false);

  const sortedKeys = [...apiKeys.items].sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  );
  const keyColumns: DataTableColumn<(typeof sortedKeys)[number]>[] = [
    {
      key: "display_name",
      header: "Display Name",
      sortable: true,
      render: (row) => (
        <Stack gap={2}>
          <Text fw={600}>{row.display_name}</Text>
          {row.description ? (
            <Text c="dimmed" size="sm">
              {row.description}
            </Text>
          ) : null}
        </Stack>
      ),
      sortValue: (row) => row.display_name,
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (row) => formatLabelValue(row.status),
      sortValue: (row) => row.status,
    },
    {
      key: "created_at",
      header: "Created",
      sortable: true,
      render: (row) => formatDateTime(row.created_at),
      sortValue: (row) => row.created_at,
    },
    {
      key: "last_used_at",
      header: "Last Used",
      sortable: true,
      render: (row) =>
        row.last_used_at ? formatDateTime(row.last_used_at) : "Never Used",
      sortValue: (row) => row.last_used_at ?? "",
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => {
        if (row.status === "revoked" || !canManageKeys) {
          return (
            <Text c="dimmed" fw={600} size="sm">
              {row.status === "revoked" ? "Revoked" : "Read Only"}
            </Text>
          );
        }

        const isBusy =
          apiKeys.isRevokingKeyId === row.key_id ||
          apiKeys.isUpdatingKeyId === row.key_id;

        return (
          <Group gap="xs" wrap="nowrap">
            <IconActionButton
              ariaLabel={`Edit key ${row.display_name}`}
              disabled={isBusy}
              icon={<IconEdit aria-hidden="true" size={16} />}
              onClick={() => {
                setEditingKey(row);
              }}
              tooltip="Edit key"
            />
            <IconActionButton
              ariaLabel={`Revoke key ${row.display_name}`}
              disabled={isBusy}
              icon={<IconTrash aria-hidden="true" size={16} />}
              onClick={() => {
                setPendingRevokeKey(row);
              }}
              tone="danger"
              tooltip="Revoke key"
            />
          </Group>
        );
      },
    },
  ];

  return (
    <>
      <StackedDetailSections>
        <Panel
          title="API Key Management"
          subtitle="Create, review, and update API keys for your organization."
        >
          <Stack gap="md">
            <PortalHint>
              API keys shown here belong to{" "}
              <strong>{organization.activeOrganization.organization_name}</strong>.
            </PortalHint>

            {!canManageKeys ? (
              <PortalNotice title="Admin Access Required" tone="warning">
                <p>
                  Only organization admins may create, edit, or revoke API keys for
                  this organization.
                </p>
              </PortalNotice>
            ) : (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  setCopyFeedback(null);
                  setIsSecretVisible(false);
                  void apiKeys.createKey({
                    description,
                    display_name: displayName,
                  });
                  setDisplayName("");
                  setDescription("");
                }}
              >
                <Stack maw={540}>
                  <TextInput
                    label="Display name"
                    onChange={(event) => {
                      setDisplayName(event.currentTarget.value);
                    }}
                    placeholder="Server Integration"
                    value={displayName}
                  />
                  <Textarea
                    autosize
                    label="Description"
                    minRows={3}
                    onChange={(event) => {
                      setDescription(event.currentTarget.value);
                    }}
                    placeholder="What this key is used for."
                    value={description}
                  />

                  <PortalActionGroup>
                    <PortalButton
                      loading={apiKeys.isCreating}
                      tone="primary"
                      type="submit"
                    >
                      {apiKeys.isCreating ? "Creating..." : "Create Key"}
                    </PortalButton>
                    <PortalButton
                      disabled={apiKeys.isLoading}
                      onClick={() => {
                        setCopyFeedback(null);
                        void apiKeys.refresh();
                      }}
                      tone="secondary"
                      type="button"
                    >
                      Refresh
                    </PortalButton>
                  </PortalActionGroup>
                </Stack>
              </form>
            )}

            {apiKeys.error ? (
              <PortalNotice tone="error">
                <p>{apiKeys.error}</p>
              </PortalNotice>
            ) : null}
          </Stack>
        </Panel>

        {apiKeys.visibleSecret ? (
          <Panel
            title="Copy Secret"
            subtitle="The plaintext API key is shown once and cannot be recovered later."
          >
            <Stack gap="md">
              {copyFeedback ? (
                <PortalNotice tone="warning">
                  <p>{copyFeedback}</p>
                </PortalNotice>
              ) : null}
              <div>
                <Text fw={600} size="sm">
                  Plaintext API Key
                </Text>
                <Group align="end" mt="xs" wrap="nowrap">
                  <TextInput
                    aria-label="Plaintext API key"
                    readOnly
                    style={{ flex: 1 }}
                    type={isSecretVisible ? "text" : "password"}
                    value={apiKeys.visibleSecret.secret}
                  />
                  <Tooltip
                    label={isSecretVisible ? "Hide key" : "Show key"}
                    withArrow
                    withinPortal
                  >
                    <ActionIcon
                      aria-label={isSecretVisible ? "Hide API key" : "Reveal API key"}
                      onClick={() => {
                        setIsSecretVisible((current) => !current);
                      }}
                      radius="xl"
                      size="lg"
                      type="button"
                      variant="light"
                    >
                      {isSecretVisible ? (
                        <IconEyeOff aria-hidden="true" size={16} />
                      ) : (
                        <IconEye aria-hidden="true" size={16} />
                      )}
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label="Copy key" withArrow withinPortal>
                    <ActionIcon
                      aria-label="Copy key"
                      onClick={() => {
                        void copySecretToClipboard({
                          onResult: setCopyFeedback,
                          secret: apiKeys.visibleSecret?.secret ?? "",
                        });
                      }}
                      radius="xl"
                      size="lg"
                      type="button"
                      variant="light"
                    >
                      <IconCopy aria-hidden="true" size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
                <Group gap={4} mt={6}>
                  <Text size="sm">Plaintext API Key</Text>
                  <InfoTooltip label="Store this key in your secrets manager before leaving the page. It will not be shown again." />
                </Group>
              </div>
              <PortalActionGroup>
                <Text size="sm">
                  Key name: <strong>{apiKeys.visibleSecret.key.display_name}</strong>
                </Text>
                <PortalButton
                  onClick={() => {
                    setCopyFeedback(null);
                    setIsSecretVisible(false);
                    apiKeys.dismissSecret();
                  }}
                  type="button"
                >
                  Dismiss
                </PortalButton>
              </PortalActionGroup>
            </Stack>
          </Panel>
        ) : null}

        <Panel title="Organization API Keys" subtitle="Manage active and revoked keys.">
          <Stack gap="md">
            {apiKeys.isLoading ? (
              <PortalNotice title="Loading" tone="loading">
                <p>Loading API keys for the current organization.</p>
              </PortalNotice>
            ) : null}
            {!apiKeys.isLoading && sortedKeys.length === 0 ? (
              <PortalNotice title="Nothing to Show Yet" tone="empty">
                <p>Create a key to start authenticating API traffic.</p>
              </PortalNotice>
            ) : null}

            {sortedKeys.length > 0 ? (
              <DataTable
                ariaLabel="Organization API keys"
                columns={keyColumns}
                getSearchText={(row) =>
                  `${row.display_name} ${row.description} ${row.status} ${row.created_at} ${row.last_used_at ?? ""}`
                }
                initialSort={{ columnKey: "created_at", direction: "desc" }}
                pageSize={8}
                rowKey={(row) => row.key_id}
                rows={sortedKeys}
                searchPlaceholder="Search API keys"
              />
            ) : null}
          </Stack>
        </Panel>
      </StackedDetailSections>
      <ApiKeyEditModal
        keyRecord={editingKey}
        onClose={() => {
          setEditingKey(null);
        }}
        onSubmit={(keyId, input) => apiKeys.updateKey(keyId, input)}
        submittingKeyId={apiKeys.isUpdatingKeyId}
      />
      <ApiKeyRevokeModal
        keyRecord={pendingRevokeKey}
        onClose={() => {
          setPendingRevokeKey(null);
        }}
        onConfirm={(keyId) => {
          void apiKeys.revokeKey(keyId);
          setPendingRevokeKey(null);
        }}
        revokingKeyId={apiKeys.isRevokingKeyId}
      />
    </>
  );
}

function ApiKeyEditModal({
  keyRecord,
  onClose,
  onSubmit,
  submittingKeyId,
}: {
  keyRecord: PortalApiKeysState["items"][number] | null;
  onClose: () => void;
  onSubmit: (
    keyId: string,
    input: { display_name: string; description?: string },
  ) => Promise<void>;
  submittingKeyId: string | null;
}) {
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    setDisplayName(keyRecord?.display_name ?? "");
    setDescription(keyRecord?.description ?? "");
  }, [keyRecord]);

  const isSubmitting = Boolean(
    keyRecord && submittingKeyId === keyRecord.key_id,
  );

  return (
    <Modal
      centered
      onClose={onClose}
      opened={Boolean(keyRecord)}
      title="Edit API Key"
    >
      <Stack>
        <TextInput
          label="Display name"
          onChange={(event) => {
            setDisplayName(event.currentTarget.value);
          }}
          value={displayName}
        />
        <Textarea
          autosize
          label="Description"
          minRows={3}
          onChange={(event) => {
            setDescription(event.currentTarget.value);
          }}
          value={description}
        />
        <Group justify="flex-end">
          <PortalButton onClick={onClose} tone="secondary" type="button">
            Cancel
          </PortalButton>
          <PortalButton
            disabled={isSubmitting || !keyRecord}
            onClick={() => {
              if (!keyRecord) {
                return;
              }
              void onSubmit(keyRecord.key_id, {
                description,
                display_name: displayName,
              })
                .then(() => {
                  onClose();
                })
                .catch(() => {});
            }}
            tone="primary"
            type="button"
          >
            {isSubmitting ? "Saving..." : "Save"}
          </PortalButton>
        </Group>
      </Stack>
    </Modal>
  );
}

function ApiKeyRevokeModal({
  keyRecord,
  onClose,
  onConfirm,
  revokingKeyId,
}: {
  keyRecord: PortalApiKeysState["items"][number] | null;
  onClose: () => void;
  onConfirm: (keyId: string) => void;
  revokingKeyId: string | null;
}) {
  const isRevoking = Boolean(keyRecord && revokingKeyId === keyRecord.key_id);

  return (
    <Modal
      centered
      onClose={onClose}
      opened={Boolean(keyRecord)}
      title="Revoke API Key"
    >
      <Stack>
        <Text>
          {keyRecord
            ? `This will revoke ${keyRecord.display_name}. Existing integrations using it will stop working.`
            : ""}
        </Text>
        <Group justify="flex-end">
          <PortalButton onClick={onClose} tone="secondary" type="button">
            Cancel
          </PortalButton>
          <PortalButton
            disabled={!keyRecord || isRevoking}
            onClick={() => {
              if (keyRecord) {
                onConfirm(keyRecord.key_id);
              }
            }}
            tone="danger"
            type="button"
          >
            {isRevoking ? "Revoking..." : "Revoke"}
          </PortalButton>
        </Group>
      </Stack>
    </Modal>
  );
}

function IconActionButton({
  ariaLabel,
  disabled = false,
  icon,
  onClick,
  tone = "neutral",
  tooltip,
}: {
  ariaLabel: string;
  disabled?: boolean;
  icon: ReactNode;
  onClick: () => void;
  tone?: "danger" | "neutral";
  tooltip: string;
}) {
  return (
    <Tooltip label={tooltip} withArrow withinPortal>
      <ActionIcon
        aria-label={ariaLabel}
        color={tone === "danger" ? "red" : "gray"}
        disabled={disabled}
        onClick={onClick}
        radius="xl"
        size="lg"
        type="button"
        variant="subtle"
      >
        {icon}
      </ActionIcon>
    </Tooltip>
  );
}

async function copySecretToClipboard({
  onResult,
  secret,
}: {
  onResult: (value: string | null) => void;
  secret: string;
}) {
  try {
    if (!navigator.clipboard?.writeText) {
      throw new Error("clipboard_unavailable");
    }
    await navigator.clipboard.writeText(secret);
    onResult("API key copied to clipboard.");
  } catch {
    onResult("Copy failed. Copy the API key manually before dismissing it.");
  }
}

function formatDateTime(value: string): string {
  const parsedValue = Date.parse(value);
  if (Number.isNaN(parsedValue)) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(parsedValue));
}

function formatLabelValue(value: string | null | undefined): string {
  const candidate = String(value ?? "").trim();
  if (!candidate) {
    return "Unknown";
  }

  return candidate
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
}
