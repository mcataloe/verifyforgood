import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalSignInMethod, PortalSignInRequest } from "../auth/portalAuthClient";

interface PortalSignInPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onSignIn: (request: PortalSignInRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalSignInPage({
  endpoints,
  isBusy,
  onSignIn,
  requestedRoute,
}: PortalSignInPageProps) {
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [activeMethod, setActiveMethod] = useState<PortalSignInMethod | null>(
    null,
  );
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const beginSignIn = async (request: PortalSignInRequest) => {
    setValidationMessage(null);
    setActiveMethod(request.method);
    try {
      await onSignIn(request);
    } finally {
      setActiveMethod(null);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      setValidationMessage("Enter both email and password to continue.");
      return;
    }

    await beginSignIn({
      email,
      method: "password",
      password,
    });
  };

  const isSubmitting = isBusy || activeMethod !== null;

  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <p className="portal-shell__eyebrow">Portal entry</p>
          <h2>Secure access for verification operations</h2>
          <p>
            Sign in to continue to {requestedRoute.label}. The current frontend
            flow stays mock-backed for local development, but the screen is
            structured for email/password and future browser identity providers.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Requested area</strong>
            <span>{requestedRoute.label}</span>
          </div>
          <div>
            <strong>Backend auth anchor</strong>
            <span>
              <code>{endpoints.oauthToken}</code>
            </span>
          </div>
          <div>
            <strong>Current mode</strong>
            <span>Mock browser session for local development</span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What stays true after sign-in</p>
          <h3>Low-friction access with room for real identity later</h3>
          <ul className="portal-list">
            <li>
              Protected routes remain behind the same auth boundary regardless
              of which entry method is used.
            </li>
            <li>
              Plan, role, and organization context still come from the portal
              session model rather than page-local assumptions.
            </li>
            <li>
              Future Google, Microsoft, and browser-session exchange work can
              plug into this screen without changing the route structure.
            </li>
          </ul>
        </div>
      </div>

      <form className="portal-auth-page__card portal-form" noValidate onSubmit={handlePasswordSubmit}>
        <div className="portal-auth-page__card-copy">
          <p className="portal-shell__eyebrow">Welcome back</p>
          <h3>Sign in</h3>
          <p>Use your work email, or continue with your identity provider.</p>
        </div>

        <label className="portal-form__field" htmlFor={emailId}>
          <span>Email</span>
          <input
            autoComplete="email"
            className="portal-form__input"
            id={emailId}
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@company.com"
            type="email"
            value={email}
          />
        </label>

        <label className="portal-form__field" htmlFor={passwordId}>
          <span>Password</span>
          <input
            autoComplete="current-password"
            className="portal-form__input"
            id={passwordId}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            type="password"
            value={password}
          />
        </label>

        {validationMessage ? (
          <p aria-live="polite" className="portal-auth-page__error" role="alert">
            {validationMessage}
          </p>
        ) : null}

        <div className="portal-form__actions">
          <button
            className="portal-shell__action portal-shell__action--primary"
            disabled={isSubmitting}
            type="submit"
          >
            {activeMethod === "password" || (isBusy && !activeMethod)
              ? "Signing in..."
              : "Sign in"}
          </button>
        </div>

        <div className="portal-auth-page__divider" role="presentation">
          <span>Or continue with</span>
        </div>

        <div className="portal-auth-page__oauth">
          <button
            className="portal-auth-page__oauth-button portal-auth-page__oauth-button--google"
            disabled={isSubmitting}
            onClick={() =>
              void beginSignIn({
                email,
                method: "google",
              })
            }
            type="button"
          >
            <span aria-hidden="true" className="portal-auth-page__oauth-mark">
              G
            </span>
            Continue with Google
          </button>

          <button
            className="portal-auth-page__oauth-button portal-auth-page__oauth-button--microsoft"
            disabled={isSubmitting}
            onClick={() =>
              void beginSignIn({
                email,
                method: "microsoft",
              })
            }
            type="button"
          >
            <span
              aria-hidden="true"
              className="portal-auth-page__oauth-mark portal-auth-page__oauth-mark--microsoft"
            >
              <span />
              <span />
              <span />
              <span />
            </span>
            Continue with Microsoft
          </button>
        </div>

        <div className="portal-auth-page__utility-links">
          <a href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20password%20help">
            Forgot password
          </a>
          <a href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20access%20request">
            Request access
          </a>
          <a href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20help">
            Help
          </a>
        </div>

        <p className="portal-auth-page__legal">
          Terms and privacy links should come from the public site when real
          identity integration lands. For now, all three entry methods create
          the same local mock session.
        </p>
      </form>
    </div>
  );
}
