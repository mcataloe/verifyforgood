import { Modal } from "@mantine/core";
import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
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
        slug: slug.trim() || undefined,
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
      title="Create your first organization"
    >
      <div data-testid="organization-onboarding-page">
        <div className="portal-auth-page__card-copy">
          <p>
            Create your organization to start managing your team, billing, and
            verification work.
          </p>
        </div>

        <form
          className="portal-form portal-form--detail"
          noValidate
          onSubmit={handleSubmit}
        >
          <label className="portal-form__field" htmlFor={nameId}>
            <span>Organization name</span>
            <input
              autoFocus
              className="portal-form__input"
              id={nameId}
              name="name"
              onChange={(event) => setName(event.target.value)}
              placeholder="Verify For Good Org"
              type="text"
              value={name}
            />
          </label>

          <label className="portal-form__field" htmlFor={slugId}>
            <span>Slug</span>
            <input
              className="portal-form__input"
              id={slugId}
              name="slug"
              onChange={(event) => setSlug(event.target.value)}
              placeholder="verify-for-good-org"
              type="text"
              value={slug}
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
              {isBusy ? "Creating organization..." : "Create organization"}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}
