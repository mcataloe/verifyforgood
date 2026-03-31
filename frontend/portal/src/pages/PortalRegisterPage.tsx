import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalRegisterRequest } from "../auth/portalAuthClient";

interface PortalRegisterPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onRegister: (request: PortalRegisterRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalRegisterPage({
  endpoints,
  isBusy,
  onRegister,
  requestedRoute,
}: PortalRegisterPageProps) {
  const fullNameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      setValidationMessage("Enter an email and password to create your account.");
      return;
    }

    setValidationMessage(null);

    try {
      await onRegister({
        email,
        full_name: fullName.trim() || undefined,
        password,
      });
    } catch (error) {
      setValidationMessage(
        error instanceof Error ? error.message : "Registration failed.",
      );
    }
  };

  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <p className="portal-shell__eyebrow">Create access</p>
          <h2>Start your portal account</h2>
          <p>
            Register to continue to {requestedRoute.label}. Account creation
            uses <code>{endpoints.authRegister}</code>, then restores the
            authenticated browser session through <code>{endpoints.authMe}</code>.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Requested area</strong>
            <span>{requestedRoute.label}</span>
          </div>
          <div>
            <strong>Register endpoint</strong>
            <span>
              <code>{endpoints.authRegister}</code>
            </span>
          </div>
          <div>
            <strong>Login route</strong>
            <span>
              <code>#/sign-in</code>
            </span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What happens next</p>
          <h3>Create identity now, finish organization setup later</h3>
          <ul className="portal-list">
            <li>
              Registration creates the authenticated user only in this phase.
            </li>
            <li>
              After registration, the portal checks for organization context and
              only then shows explicit onboarding if none exists.
            </li>
            <li>
              Google and Microsoft registration stay visible as disabled
              placeholders until provider support exists.
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
          <p className="portal-shell__eyebrow">New to VerifyForGood</p>
          <h3>Create account</h3>
          <p>Use your work identity to establish the first browser session.</p>
        </div>

        <label className="portal-form__field" htmlFor={fullNameId}>
          <span>Full name</span>
          <input
            autoComplete="name"
            className="portal-form__input"
            id={fullNameId}
            name="full_name"
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Alex Operator"
            type="text"
            value={fullName}
          />
        </label>

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
            autoComplete="new-password"
            className="portal-form__input"
            id={passwordId}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Choose a password"
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
            {isBusy ? "Creating account..." : "Create account"}
          </button>
          <a
            className="portal-shell__action portal-shell__action--secondary"
            href="#/sign-in"
          >
            Back to sign in
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
      </form>
    </div>
  );
}
