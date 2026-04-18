import { useEffect, useState } from "react";
import { normalizeSlugCandidate } from "../lib/slug";
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
  const [slug, setSlug] = useState(controller.settings.slug ?? "");

  useEffect(() => {
    setDisplayName(controller.settings.displayName);
    setContactEmail(controller.settings.contactEmail);
    setSlug(controller.settings.slug ?? "");
  }, [
    controller.settings.contactEmail,
    controller.settings.displayName,
    controller.settings.slug,
  ]);

  const trimmedDisplayName = displayName.trim();
  const trimmedContactEmail = contactEmail.trim();
  const trimmedSlug = normalizeSlugCandidate(slug);
  const isDirty =
    trimmedDisplayName !== controller.settings.displayName ||
    trimmedContactEmail !== controller.settings.contactEmail.trim() ||
    trimmedSlug !== (controller.settings.slug ?? "").trim().toLowerCase();
  const validationMessage = getValidationMessage({
    contactEmail: trimmedContactEmail,
    displayName: trimmedDisplayName,
    slug: trimmedSlug,
  });
  const isSaveDisabled =
    controller.isLoading ||
    controller.isSaving ||
    validationMessage !== null ||
    !isDirty;

  return (
    <div className="portal-budget-form">
      <form className="portal-form portal-form--detail">
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

        <label className="portal-form__field" htmlFor="organization-slug">
          <span>Slug</span>
          <input
            className="portal-form__input"
            id="organization-slug"
            onChange={(event) => {
              controller.clearNotice();
              setSlug(normalizeSlugCandidate(event.target.value));
            }}
            placeholder="verify-for-good"
            type="text"
            value={slug}
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
        Keep the organization display name customer-facing, use the slug for
        stable workspace identification, and use the contact email for early
        administrative notices. Leave the contact email blank to clear it.
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
          disabled={isSaveDisabled}
          onClick={() => {
            if (!isDirty || validationMessage !== null) {
              return;
            }

            void controller.save({
              contactEmail: trimmedContactEmail,
              displayName: trimmedDisplayName,
              slug: trimmedSlug,
            });
          }}
          type="button"
        >
          {controller.isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  );
}

function getValidationMessage(input: {
  contactEmail: string;
  displayName: string;
  slug: string;
}): string | null {
  if (input.displayName.length < 2) {
    return "Display name must be at least 2 characters.";
  }
  if (input.slug.length < 2) {
    return "Slug must be at least 2 characters.";
  }
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(input.slug)) {
    return "Slug may contain lowercase letters, numbers, and single hyphens only.";
  }
  if (
    input.contactEmail &&
    !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.contactEmail)
  ) {
    return "Contact email must be a valid email address.";
  }
  return null;
}
