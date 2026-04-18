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
        title="API key management"
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
            <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
          </div>
        </dl>

        {!canManageKeys ? (
          <PortalNotice title="Admin access required" tone="warning">
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
                {apiKeys.isCreating ? "Creating key..." : "Create API key"}
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
                Refresh keys
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
          title="Copy this secret now"
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
              Dismiss secret
            </button>
          </Inline>
        </Panel>
      ) : null}

      <Panel
        title="Organization API keys"
        subtitle="Secrets are never shown again after creation."
      >
        {apiKeys.isLoading ? (
          <PortalNotice title="Loading" tone="loading">
            <p>Loading API keys for the current organization.</p>
          </PortalNotice>
        ) : null}
        {!apiKeys.isLoading && sortedKeys.length === 0 ? (
          <PortalNotice title="Nothing to show yet" tone="empty">
            <p>Create a key to start authenticating API traffic.</p>
          </PortalNotice>
        ) : null}

        {sortedKeys.length > 0 ? (
          <table className="portal-table">
            <thead>
              <tr>
                <th>Display name</th>
                <th>Status</th>
                <th>Created</th>
                <th>Last used</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sortedKeys.map((key) => (
                <tr key={key.key_id}>
                  <td>{key.display_name}</td>
                  <td>{key.status}</td>
                  <td>{formatDateTime(key.created_at)}</td>
                  <td>
                    {key.last_used_at
                      ? formatDateTime(key.last_used_at)
                      : "Never used"}
                  </td>
                  <td>
                    {key.status === "revoked" || !canManageKeys ? (
                      <span>
                        {key.status === "revoked" ? "Revoked" : "Read only"}
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
                            : "Confirm revoke"}
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
                        Revoke key
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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

  return new Date(parsedValue).toLocaleString();
}
