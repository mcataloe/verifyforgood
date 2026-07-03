import { Stack, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
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
  const [touched, setTouched] = useState(false);

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
    <Stack gap="md">
      <TextInput
        id="organization-display-name"
        label="Display name"
        onBlur={() => setTouched(true)}
        onChange={(event) => {
          controller.clearNotice();
          setDisplayName(event.target.value);
        }}
        placeholder="VerifyForGood"
        value={displayName}
      />

      <TextInput
        id="organization-slug"
        label="Slug"
        onBlur={() => setTouched(true)}
        onChange={(event) => {
          controller.clearNotice();
          setSlug(normalizeSlugCandidate(event.target.value));
        }}
        placeholder="verify-for-good"
        value={slug}
      />

      <TextInput
        id="organization-contact-email"
        label="Contact email"
        onBlur={() => setTouched(true)}
        onChange={(event) => {
          controller.clearNotice();
          setContactEmail(event.target.value);
        }}
        placeholder="ops@example.org"
        type="email"
        value={contactEmail}
      />

      <PortalHint>
        Keep the organization display name customer-facing, use the slug for
        stable workspace identification, and use the contact email for early
        administrative notices. Leave the contact email blank to clear it.
      </PortalHint>

      {touched && validationMessage ? (
        <PortalNotice tone="error">
          <p>{validationMessage}</p>
        </PortalNotice>
      ) : null}

      {controller.error ? (
        <PortalNotice tone="error">
          <p>{controller.error}</p>
        </PortalNotice>
      ) : null}

      {controller.notice ? (
        <PortalNotice tone="warning">
          <p>{controller.notice}</p>
        </PortalNotice>
      ) : null}

      <PortalActionGroup>
        <PortalButton
          disabled={isSaveDisabled}
          loading={controller.isSaving}
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
          tone="primary"
          type="button"
        >
          {controller.isSaving ? "Saving..." : "Save Changes"}
        </PortalButton>
      </PortalActionGroup>
    </Stack>
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
