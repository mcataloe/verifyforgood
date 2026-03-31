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
          <h2>Sign in first, then manage your organization workspace</h2>
          <p>
            Access the authenticated portal for verification workflows, billing
            visibility, API credentials, and organization settings. Account
            authentication always happens before organization creation or
            selection.
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
                ? "You will continue to dashboard or organization onboarding."
                : `You will continue to ${requestedRoute.label}.`}
            </span>
          </div>
          <div>
            <strong>Organization flow</strong>
            <span>
              Organization setup appears only when the authenticated account has
              no organization context yet.
            </span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What opens after sign-in</p>
          <h3>Protected operations stay behind one clear auth boundary</h3>
          <ul className="portal-list">
            <li>
              Existing organization context routes directly into the dashboard.
            </li>
            <li>
              First-time authenticated users without organizations are routed to
              explicit organization onboarding.
            </li>
            <li>
              No organization is created silently or before authentication.
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
          <span>Portal scope</span>
        </div>

        <ul className="portal-auth-page__list portal-list">
          <li>Verification dashboard and organization activity</li>
          <li>Tenant-aware nonprofit workspace and detail review</li>
          <li>Usage, billing, settings, and API credential management</li>
        </ul>
      </div>
    </div>
  );
}
