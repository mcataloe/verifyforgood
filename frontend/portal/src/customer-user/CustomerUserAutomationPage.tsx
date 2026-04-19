import {
  ActionIcon,
  Button,
  Group,
  Modal,
  Paper,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { DetailFieldList, EmptyState } from "@charity-status/shared-ui";
import { IconCopy, IconEye, IconEyeOff, IconTrash } from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  PortalActionGroup,
  PortalButton,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import {
  PortalDetailSection,
  PortalDetailView,
} from "../components/PortalDetailView";
import { HardStopEnforcementField } from "../settings/HardStopEnforcementField";
import { usePortalBudgetSettings } from "../settings/usePortalBudgetSettings";
import type {
  CustomerUserApiKeyRecord,
  CustomerUserOAuthClientRecord,
} from "./automationCredentials";
import {
  useCustomerUserApiKeys,
  useCustomerUserOAuthClients,
} from "./useCustomerUserAutomationCredentials";

interface CustomerUserAutomationPageProps {
  pane: "automation-api" | "automation-general" | "automation-oauth";
  session: PortalAuthenticatedSession;
}

export function CustomerUserAutomationPage({
  pane,
  session,
}: CustomerUserAutomationPageProps) {
  const title =
    pane === "automation-general"
      ? "General"
      : pane === "automation-api"
        ? "API Key"
        : "OAuth";
  const description =
    pane === "automation-general"
      ? "Automation-wide controls for how verification traffic behaves when usage thresholds are reached."
      : pane === "automation-api"
        ? "Create API keys for direct integrations and background workflows."
        : "Create OAuth client credentials for server-to-server integrations.";

  return (
    <PortalDetailView eyebrow="Automation" intro={description} title={title}>
      {pane === "automation-general" ? <AutomationGeneralPanel /> : null}

      {pane === "automation-api" ? (
        <AutomationApiKeyPanel session={session} />
      ) : null}

      {pane === "automation-oauth" ? (
        <AutomationOAuthPanel session={session} />
      ) : null}
    </PortalDetailView>
  );
}

function AutomationGeneralPanel() {
  const budget = usePortalBudgetSettings();
  const [allowOverage, setAllowOverage] = useState(
    budget.settings.allowOverage,
  );

  return (
    <PortalDetailSection
      intro="Control how automation behaves when usage limits are reached."
      title="General settings"
    >
      <Stack gap="md">
        <HardStopEnforcementField
          allowOverage={allowOverage}
          monthlyRequestCap={budget.settings.monthlyRequestCap}
          onChange={(nextHardStopEnabled) => {
            budget.clearNotice();
            setAllowOverage(!nextHardStopEnabled);
          }}
        />

        {budget.error ? (
          <PortalNotice tone="error">
            <p>{budget.error}</p>
          </PortalNotice>
        ) : null}
        {budget.notice ? (
          <PortalNotice tone="warning">
            <p>{budget.notice}</p>
          </PortalNotice>
        ) : null}

        <PortalActionGroup>
          <PortalButton
            disabled={
              budget.isLoading ||
              budget.isSaving ||
              allowOverage === budget.settings.allowOverage
            }
            loading={budget.isSaving}
            onClick={() =>
              void budget.save({
                allowOverage,
                monthlyRequestCap: budget.settings.monthlyRequestCap,
              })
            }
            tone="primary"
            type="button"
          >
            {budget.isSaving
              ? "Saving automation settings..."
              : "Save automation setting"}
          </PortalButton>
        </PortalActionGroup>
      </Stack>
    </PortalDetailSection>
  );
}

function AutomationApiKeyPanel({
  session,
}: {
  session: PortalAuthenticatedSession;
}) {
  const apiKeys = useCustomerUserApiKeys(session.user.email);
  const [name, setName] = useState("");
  const [expirationDate, setExpirationDate] = useState("");
  const [revealedId, setRevealedId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] =
    useState<CustomerUserApiKeyRecord | null>(null);

  return (
    <>
      <PortalDetailSection
        intro="Create and manage API keys for your integrations."
        title="API Keys"
      >
        <CredentialCreateForm
          expirationDate={expirationDate}
          expirationLabel="Expiration date"
          expirationName="API key expiration date"
          name={name}
          nameLabel="API key name"
          namePlaceholder="Primary automation key"
          onExpirationDateChange={setExpirationDate}
          onNameChange={setName}
          onSubmit={() => {
            void apiKeys.createItem({
              expiresAt: expirationDate,
              name,
            });
            setName("");
            setExpirationDate("");
          }}
          submitLabel="Add API key"
        />
      </PortalDetailSection>

      <PortalDetailSection
        intro="Keys stay hidden until you choose to reveal them."
        title="Usable API keys"
      >
        {apiKeys.isLoading ? <p>Loading API keys...</p> : null}
        {!apiKeys.isLoading && apiKeys.items.length === 0 ? (
          <EmptyState
            description="Create an API key to begin wiring automated verification traffic."
            title="No API keys yet"
          />
        ) : null}
        <Stack gap="md">
          {apiKeys.items.map((item) => (
            <CredentialCard
              key={item.id}
              copyLabel="Copy API key"
              createdAt={item.createdAt}
              createdBy={item.createdBy}
              deleteLabel="Delete API key"
              expiresAt={item.expiresAt}
              isRevealed={revealedId === item.id}
              onCopy={() => void copyToClipboard(item.keyValue)}
              onDelete={() => {
                setPendingDelete(item);
              }}
              onToggleReveal={() => {
                setRevealedId((current) =>
                  current === item.id ? null : item.id,
                );
              }}
              revealLabel={
                revealedId === item.id ? "Hide API key" : "Reveal API key"
              }
              secrets={[
                {
                  key: "api-key",
                  label: "API key",
                  value:
                    revealedId === item.id
                      ? item.keyValue
                      : maskSecret(item.keyValue),
                },
              ]}
              title={item.name}
            />
          ))}
        </Stack>
      </PortalDetailSection>

      <DeleteCredentialModal
        itemLabel={pendingDelete?.name ?? null}
        onClose={() => {
          setPendingDelete(null);
        }}
        onConfirm={() => {
          if (!pendingDelete) {
            return;
          }

          void apiKeys.deleteItem(pendingDelete.id);
          setPendingDelete(null);
        }}
        opened={Boolean(pendingDelete)}
      />
    </>
  );
}

function AutomationOAuthPanel({
  session,
}: {
  session: PortalAuthenticatedSession;
}) {
  const oauthClients = useCustomerUserOAuthClients(session.user.email);
  const [name, setName] = useState("");
  const [expirationDate, setExpirationDate] = useState("");
  const [revealedId, setRevealedId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] =
    useState<CustomerUserOAuthClientRecord | null>(null);

  return (
    <>
      <PortalDetailSection
        intro="Create OAuth clients for secure server-to-server access."
        title="OAuth clients"
      >
        <CredentialCreateForm
          expirationDate={expirationDate}
          expirationLabel="Expiration date"
          expirationName="OAuth client expiration date"
          name={name}
          nameLabel="OAuth client name"
          namePlaceholder="Background sync client"
          onExpirationDateChange={setExpirationDate}
          onNameChange={setName}
          onSubmit={() => {
            void oauthClients.createItem({
              expiresAt: expirationDate,
              name,
            });
            setName("");
            setExpirationDate("");
          }}
          submitLabel="Add OAuth client"
        />
      </PortalDetailSection>

      <PortalDetailSection
        intro="Client identifiers and secrets stay masked until explicitly revealed."
        title="Usable OAuth clients"
      >
        {oauthClients.isLoading ? <p>Loading OAuth clients...</p> : null}
        {!oauthClients.isLoading && oauthClients.items.length === 0 ? (
          <EmptyState
            description="Create an OAuth client when you need server-to-server automation credentials."
            title="No OAuth clients yet"
          />
        ) : null}
        <Stack gap="md">
          {oauthClients.items.map((item) => (
            <CredentialCard
              key={item.id}
              copyLabel="Copy OAuth credentials"
              createdAt={item.createdAt}
              createdBy={item.createdBy}
              deleteLabel="Delete OAuth client"
              expiresAt={item.expiresAt}
              isRevealed={revealedId === item.id}
              onCopy={() =>
                void copyToClipboard(
                  JSON.stringify(
                    {
                      client_id: item.clientId,
                      client_secret: item.clientSecret,
                    },
                    null,
                    2,
                  ),
                )
              }
              onDelete={() => {
                setPendingDelete(item);
              }}
              onToggleReveal={() => {
                setRevealedId((current) =>
                  current === item.id ? null : item.id,
                );
              }}
              revealLabel={
                revealedId === item.id
                  ? "Hide OAuth credentials"
                  : "Reveal OAuth credentials"
              }
              secrets={[
                {
                  key: "client-id",
                  label: "Client ID",
                  value:
                    revealedId === item.id
                      ? item.clientId
                      : maskSecret(item.clientId),
                },
                {
                  key: "client-secret",
                  label: "Client secret",
                  value:
                    revealedId === item.id
                      ? item.clientSecret
                      : maskSecret(item.clientSecret),
                },
              ]}
              title={item.name}
            />
          ))}
        </Stack>
      </PortalDetailSection>

      <DeleteCredentialModal
        itemLabel={pendingDelete?.name ?? null}
        onClose={() => {
          setPendingDelete(null);
        }}
        onConfirm={() => {
          if (!pendingDelete) {
            return;
          }

          void oauthClients.deleteItem(pendingDelete.id);
          setPendingDelete(null);
        }}
        opened={Boolean(pendingDelete)}
      />
    </>
  );
}

function CredentialCreateForm(input: {
  expirationDate: string;
  expirationLabel: string;
  expirationName: string;
  name: string;
  nameLabel: string;
  namePlaceholder: string;
  onExpirationDateChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onSubmit: () => void;
  submitLabel: string;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        input.onSubmit();
      }}
    >
      <Stack maw={540}>
        <TextInput
          aria-label={input.nameLabel}
          label="Name"
          onChange={(event) => {
            input.onNameChange(event.target.value);
          }}
          placeholder={input.namePlaceholder}
          value={input.name}
        />

        <TextInput
          aria-label={input.expirationName}
          label={input.expirationLabel}
          min={todayDateValue()}
          onChange={(event) => {
            input.onExpirationDateChange(event.target.value);
          }}
          type="date"
          value={input.expirationDate}
        />

        <PortalActionGroup>
          <Button
            disabled={!input.name.trim() || !input.expirationDate}
            type="submit"
          >
            {input.submitLabel}
          </Button>
        </PortalActionGroup>
      </Stack>
    </form>
  );
}

