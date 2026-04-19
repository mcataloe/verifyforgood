import {
  IconCopy,
  IconEdit,
  IconEye,
  IconEyeOff,
  IconTrash,
} from "@tabler/icons-react";
import { useEffect, useState, type ReactNode } from "react";
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
  Inline,
  Panel,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import { PortalNotice } from "../components/feedback";
import { InfoTooltip } from "../components/InfoTooltip";
import { StackedDetailSections } from "../components/shell";
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
        <div className="portal-key-row">
          <div className="portal-key-row__name">{row.display_name}</div>
          {row.description ? (
            <div className="portal-key-row__description">{row.description}</div>
          ) : null}
        </div>
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
            <span className="portal-key-card__action-note">
              {row.status === "revoked" ? "Revoked" : "Read Only"}
            </span>
          );
        }

        const isBusy =
          apiKeys.isRevokingKeyId === row.key_id ||
          apiKeys.isUpdatingKeyId === row.key_id;

        return (
          <Group gap="xs" wrap="nowrap">
            <IconActionButton
              ariaLabel={`Edit key ${row.display_name}`}
              icon={<IconEdit aria-hidden="true" size={16} />}
              onClick={() => {
                setEditingKey(row);
              }}
              tooltip="Edit key"
              disabled={isBusy}
            />
            <IconActionButton
              ariaLabel={`Revoke key ${row.display_name}`}
              icon={<IconTrash aria-hidden="true" size={16} />}
              onClick={() => {
                setPendingRevokeKey(row);
              }}
              tooltip="Revoke key"
              disabled={isBusy}
              tone="danger"
            />
          </Group>
        );
      },
    },
  ];

  return (
    <StackedDetailSections>
      <Panel
        title="API Key Management"
        subtitle="Create, review, and update API keys for your organization."
      >
        {!canManageKeys ? (
          <PortalNotice title="Admin Access Required" tone="warning">
            <p>
              Only organization admins may create, edit, or revoke API keys for
              this organization.
            </p>
          </PortalNotice>
        ) : (
          <form
            className="portal-form portal-form--detail"
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

            <Inline className="portal-form__actions">
              <button
                className="portal-shell__action portal-shell__action--primary"
                disabled={apiKeys.isCreating}
                type="submit"
              >
                {apiKeys.isCreating ? "Creating..." : "Create Key"}
              </button>
              <button
                className="portal-shell__action portal-shell__action--secondary"
                disabled={apiKeys.isLoading}
                onClick={() => {
                  setCopyFeedback(null);
                  void apiKeys.refresh();
                }}
                type="button"
              >
                Refresh
              </button>
            </Inline>
          </form>
        )}

        {apiKeys.error ? (
          <PortalNotice tone="error">
            <p>{apiKeys.error}</p>
          </PortalNotice>
        ) : null}
      </Panel>

      {apiKeys.visibleSecret ? (
        <Panel
          title="Copy Secret"
          subtitle="The plaintext API key is shown once and cannot be recovered later."
        >
          {copyFeedback ? (
            <PortalNotice tone="warning">
              <p>{copyFeedback}</p>
            </PortalNotice>
          ) : null}
          <label className="portal-form__field" htmlFor="plaintext-api-key">
            <span className="portal-form__label-with-tooltip">
              <span>Plaintext API Key</span>
              <InfoTooltip label="Store this key in your secrets manager before leaving the page. It will not be shown again." />
            </span>
            <div className="portal-secret-field">
              <input
                aria-label="Plaintext API key"
                className="portal-form__input portal-secret-field__input"
                id="plaintext-api-key"
                readOnly
                type={isSecretVisible ? "text" : "password"}
                value={apiKeys.visibleSecret.secret}
              />
              <Inline className="portal-secret-field__actions">
                <Tooltip
                  label={isSecretVisible ? "Hide key" : "Show key"}
                  withArrow
                  withinPortal
                >
                  <button
                    aria-label={isSecretVisible ? "Hide API key" : "Reveal API key"}
                    className="portal-secret-field__action"
                    onClick={() => {
                      setIsSecretVisible((current) => !current);
                    }}
                    type="button"
                  >
                    {isSecretVisible ? (
                      <IconEyeOff aria-hidden="true" size={16} />
                    ) : (
                      <IconEye aria-hidden="true" size={16} />
                    )}
                  </button>
                </Tooltip>
                <Tooltip label="Copy key" withArrow withinPortal>
                  <button
                    aria-label="Copy key"
                    className="portal-secret-field__action"
                    onClick={() => {
                      void copySecretToClipboard({
                        onResult: setCopyFeedback,
                        secret: apiKeys.visibleSecret?.secret ?? "",
                      });
                    }}
                    type="button"
                  >
                    <IconCopy aria-hidden="true" size={16} />
                  </button>
                </Tooltip>
              </Inline>
            </div>
          </label>
          <Inline className="portal-form__actions">
            <span>
              Key name: <strong>{apiKeys.visibleSecret.key.display_name}</strong>
            </span>
            <button
              className="portal-shell__action"
              onClick={() => {
                setCopyFeedback(null);
                setIsSecretVisible(false);
                apiKeys.dismissSecret();
              }}
              type="button"
            >
              Dismiss
            </button>
          </Inline>
        </Panel>
      ) : null}

      <Panel title="Organization API Keys" subtitle="Manage active and revoked keys.">
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
      </Panel>

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
    </StackedDetailSections>
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
          <button className="portal-shell__action" onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className="portal-shell__action portal-shell__action--primary"
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
            type="button"
          >
            {isSubmitting ? "Saving..." : "Save"}
          </button>
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
          <button className="portal-shell__action" onClick={onClose} type="button">
            Cancel
          </button>
          <button
            className="portal-shell__action portal-shell__action--danger"
            disabled={!keyRecord || isRevoking}
            onClick={() => {
              if (keyRecord) {
                onConfirm(keyRecord.key_id);
              }
            }}
            type="button"
          >
            {isRevoking ? "Revoking..." : "Revoke"}
          </button>
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
