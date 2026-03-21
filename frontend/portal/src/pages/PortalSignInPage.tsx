import { Inline } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";

interface PortalSignInPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onSignIn: () => Promise<void>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalSignInPage({
  endpoints,
  isBusy,
  onSignIn,
  requestedRoute,
}: PortalSignInPageProps) {
  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__copy">
        <h2>Sign in to continue</h2>
        <p>
          The portal keeps application routes behind an explicit auth boundary.
          This local-development flow uses a mock browser session now, while the
          real provider and session exchange stay deferred.
        </p>
      </div>

      <dl className="portal-shell__details">
        <div>
          <dt>Requested area</dt>
          <dd>{requestedRoute.label}</dd>
        </div>
        <div>
          <dt>Current backend auth anchor</dt>
          <dd>
            <code>{endpoints.oauthToken}</code>
          </dd>
        </div>
      </dl>

      <div className="portal-auth-page__onboarding">
        <p className="portal-shell__eyebrow">Start without pressure</p>
        <h3>Free tier first, trial only when it helps</h3>
        <ul className="portal-list">
          <li>
            Free tier limits stay visible after sign-in so onboarding is
            predictable.
          </li>
          <li>
            A trial can activate later around real product use instead of being
            forced during sign-in.
          </li>
          <li>
            Moving to a paid plan remains a separate choice, not an automatic
            trial outcome.
          </li>
        </ul>
      </div>

      <Inline className="portal-auth-page__actions">
        <button
          className="portal-shell__action portal-shell__action--primary"
          disabled={isBusy}
          onClick={() => void onSignIn()}
          type="button"
        >
          {isBusy ? "Starting session..." : "Continue with demo session"}
        </button>
      </Inline>

      <ul className="portal-list portal-auth-page__list">
        <li>
          Protected portal routes never render authenticated content
          anonymously.
        </li>
        <li>
          Future browser auth can exchange into backend account and workspace
          context without exposing raw API keys in the UI.
        </li>
        <li>
          Role and scope arrays already exist in session state, but no fixed
          RBAC policy is hardcoded into this shell yet.
        </li>
      </ul>
    </div>
  );
}
