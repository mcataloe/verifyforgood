import { useEffect, useState } from "react";
import type { PortalOrganizationProfileSettingsController } from "./usePortalOrganizationProfileSettings";

interface OrganizationProfileSettingsPanelProps {
  controller: PortalOrganizationProfileSettingsController;
}

export function OrganizationProfileSettingsPanel({
  controller,
}: OrganizationProfileSettingsPanelProps) {
  const [displayName, setDisplayName] = useState(
    controller.settings.displayName,
  );
  const [contactEmail, setContactEmail] = useState(
    controller.settings.contactEmail,
  );

  useEffect(() => {
    setDisplayName(controller.settings.displayName);
    setContactEmail(controller.settings.contactEmail);
  }, [controller.settings.contactEmail, controller.settings.displayName]);

  const trimmedDisplayName = displayName.trim();
  const trimmedContactEmail = contactEmail.trim();
  const isDirty =
    trimmedDisplayName !== controller.settings.displayName ||
    trimmedContactEmail !== controller.settings.contactEmail.trim();
  const validationMessage = getValidationMessage({
    contactEmail: trimmedContactEmail,
    displayName: trimmedDisplayName,
  });

  return (
    <div className="portal-budget-form">
      <form className="portal-form portal-form--two-column">
        <label className="portal-form__field" htmlFor="organization-display-name">
          <span>Display name</span>
          <input
            className="portal-form__input"
            id="organization-display-name"
            onChange={(event) => {
              controller.clearNotice();
              setDisplayName(event.target.value);
            }}
            placeholder="VerifyForGood"
            type="text"
            value={displayName}
          />
        </label>

        <label className="portal-form__field" htmlFor="organization-contact-email">
          <span>Contact email</span>
          <input
            className="portal-form__input"
            id="organization-contact-email"
            onChange={(event) => {
              controller.clearNotice();
              setContactEmail(event.target.value);
            }}
            placeholder="ops@example.org"
            type="email"
            value={contactEmail}
          />
        </label>
      </form>

      <p className="portal-budget-form__hint">
        Keep the organization display name customer-facing and use the contact
        email for early administrative notices. Leave the contact email blank to
        clear it.
      </p>

      {validationMessage ? (
        <p className="portal-feedback portal-feedback--error">
          {validationMessage}
        </p>
      ) : null}

      {controller.error ? (
        <p className="portal-feedback portal-feedback--error">
          {controller.error}
        </p>
      ) : null}

      {controller.notice ? (
        <p className="portal-feedback portal-feedback--warning">
          {controller.notice}
        </p>
      ) : null}

      <div className="portal-form__actions">
        <button
          className="portal-shell__action portal-shell__action--primary"
          disabled={
            controller.isLoading ||
            controller.isSaving ||
            !isDirty ||
            validationMessage !== null
          }
          onClick={() =>
            void controller.save({
              contactEmail: trimmedContactEmail,
              displayName: trimmedDisplayName,
            })
          }
          type="button"
        >
          {controller.isSaving
            ? "Saving organization profile..."
            : "Save organization profile"}
        </button>
      </div>
    </div>
  );
}

function getValidationMessage(input: {
  contactEmail: string;
  displayName: string;
}): string | null {
  if (input.displayName.length < 2) {
    return "Display name must be at least 2 characters.";
  }
  if (
    input.contactEmail &&
    !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.contactEmail)
  ) {
    return "Contact email must be a valid email address.";
  }
  return null;
}
