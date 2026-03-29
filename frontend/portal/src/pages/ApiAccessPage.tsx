import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import { ApiKeyManager } from "../api-access/ApiKeyManager";
import {
  PortalActionToolbar,
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
      description="Manage self-serve API credentials and keep the OAuth boundary explicit for operational admin workflows."
      eyebrow={pane === "api" ? "Customer admin API" : "Customer portal API"}
      title="API access"
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Auth {session.auth_method.replaceAll("_", " ")}
            </span>
            <span className="portal-shell__summary-pill">
              {session.scopes.length} scopes
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <Panel
        title="Credential access"
        subtitle="API keys are managed through the organization-scoped backend lifecycle."
      >
        <PortalSectionHeader
          description="Use the shared account shell to manage customer credentials without mixing OAuth token exchange details into the rest of the portal."
          eyebrow="Shared admin shell"
          title="Keep API workflows consistent"
        />
        <p>
          Customers authenticate through issued API keys or OAuth client
          credentials. API key lifecycle is now backed by the current
          organization routes, while OAuth token exchange continues to anchor at{" "}
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
    </PortalPageShell>
  );
}
