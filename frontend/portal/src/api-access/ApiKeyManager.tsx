import { useState } from "react";
import { Grid, Inline, Panel } from "@charity-status/shared-ui";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { usePortalApiKeys, type PortalApiKeysState } from "./usePortalApiKeys";

interface ApiKeyManagerProps {
  controller?: PortalApiKeysState;
}

export function ApiKeyManager({ controller }: ApiKeyManagerProps) {
  const organization = usePortalOrganization();
  const defaultController = usePortalApiKeys();
  const apiKeys = controller ?? defaultController;
  const [label, setLabel] = useState("");
  const [scopes, setScopes] = useState(apiKeys.scopesPlaceholder);

  const activeKeys = apiKeys.items.filter((item) => item.status === "active");
  const revokedKeys = apiKeys.items.filter((item) => item.status === "revoked");

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="API key management"
        subtitle="This is the portal-owned UI for customer API credentials."
      >
        <p>
          The portal now scopes API credential management to{" "}
          <strong>{organization.activeOrganization.organization_name}</strong>.
          Backend customer self-serve API-key routes are not available yet, so
          this page uses a replaceable local mock service with one-time secret
          visibility.
        </p>

        <dl className="portal-shell__details">
          <div>
            <dt>Workspace</dt>
            <dd>{organization.activeOrganization.workspace_id}</dd>
          </div>
          <div>
            <dt>Account</dt>
            <dd>{organization.activeOrganization.account_id}</dd>
          </div>
          <div>
            <dt>Credential service</dt>
            <dd>{apiKeys.implementation ?? "loading"}</dd>
          </div>
        </dl>

        <form
          className="portal-form"
          onSubmit={(event) => {
            event.preventDefault();
            void apiKeys.createKey({
              label,
              scopes: scopes
                .split(",")
                .map((scope) => scope.trim())
                .filter(Boolean),
            });
            setLabel("");
          }}
        >
          <label className="portal-form__field">
            <span>Key label</span>
            <input
              className="portal-form__input"
              name="label"
              onChange={(event) => {
                setLabel(event.target.value);
              }}
              placeholder="Production integration"
              type="text"
              value={label}
            />
          </label>

          <label className="portal-form__field">
            <span>Scopes</span>
            <input
              className="portal-form__input"
              name="scopes"
              onChange={(event) => {
                setScopes(event.target.value);
              }}
              placeholder={apiKeys.scopesPlaceholder}
              type="text"
              value={scopes}
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
                void apiKeys.refresh();
              }}
              type="button"
            >
              Refresh list
            </button>
          </Inline>
        </form>

        {apiKeys.error ? (
          <p className="portal-feedback portal-feedback--error">
            {apiKeys.error}
          </p>
        ) : null}
      </Panel>

      {apiKeys.visibleSecret ? (
        <Panel
          title="Copy this secret now"
          subtitle="The plaintext API key is shown once and is not persisted in portal storage."
        >
          <p className="portal-feedback portal-feedback--warning">
            Store this key in your secrets manager before leaving the page.
          </p>
          <code className="portal-secret">{apiKeys.visibleSecret.secret}</code>
          <Inline className="portal-form__actions">
            <span className="portal-key-chip">
              {apiKeys.visibleSecret.key.label}
            </span>
            <button
              className="portal-shell__action"
              onClick={apiKeys.dismissSecret}
              type="button"
            >
              Dismiss secret
            </button>
          </Inline>
        </Panel>
      ) : null}

      <Panel
        title="Active API keys"
        subtitle="Secrets are never shown again after creation."
      >
        {apiKeys.isLoading ? <p>Loading API keys...</p> : null}
        {!apiKeys.isLoading && activeKeys.length === 0 ? (
          <p>No active API keys yet for this organization.</p>
        ) : null}

        <div className="portal-key-list">
          {activeKeys.map((key) => (
            <article className="portal-key-card" key={key.key_id}>
              <div className="portal-key-card__header">
                <div>
                  <h3>{key.label}</h3>
                  <p>{key.key_prefix}...</p>
                </div>
                <span className="portal-key-chip portal-key-chip--active">
                  active
                </span>
              </div>

              <dl className="portal-shell__details">
                <div>
                  <dt>Key ID</dt>
                  <dd>{key.key_id}</dd>
                </div>
                <div>
                  <dt>Scopes</dt>
                  <dd>{key.scopes.join(", ")}</dd>
                </div>
                <div>
                  <dt>Created</dt>
                  <dd>{formatDateTime(key.created_at)}</dd>
                </div>
              </dl>

              <Inline className="portal-form__actions">
                <button
                  className="portal-shell__action portal-shell__action--danger"
                  disabled={apiKeys.isRevokingKeyId === key.key_id}
                  onClick={() => {
                    void apiKeys.revokeKey(key.key_id);
                  }}
                  type="button"
                >
                  {apiKeys.isRevokingKeyId === key.key_id
                    ? "Revoking..."
                    : "Revoke key"}
                </button>
              </Inline>
            </article>
          ))}
        </div>
      </Panel>

      <Panel
        title="Revoked keys"
        subtitle="Revoked keys remain visible as audit-friendly metadata only."
      >
        {revokedKeys.length === 0 ? <p>No revoked keys yet.</p> : null}
        <div className="portal-key-list">
          {revokedKeys.map((key) => (
            <article className="portal-key-card" key={key.key_id}>
              <div className="portal-key-card__header">
                <div>
                  <h3>{key.label}</h3>
                  <p>{key.key_prefix}...</p>
                </div>
                <span className="portal-key-chip portal-key-chip--revoked">
                  revoked
                </span>
              </div>
              <dl className="portal-shell__details">
                <div>
                  <dt>Key ID</dt>
                  <dd>{key.key_id}</dd>
                </div>
                <div>
                  <dt>Scopes</dt>
                  <dd>{key.scopes.join(", ")}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </Panel>
    </Grid>
  );
}

function formatDateTime(value: string): string {
  const parsedValue = Date.parse(value);
  if (Number.isNaN(parsedValue)) {
    return value;
  }

  return new Date(parsedValue).toLocaleString();
}
