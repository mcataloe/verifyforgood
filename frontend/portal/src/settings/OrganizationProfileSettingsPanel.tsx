import { Group, Stack, Text, TextInput } from "@mantine/core";
import { useEffect, useState, type ReactNode } from "react";
import { InfoTooltip } from "../components/InfoTooltip";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import { normalizeSlugCandidate } from "../lib/slug";
import type { PortalOrganizationProfileSettingsController } from "./usePortalOrganizationProfileSettings";

function LabeledFieldWithTooltip({
  children,
  htmlFor,
  label,
  tooltip,
}: {
  children: ReactNode;
  htmlFor: string;
  label: string;
  tooltip: string;
}) {
  return (
    <Stack gap={4}>
      <Group gap={4}>
        <Text component="label" fw={500} htmlFor={htmlFor} size="sm">
          {label}
        </Text>
        <InfoTooltip label={tooltip} />
      </Group>
      {children}
    </Stack>
  );
}

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
      <LabeledFieldWithTooltip
        htmlFor="organization-display-name"
        label="Display name"
        tooltip="The customer-facing name shown throughout the portal and in emails to your team."
      >
        <TextInput
          id="organization-display-name"
          onBlur={() => setTouched(true)}
          onChange={(event) => {
            controller.clearNotice();
            setDisplayName(event.target.value);
          }}
          placeholder="VerifyForGood"
          value={displayName}
        />
      </LabeledFieldWithTooltip>

      <LabeledFieldWithTooltip
        htmlFor="organization-slug"
        label="Slug"
        tooltip="A stable, URL-safe identifier for this organization. Use lowercase letters, numbers, and single hyphens only."
      >
        <TextInput
          id="organization-slug"
          onBlur={() => setTouched(true)}
          onChange={(event) => {
            controller.clearNotice();
            setSlug(normalizeSlugCandidate(event.target.value));
          }}
          placeholder="verify-for-good"
          value={slug}
        />
      </LabeledFieldWithTooltip>

      <LabeledFieldWithTooltip
        htmlFor="organization-contact-email"
        label="Contact email"
        tooltip="Where early administrative notices about this organization are sent. Leave blank to clear it."
      >
        <TextInput
          id="organization-contact-email"
          onBlur={() => setTouched(true)}
          onChange={(event) => {
            controller.clearNotice();
            setContactEmail(event.target.value);
          }}
          placeholder="ops@example.org"
          type="email"
          value={contactEmail}
        />
      </LabeledFieldWithTooltip>

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
