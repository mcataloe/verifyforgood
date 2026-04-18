import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import { ApiKeyManager } from "../api-access/ApiKeyManager";
import {
  PortalPageShell,
  PortalSectionHeader,
} from "../components/shell";

interface ApiAccessPageProps {
  endpoints: PortalEndpoints;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
}

export function ApiAccessPage({
  endpoints,
  pane,
  session,
}: ApiAccessPageProps) {
  return (
    <PortalPageShell
      description="Create and manage API keys for your organization."
      eyebrow={pane === "api" ? "Customer admin API" : "Customer portal API"}
      title="API access"
    >
      <Panel
        title="API credentials"
        subtitle="Manage API keys for your organization and review available access."
      >
        <PortalSectionHeader
          description="Use this page to manage API access for your organization."
          eyebrow="Organization access"
          title="Manage API access"
        />
        <p>
          Use API keys for server-to-server integrations. If your team also uses
          OAuth, token requests are available at <code>{endpoints.oauthToken}</code>.
        </p>
        <dl className="portal-shell__details">
          <div>
            <dt>Sign-in method</dt>
            <dd>{session.auth_method.replaceAll("_", " ")}</dd>
          </div>
          <div>
            <dt>Available access</dt>
            <dd>{session.scopes.join(", ")}</dd>
          </div>
          <div>
            <dt>OAuth token URL</dt>
            <dd>
              <code>{endpoints.oauthToken}</code>
            </dd>
          </div>
        </dl>
      </Panel>
      <ApiKeyManager />
    </PortalPageShell>
  );
}
