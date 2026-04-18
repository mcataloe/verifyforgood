import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalRegisterRequest } from "../auth/portalAuthClient";
import { usePortalToast } from "../components/feedback";

interface PortalRegisterPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onRegister: (request: PortalRegisterRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalRegisterPage({
  endpoints: _endpoints,
  isBusy,
  onRegister,
  requestedRoute,
}: PortalRegisterPageProps) {
  const fullNameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const { dismissToast, showToast } = usePortalToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      showToast({
        id: "portal-register",
        message: "Enter an email and password to create your account.",
        title: "Account details required",
        tone: "warning",
      });
      return;
    }

    dismissToast("portal-register");

    try {
      await onRegister({
        email,
        full_name: fullName.trim() || undefined,
        password,
      });
    } catch (error) {
      showToast({
        id: "portal-register",
        message: error instanceof Error ? error.message : "Registration failed.",
        title: "Unable to create account",
        tone: "error",
      });
    }
  };

  return (
    <div className="portal-auth-page">
      <div className="portal-auth-page__intro">
        <div className="portal-auth-page__copy">
          <p className="portal-shell__eyebrow">Create access</p>
          <h2>Start your portal account</h2>
          <p>
            Create an account to continue to {requestedRoute.label}. Once your
            account is ready, you can sign in and finish setting up your
            organization if needed.
          </p>
        </div>

        <div className="portal-auth-page__trust-band">
          <div>
            <strong>Requested area</strong>
            <span>{requestedRoute.label}</span>
          </div>
          <div>
            <strong>Account setup</strong>
            <span>Create your login for the customer portal</span>
          </div>
          <div>
            <strong>Next step</strong>
            <span>After sign-up, you can create or join an organization.</span>
          </div>
        </div>

        <div className="portal-auth-page__onboarding">
          <p className="portal-shell__eyebrow">What happens next</p>
          <h3>Create your account first</h3>
          <ul className="portal-list">
            <li>Create your account with your work details.</li>
            <li>
              After sign-in, we’ll check whether you already belong to an
              organization.
            </li>
            <li>
              If you do not, you can create one in a dedicated setup step.
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
          <p>Use your work email to create your portal login.</p>
        </div>

        <label className="portal-form__field" htmlFor={fullNameId}>
          <span>Full name</span>
          <input
            autoComplete="name"
            className="portal-form__input"
            id={fullNameId}
            name="full_name"
            onChange={(event) => {
              dismissToast("portal-register");
              setFullName(event.target.value);
            }}
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
            onChange={(event) => {
              dismissToast("portal-register");
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
            autoComplete="new-password"
            className="portal-form__input"
            id={passwordId}
            name="password"
            onChange={(event) => {
              dismissToast("portal-register");
              setPassword(event.target.value);
            }}
            placeholder="Choose a password"
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
