import { Modal, Stack, Text, TextInput } from "@mantine/core";
import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import { normalizeSlugCandidate } from "../lib/slug";
import type { PortalOrganizationCreateRequest } from "../organization/portalOrganization";

interface PortalOrganizationOnboardingPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onClose: () => void;
  onCreateOrganization: (
    request: PortalOrganizationCreateRequest,
  ) => Promise<unknown>;
}

export function PortalOrganizationOnboardingPage({
  endpoints: _endpoints,
  isBusy,
  onClose,
  onCreateOrganization,
}: PortalOrganizationOnboardingPageProps) {
  const nameId = useId();
  const slugId = useId();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!name.trim()) {
      setValidationMessage("Enter an organization name to continue.");
      return;
    }

    setValidationMessage(null);

    try {
      await onCreateOrganization({
        name,
        slug: normalizeSlugCandidate(slug) || undefined,
      });
    } catch (error) {
      setValidationMessage(
        error instanceof Error
          ? error.message
          : "Organization creation failed.",
      );
    }
  };

  return (
    <Modal
      closeButtonProps={{
        "aria-label": "Close organization setup",
        disabled: isBusy,
      }}
      onClose={onClose}
      opened
      styles={{
        title: { fontSize: "var(--mantine-font-size-xl)", fontWeight: 700 },
      }}
      title="Create Your Organization"
    >
      <div data-testid="organization-onboarding-page">
        <Stack gap="lg">
          <Text c="dimmed" lh={1.6} size="md">
            Create your organization to start managing your team, billing, and
            verification work.
          </Text>

          <form noValidate onSubmit={handleSubmit}>
            <Stack gap="md">
              <TextInput
                autoFocus
                id={nameId}
                label="Organization name"
                name="name"
                onChange={(event) => {
                  const nextName = event.target.value;
                  const previousAutoSlug = normalizeSlugCandidate(name);
                  const nextAutoSlug = normalizeSlugCandidate(nextName);

                  setName(nextName);
                  setSlug((currentSlug) =>
                    !currentSlug || currentSlug === previousAutoSlug
                      ? nextAutoSlug
                      : currentSlug,
                  );
                }}
                placeholder="Verify For Good Org"
                value={name}
              />

              <TextInput
                id={slugId}
                label="Slug"
                name="slug"
                onChange={(event) => {
                  setSlug(normalizeSlugCandidate(event.target.value));
                }}
                placeholder="verify-for-good-org"
                value={slug}
              />

              <PortalHint>
                The slug is generated from the organization name and can be
                adjusted before creation.
              </PortalHint>

              {validationMessage ? (
                <PortalNotice tone="error">
                  <p>{validationMessage}</p>
                </PortalNotice>
              ) : null}

              <PortalActionGroup>
                <PortalButton loading={isBusy} tone="primary" type="submit">
                  {isBusy ? "Creating..." : "Create Organization"}
                </PortalButton>
              </PortalActionGroup>
            </Stack>
          </form>
        </Stack>
      </div>
    </Modal>
  );
}
