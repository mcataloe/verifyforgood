import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalLoginRequest } from "../auth/portalAuthClient";

interface PortalSignInPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onLogin: (request: PortalLoginRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalSignInPage({
  endpoints,
  isBusy,
  onLogin,
  requestedRoute,
}: PortalSignInPageProps) {
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      setValidationMessage("Enter both email and password to continue.");
      return;
    }

    setValidationMessage(null);

    try {
      await onLogin({
        email,
        password,
      });
    } catch (error) {
      setValidationMessage(
        error instanceof Error ? error.message : "Sign-in failed.",
      );
    }
  };

  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <p className="portal-shell__eyebrow">Portal entry</p>
          <h2>Secure access for verification operations</h2>
          <p>
            Sign in to continue to {requestedRoute.label}. This frontend now
            uses the backend portal auth endpoints and restores the browser
            session through <code>{endpoints.authMe}</code>.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Requested area</strong>
            <span>{requestedRoute.label}</span>
          </div>
          <div>
            <strong>Login endpoint</strong>
            <span>
              <code>{endpoints.authLogin}</code>
            </span>
          </div>
          <div>
            <strong>Session restore</strong>
            <span>
              <code>{endpoints.authMe}</code>
            </span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What stays true after sign-in</p>
          <h3>Protected routes still use one consistent auth boundary</h3>
          <ul className="portal-list">
            <li>
              Requested protected routes are remembered and restored after a
              successful sign-in.
            </li>
            <li>
              Session identity comes from the backend. Organization onboarding
              only appears after authentication when no organization context
              exists yet.
            </li>
            <li>
              Google and Microsoft sign-in remain visible, but they are not yet
              available in this phase.
            </li>
          </ul>
        </div>
      </div>

      <form
        className="portal-auth-page__card portal-form"
        noValidate
        onSubmit={handleSubmit}
      >
        <div className="portal-auth-page__card-copy">
          <p className="portal-shell__eyebrow">Welcome back</p>
          <h3>Sign in</h3>
          <p>Use your work email and password to access the portal.</p>
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
          <p
            aria-live="polite"
            className="portal-auth-page__error"
            role="alert"
          >
            {validationMessage}
          </p>
        ) : null}

        <div className="portal-form__actions">
          <button
            className="portal-shell__action portal-shell__action--primary"
            disabled={isBusy}
            type="submit"
          >
            {isBusy ? "Signing in..." : "Sign in"}
          </button>
          <a
            className="portal-shell__action portal-shell__action--secondary"
            href="#/register"
          >
            Create account
          </a>
        </div>

        <div className="portal-auth-page__divider" role="presentation">
          <span>Identity providers</span>
        </div>

        <div className="portal-auth-page__oauth">
          <button
            aria-disabled="true"
            className="portal-auth-page__oauth-button portal-auth-page__oauth-button--google"
            disabled
            type="button"
          >
            <span aria-hidden="true" className="portal-auth-page__oauth-mark">
              G
            </span>
            Google available soon
          </button>

          <button
            aria-disabled="true"
            className="portal-auth-page__oauth-button portal-auth-page__oauth-button--microsoft"
            disabled
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
            Microsoft available soon
          </button>
        </div>

        <div className="portal-auth-page__utility-links">
          <a href="#/">Portal home</a>
          <a href="#/register">Need an account?</a>
          <a href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20password%20help">
            Forgot password
          </a>
          <a href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20help">
            Help
          </a>
        </div>
      </form>
    </div>
  );
}
