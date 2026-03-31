import { Panel } from "@charity-status/shared-ui";
import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import {
  DetailPageLayout,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import type { PortalOrganizationCreateRequest } from "../organization/portalOrganization";

interface PortalOrganizationOnboardingPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onCreateOrganization: (
    request: PortalOrganizationCreateRequest,
  ) => Promise<unknown>;
}

export function PortalOrganizationOnboardingPage({
  endpoints: _endpoints,
  isBusy,
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
    <DetailPageLayout
      data-testid="organization-onboarding-page"
      eyebrow="Onboarding"
      intro="Create your organization to start managing your team, billing, and verification work."
      testId="organization-onboarding-page"
      title="Create your first organization"
    >
      <SectionBlock
        intro="A few quick steps will get your organization ready."
        title="Getting started"
      >
        <ol className="portal-list">
          <li>Create your organization profile.</li>
          <li>We'll take you to the dashboard when setup is complete.</li>
          <li>You can invite teammates after your organization is ready.</li>
        </ol>
      </SectionBlock>
      <SectionDivider />
      <SectionBlock>
        <Panel
          title="Create organization"
          subtitle="Enter the basic details for your organization."
        >
          <form
            className="portal-form portal-form--detail"
            noValidate
            onSubmit={handleSubmit}
          >
            <label className="portal-form__field" htmlFor={nameId}>
              <span>Organization name</span>
              <input
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
        </Panel>
      </SectionBlock>
      <SectionDivider />
      <SectionBlock>
        <Panel
          title="What happens next"
          subtitle="After your organization is created, you can continue setting up your account."
        >
          <p>
            You'll go straight to the dashboard, where you can review activity,
            manage access, and continue setup.
          </p>
        </Panel>
      </SectionBlock>
    </DetailPageLayout>
  );
}
