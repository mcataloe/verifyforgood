import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { ApiKeyManager } from "../api-access/ApiKeyManager";

interface ApiAccessPageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function ApiAccessPage({ endpoints, session }: ApiAccessPageProps) {
  return (
    <>
      <Panel
        title="Credential access"
        subtitle="API keys now have a minimal self-serve portal surface."
      >
        <p>
          Customers authenticate through issued API keys or OAuth client
          credentials. The portal now owns a minimal API-key management flow,
          while OAuth token exchange continues to anchor at{" "}
          <code>{endpoints.oauthToken}</code>.
        </p>
        <dl className="portal-shell__details">
          <div>
            <dt>Portal auth mode</dt>
            <dd>{session.auth_method.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>Available scopes</dt>
            <dd>{session.scopes.join(", ")}</dd>
          </div>
          <div>
            <dt>OAuth token route</dt>
            <dd>
              <code>{endpoints.oauthToken}</code>
            </dd>
          </div>
        </dl>
      </Panel>
      <ApiKeyManager />
    </>
  );
}
