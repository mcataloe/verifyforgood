import type { PortalRouteDefinition } from "../app/portalRoutes";

interface PortalHomePageProps {
  requestedRoute: PortalRouteDefinition;
}

export function PortalHomePage({ requestedRoute }: PortalHomePageProps) {
  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <p className="portal-shell__eyebrow">Customer portal</p>
          <h2>Sign in to manage your organization</h2>
          <p>
            Access billing, team access, API credentials, and verification
            activity from one secure account. Sign in first, then create or
            join an organization if needed.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Primary next step</strong>
            <span>Sign in or create an account</span>
          </div>
          <div>
            <strong>After authentication</strong>
            <span>
              {requestedRoute.key === "home"
                ? "You will continue to your dashboard or organization setup."
                : `You will continue to ${requestedRoute.label}.`}
            </span>
          </div>
          <div>
            <strong>Organization setup</strong>
            <span>
              Organization setup appears only if your account does not already
              belong to an organization.
            </span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What happens next</p>
          <h3>Get started quickly</h3>
          <ul className="portal-list">
            <li>
              If you already belong to an organization, you go straight to your
              dashboard.
            </li>
            <li>
              If you are new, you can create your organization in a dedicated
              setup step.
            </li>
            <li>
              Your account is always authenticated before organization setup.
            </li>
          </ul>
        </div>
      </div>

      <div className="portal-auth-page__card portal-form">
        <div className="portal-auth-page__card-copy">
          <p className="portal-shell__eyebrow">Portal entry</p>
          <h3>Start with authentication</h3>
          <p>Choose the account flow that fits your current state.</p>
        </div>

        <div className="portal-form__actions" data-testid="public-home-auth-cta">
          <a
            className="portal-shell__action portal-shell__action--primary"
            href="#/sign-in"
          >
            Sign in
          </a>
          <a
            className="portal-shell__action portal-shell__action--secondary"
            href="#/register"
          >
            Create account
          </a>
        </div>

        <div className="portal-auth-page__divider" role="presentation">
          <span>What you can manage</span>
        </div>

        <ul className="portal-auth-page__list portal-list">
          <li>Verification dashboard and organization activity</li>
          <li>Nonprofit search and detailed review</li>
          <li>Usage, billing, settings, and API credential management</li>
        </ul>
      </div>
    </div>
  );
}
