import { useMemo, useState } from "react";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  PortalDetailSection,
  PortalDetailView,
} from "../components/PortalDetailView";
import { AppearancePreferenceSection } from "../settings/AppearancePreferenceSection";
import { ProfileContextSection } from "../settings/ProfileContextSection";

interface CustomerUserProfilePageProps {
  environment: string;
  session: PortalAuthenticatedSession;
}

export function CustomerUserProfilePage({
  environment: _environment,
  session,
}: CustomerUserProfilePageProps) {
  const organization = usePortalOrganization();
  const [firstName, setFirstName] = useState(
    splitDisplayName(session.user.display_name).firstName,
  );
  const [lastName, setLastName] = useState(
    splitDisplayName(session.user.display_name).lastName,
  );
  const [email, setEmail] = useState(session.user.email);
  const [pronouns, setPronouns] = useState("Prefer not to say");
  const [avatarName, setAvatarName] = useState<string | null>(null);
  const initials = useMemo(
    () =>
      `${firstName[0] ?? ""}${lastName[0] ?? ""}`.trim().toUpperCase() || "VF",
    [firstName, lastName],
  );

  return (
    <PortalDetailView
      eyebrow="Profile"
      intro="Manage your profile details and appearance preferences."
      title="Profile"
    >
      <PortalDetailSection
        intro="Update the personal details shown in your profile."
        title="Personal information"
      >
        <form className="portal-form portal-form--detail">
          <label className="portal-form__field">
            <span>First Name</span>
            <input
              aria-label="First Name"
              className="portal-form__input"
              onChange={(event) => {
                setFirstName(event.target.value);
              }}
              type="text"
              value={firstName}
            />
          </label>

          <label className="portal-form__field">
            <span>Last Name</span>
            <input
              aria-label="Last Name"
              className="portal-form__input"
              onChange={(event) => {
                setLastName(event.target.value);
              }}
              type="text"
              value={lastName}
            />
          </label>

          <label className="portal-form__field">
            <span>Email</span>
            <input
              aria-label="Email"
              className="portal-form__input"
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              type="email"
              value={email}
            />
          </label>

          <label className="portal-form__field">
            <span>Pronouns</span>
            <select
              aria-label="Pronouns"
              className="portal-form__input"
              onChange={(event) => {
                setPronouns(event.target.value);
              }}
              value={pronouns}
            >
              <option>Prefer not to say</option>
              <option>She / her</option>
              <option>He / him</option>
              <option>They / them</option>
              <option>Custom / ask me</option>
            </select>
          </label>
        </form>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Choose the image you want to use for your profile."
        title="Avatar"
      >
        <div className="portal-profile-page__avatar-panel">
          <div aria-hidden="true" className="portal-profile-page__avatar">
            {initials}
          </div>
          <div className="portal-profile-page__avatar-content">
            <label className="portal-form__field">
              <span>Avatar upload</span>
              <input
                aria-label="Avatar upload"
                className="portal-form__input"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  setAvatarName(file?.name ?? null);
                }}
                type="file"
              />
            </label>
            <p className="portal-settings-preferences__note">
              {avatarName ? `Selected file: ${avatarName}` : "No file selected"}
            </p>
          </div>
        </div>
      </PortalDetailSection>

      <PortalDetailSection
        intro="Review the organization and plan connected to your account."
        title="Account details"
      >
        <ProfileContextSection
          organization={organization.activeOrganization}
          session={session}
          showTitle={false}
        />
      </PortalDetailSection>

      <PortalDetailSection
        intro="Choose the appearance that feels best for you."
        title="Appearance"
      >
        <AppearancePreferenceSection showTitle={false} />
      </PortalDetailSection>
    </PortalDetailView>
  );
}

function splitDisplayName(displayName: string) {
  const [firstName = "", ...rest] = displayName.trim().split(/\s+/);

  return {
    firstName,
    lastName: rest.join(" "),
  };
}
