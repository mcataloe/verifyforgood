import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalLoginRequest } from "../auth/portalAuthClient";
import { usePortalToast } from "../components/feedback";

interface PortalSignInPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onLogin: (request: PortalLoginRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalSignInPage({
  endpoints: _endpoints,
  isBusy,
  onLogin,
  requestedRoute,
}: PortalSignInPageProps) {
  const emailId = useId();
  const passwordId = useId();
  const { dismissToast, showToast } = usePortalToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      showToast({
        id: "portal-sign-in",
        message: "Enter both email and password to continue.",
        title: "Sign-in details required",
        tone: "warning",
      });
      return;
    }

    dismissToast("portal-sign-in");

    try {
      await onLogin({
        email,
        password,
      });
    } catch (error) {
      showToast({
        id: "portal-sign-in",
        message: error instanceof Error ? error.message : "Sign-in failed.",
        title: "Unable to sign in",
        tone: "error",
      });
    }
  };

  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <h2>Secure Access for Verification Operations</h2>
          <p>
            Sign in to continue to {requestedRoute.label}. Use your work email
            and password to access your organization dashboard, billing, team
            access, and verification tools.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Requested area</strong>
            <span>{requestedRoute.label}</span>
          </div>
          <div>
            <strong>Account access</strong>
            <span>Secure sign-in for your organization workspace</span>
          </div>
          <div>
            <strong>Need an organization?</strong>
            <span>You can create one after signing in if your account is new.</span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <h3>We&apos;ll Take You There</h3>
          <ul className="portal-list">
            <li>
              If you requested a specific area, we&apos;ll return you there after
              sign-in.
            </li>
            <li>
              If your account does not belong to an organization yet, you&apos;ll
              be guided through organization setup next.
            </li>
            <li>
              Help is available if you need support accessing your account.
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
          <h3>Sign In</h3>
          <p>Use your work email and password to access the portal.</p>
        </div>

        <label className="portal-form__field" htmlFor={emailId}>
          <span>Email</span>
          <input
            autoComplete="email"
            className="portal-form__input"
            id={emailId}
            name="email"
            onChange={(event) => {
              dismissToast("portal-sign-in");
              setEmail(event.target.value);
            }}
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
            onChange={(event) => {
              dismissToast("portal-sign-in");
              setPassword(event.target.value);
            }}
            placeholder="Enter your password"
            type="password"
            value={password}
          />
        </label>

        <div className="portal-form__actions">
          <button
            className="portal-shell__action portal-shell__action--primary"
            disabled={isBusy}
            type="submit"
          >
            {isBusy ? "Signing..." : "Sign In"}
          </button>
          <a
            className="portal-shell__action portal-shell__action--secondary"
            href="#/register"
          >
            Create Account
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