function CredentialCard({
  copyLabel,
  createdAt,
  createdBy,
  deleteLabel,
  expiresAt,
  isRevealed,
  onCopy,
  onDelete,
  onToggleReveal,
  revealLabel,
  secrets,
  title,
}: {
  copyLabel: string;
  createdAt: string;
  createdBy: string;
  deleteLabel: string;
  expiresAt: string;
  isRevealed: boolean;
  onCopy: () => void;
  onDelete: () => void;
  onToggleReveal: () => void;
  revealLabel: string;
  secrets: Array<{ key: string; label: string; value: string }>;
  title: string;
}) {
  return (
    <Paper className="portal-credential-entry" p="md" radius="md" withBorder>
      <Stack gap="md">
        <Group align="start" justify="space-between" wrap="nowrap">
          <Stack gap={2}>
            <Text component="h3" fw={700}>
              {title}
            </Text>
            <Text c="dimmed" size="sm">
              Expires {formatDate(expiresAt)} | Created by {createdBy}
            </Text>
          </Stack>
          <Group align="center" gap={6} wrap="nowrap">
            <IconActionButton
              ariaLabel={revealLabel}
              icon={isRevealed ? <IconEyeOff size={16} /> : <IconEye size={16} />}
              onClick={onToggleReveal}
              tooltip={revealLabel}
            />
            <IconActionButton
              ariaLabel={copyLabel}
              icon={<IconCopy size={16} />}
              onClick={onCopy}
              tooltip={copyLabel}
            />
            <IconActionButton
              ariaLabel={deleteLabel}
              icon={<IconTrash size={16} />}
              onClick={onDelete}
              tooltip={deleteLabel}
            />
          </Group>
        </Group>

        <DetailFieldList
          items={[
            ...secrets.map((secret) => ({
              key: secret.key,
              label: secret.label,
              value: secret.value,
            })),
            {
              key: "created-at",
              label: "Created",
              value: formatDateTime(createdAt),
            },
          ]}
        />
      </Stack>
    </Paper>
  );
}

