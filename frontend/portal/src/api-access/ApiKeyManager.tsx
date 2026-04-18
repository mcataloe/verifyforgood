import { IconCopy, IconEye, IconEyeOff } from "@tabler/icons-react";
import { useState } from "react";
import { Inline, Panel } from "@charity-status/shared-ui";
import { PortalNotice } from "../components/feedback";
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
  const [pendingRevokeKeyId, setPendingRevokeKeyId] = useState<string | null>(
    null,
  );
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [isSecretVisible, setIsSecretVisible] = useState(false);

  const sortedKeys = [...apiKeys.items].sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  );

  return (
    <StackedDetailSections>
      <Panel
        title="API Key Management"
        subtitle="Create, review, and revoke API keys for your organization."
      >
        <p>
          API keys created here belong to{" "}
          <strong>{organization.activeOrganization.organization_name}</strong>
          {" "}and can only be shown in plaintext once at creation time.
        </p>

        <dl className="portal-shell__details">
          <div>
            <dt>Your role</dt>
            <dd>{formatLabelValue(organization.currentMembership?.role)}</dd>
          </div>
        </dl>

        {!canManageKeys ? (
          <PortalNotice title="Admin Access Required" tone="warning">
            <p>
              Only organization admins may create or revoke API keys for this
              organization.
            </p>
          </PortalNotice>
        ) : (
          <form
            className="portal-form"
            onSubmit={(event) => {
              event.preventDefault();
              setCopyFeedback(null);
              setIsSecretVisible(false);
              void apiKeys.createKey({
                display_name: displayName,
              });
              setDisplayName("");
            }}
          >
            <label className="portal-form__field">
              <span>Display name</span>
              <input
                className="portal-form__input"
                name="display-name"
                onChange={(event) => {
                  setDisplayName(event.target.value);
                }}
                placeholder="Server integration"
                type="text"
                value={displayName}
              />
            </label>

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
                Refresh Keys
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
          <PortalNotice tone="warning">
            <p>
              Store this key in your secrets manager before leaving the page.
            </p>
          </PortalNotice>
          {copyFeedback ? (
            <PortalNotice tone="warning">
              <p>{copyFeedback}</p>
            </PortalNotice>
          ) : null}
          <label className="portal-form__field" htmlFor="plaintext-api-key">
            <span>Plaintext API key</span>
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
                <button
                  aria-label={isSecretVisible ? "Hide API key" : "Reveal API key"}
                  className="portal-secret-field__action"
                  onClick={() => {
                    setIsSecretVisible((current) => !current);
                  }}
                  title={isSecretVisible ? "Hide API key" : "Reveal API key"}
                  type="button"
                >
                  {isSecretVisible ? (
                    <IconEyeOff aria-hidden="true" size={16} />
                  ) : (
                    <IconEye aria-hidden="true" size={16} />
                  )}
                </button>
                <button
                  aria-label="Copy key"
                  className="portal-secret-field__action"
                  onClick={() => {
                    void copySecretToClipboard({
                      onResult: setCopyFeedback,
                      secret: apiKeys.visibleSecret?.secret ?? "",
                    });
                  }}
                  title="Copy key"
                  type="button"
                >
                  <IconCopy aria-hidden="true" size={16} />
                </button>
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
              Dismiss Secret
            </button>
          </Inline>
        </Panel>
      ) : null}

      <Panel
        title="Organization API Keys"
        subtitle="Secrets are never shown again after creation."
      >
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
          <div className="portal-key-list">
            {sortedKeys.map((key) => (
              <article className="portal-key-card" key={key.key_id}>
                <div className="portal-key-card__header">
                  <div>
                    <h3>{key.display_name}</h3>
                    <p>Created {formatDateTime(key.created_at)}</p>
                  </div>
                  <span
                    className={`portal-key-chip ${
                      key.status === "revoked"
                        ? "portal-key-chip--revoked"
                        : "portal-key-chip--active"
                    }`}
                  >
                    {formatLabelValue(key.status)}
                  </span>
                </div>

                <dl className="portal-key-card__meta">
                  <div>
                    <dt>Last Used</dt>
                    <dd>
                      {key.last_used_at
                        ? formatDateTime(key.last_used_at)
                        : "Never Used"}
                    </dd>
                  </div>
                  <div>
                    <dt>Key Access</dt>
                    <dd>{canManageKeys ? "Managed Here" : "Read Only"}</dd>
                  </div>
                </dl>

                <div className="portal-key-card__actions">
                  {key.status === "revoked" || !canManageKeys ? (
                    <span className="portal-key-card__action-note">
                      {key.status === "revoked" ? "Revoked" : "Read Only"}
                    </span>
                  ) : pendingRevokeKeyId === key.key_id ? (
                    <Inline className="portal-form__actions">
                      <button
                        className="portal-shell__action portal-shell__action--danger"
                        disabled={apiKeys.isRevokingKeyId === key.key_id}
                        onClick={() => {
                          void apiKeys.revokeKey(key.key_id);
                          setPendingRevokeKeyId(null);
                        }}
                        type="button"
                      >
                        {apiKeys.isRevokingKeyId === key.key_id
                          ? "Revoking..."
                          : "Confirm Revoke"}
                      </button>
                      <button
                        className="portal-shell__action"
                        disabled={apiKeys.isRevokingKeyId === key.key_id}
                        onClick={() => {
                          setPendingRevokeKeyId(null);
                        }}
                        type="button"
                      >
                        Cancel
                      </button>
                    </Inline>
                  ) : (
                    <button
                      className="portal-shell__action portal-shell__action--danger"
                      disabled={apiKeys.isRevokingKeyId === key.key_id}
                      onClick={() => {
                        setPendingRevokeKeyId(key.key_id);
                      }}
                      type="button"
                    >
                      Revoke Key
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </Panel>
    </StackedDetailSections>
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
