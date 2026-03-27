import { Grid, OnboardingLayout, Panel } from "@charity-status/shared-ui";
import { useId, useState, type FormEvent } from "react";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalOrganizationCreateRequest } from "../organization/portalOrganization";

interface PortalOrganizationOnboardingPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onCreateOrganization: (
    request: PortalOrganizationCreateRequest,
  ) => Promise<unknown>;
}

export function PortalOrganizationOnboardingPage({
  endpoints,
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
    <Grid className="portal-page-grid">
      <OnboardingLayout
        steps={[
          {
            key: "create-org",
            label: "Create organization",
            status: "current",
            description:
              "Create the first organization context so the portal can attach your workspace, account, and future memberships.",
          },
          {
            key: "verification",
            label: "Go to dashboard",
            status: "upcoming",
            description:
              "After organization setup, the portal will send you to the dashboard to start the first workflow.",
          },
          {
            key: "invite",
            label: "Invite teammates",
            status: "upcoming",
            description:
              "Future team onboarding will build on this organization context instead of page-local assumptions.",
          },
        ]}
        subtitle="Create your first organization now. Future phases can support switching between multiple organizations."
        title="Organization setup"
      />

      <Panel
        title="Organization bootstrap"
        subtitle="This activates the global organization context for the portal."
      >
        <form className="portal-form" noValidate onSubmit={handleSubmit}>
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
            <p aria-live="polite" className="portal-auth-page__error" role="alert">
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

      <Panel
        title="Backend contract"
        subtitle="The onboarding flow already has a stable organization bootstrap API."
      >
        <p>
          This screen uses <code>{endpoints.organizationCreate}</code> and
          promotes the resulting account and workspace identifiers into the
          global portal organization context.
        </p>
      </Panel>
    </Grid>
  );
}