function DeleteCredentialModal({
  itemLabel,
  onClose,
  onConfirm,
  opened,
}: {
  itemLabel: string | null;
  onClose: () => void;
  onConfirm: () => void;
  opened: boolean;
}) {
  return (
    <Modal
      centered
      onClose={onClose}
      opened={opened}
      title="Confirm credential deletion"
    >
      <Stack gap="md">
        <Text size="sm">
          Delete <strong>{itemLabel ?? "this credential"}</strong>? This action
          removes it from your saved credentials list.
        </Text>
        <Group justify="flex-end">
          <PortalButton onClick={onClose} tone="secondary" type="button">
            Cancel
          </PortalButton>
          <PortalButton onClick={onConfirm} tone="danger" type="button">
            Delete
          </PortalButton>
        </Group>
      </Stack>
    </Modal>
  );
}

function IconActionButton({
  ariaLabel,
  icon,
  onClick,
  tooltip,
}: {
  ariaLabel: string;
  icon: ReactNode;
  onClick: () => void;
  tooltip: string;
}) {
  return (
    <Tooltip label={tooltip} withArrow withinPortal={false}>
      <ActionIcon
        aria-label={ariaLabel}
        color="gray"
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

function formatDate(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Date(parsed).toLocaleDateString();
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }

  return new Date(parsed).toLocaleString();
}

function maskSecret(value: string) {
  return "*".repeat(Math.max(12, value.length));
}

async function copyToClipboard(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
  }
}

function todayDateValue() {
  return new Date().toISOString().slice(0, 10);
}
