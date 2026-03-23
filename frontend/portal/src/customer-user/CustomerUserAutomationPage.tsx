import {
  ActionIcon,
  Group,
  Modal,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
import {
  EmptyState,
} from "@charity-status/shared-ui";
import {
  IconCopy,
  IconEye,
  IconEyeOff,
  IconTrash,
} from "@tabler/icons-react";
import { useState, type ReactNode } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalBudgetSettings } from "../settings/usePortalBudgetSettings";
import { HardStopEnforcementField } from "../settings/HardStopEnforcementField";
import type {
  CustomerUserApiKeyRecord,
  CustomerUserOAuthClientRecord,
} from "./automationCredentials";
import {
  useCustomerUserApiKeys,
  useCustomerUserOAuthClients,
} from "./useCustomerUserAutomationCredentials";
import { PortalDetailSection, PortalDetailView } from "../components/PortalDetailView";

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
        ? "Generate masked API keys for direct integrations. The local mock persists credentials in browser storage for this phase only."
        : "Generate client credentials for server-to-server OAuth automation without introducing backend token issuance yet.";

  return (
    <PortalDetailView
        eyebrow="Automation"
        intro={description}
        title={title}
      >

      {pane === "automation-general" ? (
        <AutomationGeneralPanel />
      ) : null}

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
      intro="This pane intentionally contains only the hard-stop automation control in this phase."
      title="General settings"
    >
      <div className="portal-budget-form">
        <HardStopEnforcementField
          allowOverage={allowOverage}
          monthlyRequestCap={budget.settings.monthlyRequestCap}
          onChange={(nextHardStopEnabled) => {
            budget.clearNotice();
            setAllowOverage(!nextHardStopEnabled);
          }}
        />

        {budget.error ? (
          <p className="portal-feedback portal-feedback--error">
            {budget.error}
          </p>
        ) : null}
        {budget.notice ? (
          <p className="portal-feedback portal-feedback--warning">
            {budget.notice}
          </p>
        ) : null}

        <div className="portal-form__actions">
          <button
            className="portal-shell__action portal-shell__action--primary"
            disabled={
              budget.isLoading ||
              budget.isSaving ||
              allowOverage === budget.settings.allowOverage
            }
            onClick={() =>
              void budget.save({
                allowOverage,
                monthlyRequestCap: budget.settings.monthlyRequestCap,
              })
            }
            type="button"
          >
            {budget.isSaving ? "Saving automation settings..." : "Save automation setting"}
          </button>
        </div>
      </div>
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
        intro="Create browser-local placeholder keys with audit metadata that can later align to a backend customer credential API."
        title="API Keys"
      >
        <form
          className="portal-form portal-form--two-column"
          onSubmit={(event) => {
            event.preventDefault();
            void apiKeys.createItem({
              expiresAt: expirationDate,
              name,
            });
            setName("");
            setExpirationDate("");
          }}
        >
          <label className="portal-form__field">
            <span>Name</span>
            <input
              aria-label="API key name"
              className="portal-form__input"
              onChange={(event) => {
                setName(event.target.value);
              }}
              placeholder="Primary automation key"
              type="text"
              value={name}
            />
          </label>

          <label className="portal-form__field">
            <span>Expiration date</span>
            <input
              aria-label="API key expiration date"
              className="portal-form__input"
              min={todayDateValue()}
              onChange={(event) => {
                setExpirationDate(event.target.value);
              }}
              type="date"
              value={expirationDate}
            />
          </label>

          <div className="portal-form__actions portal-form__actions--full">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={!name.trim() || !expirationDate}
              type="submit"
            >
              Add API key
            </button>
          </div>
        </form>

        <p className="portal-settings-preferences__note">
          Backend coordination note: `created_by` is being captured locally from
          the signed-in portal user and should align with the eventual customer
          credential API contract.
        </p>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Keys are masked by default and surfaced here as placeholder values only."
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
              createdAt={item.createdAt}
              createdBy={item.createdBy}
              expiresAt={item.expiresAt}
              onCopy={() => void copyToClipboard(item.keyValue)}
              onDelete={() => {
                setPendingDelete(item);
              }}
              onToggleReveal={() => {
                setRevealedId((current) => (current === item.id ? null : item.id));
              }}
              revealLabel={
                revealedId === item.id ? "Hide API key" : "Reveal API key"
              }
              secrets={[
                {
                  key: "api-key",
                  label: "API key",
                  value: revealedId === item.id ? item.keyValue : maskSecret(item.keyValue),
                },
              ]}
              title={item.name}
              deleteLabel="Delete API key"
              copyLabel="Copy API key"
              isRevealed={revealedId === item.id}
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
        intro="Generate placeholder client credentials with the same title-row action pattern as API keys."
        title="OAuth clients"
      >
        <form
          className="portal-form portal-form--two-column"
          onSubmit={(event) => {
            event.preventDefault();
            void oauthClients.createItem({
              expiresAt: expirationDate,
              name,
            });
            setName("");
            setExpirationDate("");
          }}
        >
          <label className="portal-form__field">
            <span>Name</span>
            <input
              aria-label="OAuth client name"
              className="portal-form__input"
              onChange={(event) => {
                setName(event.target.value);
              }}
              placeholder="Background sync client"
              type="text"
              value={name}
            />
          </label>

          <label className="portal-form__field">
            <span>Expiration date</span>
            <input
              aria-label="OAuth client expiration date"
              className="portal-form__input"
              min={todayDateValue()}
              onChange={(event) => {
                setExpirationDate(event.target.value);
              }}
              type="date"
              value={expirationDate}
            />
          </label>

          <div className="portal-form__actions portal-form__actions--full">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={!name.trim() || !expirationDate}
              type="submit"
            >
              Add OAuth client
            </button>
          </div>
        </form>

        <p className="portal-settings-preferences__note">
          Backend coordination note: generated `client_id`, `client_secret`,
          and `created_by` metadata are local placeholders until customer OAuth
          lifecycle endpoints exist.
        </p>
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
              createdAt={item.createdAt}
              createdBy={item.createdBy}
              expiresAt={item.expiresAt}
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
                setRevealedId((current) => (current === item.id ? null : item.id));
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
              deleteLabel="Delete OAuth client"
              copyLabel="Copy OAuth credentials"
              isRevealed={revealedId === item.id}
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
    <article className="portal-credential-card">
      <Group justify="space-between" wrap="nowrap" align="start">
        <div>
          <h3 className="portal-credential-card__title">{title}</h3>
          <p className="portal-credential-card__meta">
            Expires {formatDate(expiresAt)} | Created by {createdBy}
          </p>
        </div>
        <Group className="portal-credential-card__actions" gap={6} wrap="nowrap">
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

      <dl className="portal-credential-card__secrets">
        {secrets.map((secret) => (
          <div key={secret.key}>
            <dt>{secret.label}</dt>
            <dd>{secret.value}</dd>
          </div>
        ))}
        <div>
          <dt>Created</dt>
          <dd>{formatDateTime(createdAt)}</dd>
        </div>
      </dl>
    </article>
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
          removes the placeholder credential from the local portal store.
        </Text>
        <Group justify="flex-end">
          <button className="portal-shell__action portal-shell__action--secondary" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="portal-shell__action portal-shell__action--danger" onClick={onConfirm} type="button">
            Delete
          </button>
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
        className="portal-credential-card__action"
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
