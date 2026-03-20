import { Grid, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";

interface ApiAccessPageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function ApiAccessPage({ endpoints, session }: ApiAccessPageProps) {
  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Authentication-adjacent shell"
        subtitle="Credential workflows stay stubbed for now."
      >
        <p>
          Customers currently authenticate through issued API keys or OAuth
          client credentials. This page reserves the portal home for future
          self-serve credential visibility without assuming that issuance
          becomes a portal feature immediately.
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

      <Panel
        title="Intentionally deferred"
        subtitle="Kept out of this bootstrap phase."
      >
        <ul className="portal-list">
          <li>No full credential issuance or rotation workflow yet.</li>
          <li>No secret-display UX yet.</li>
          <li>No user-role assumptions baked into page state.</li>
        </ul>
      </Panel>
    </Grid>
  );
}
