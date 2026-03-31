import { getPortalAccessLabel } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganizationContextValue } from "../organization/usePortalOrganization";
import { DetailFieldList } from "@charity-status/shared-ui";

interface ProfileContextSectionProps {
  environment?: string;
  organization: PortalOrganizationContextValue["activeOrganization"];
  session: PortalAuthenticatedSession;
  showTitle?: boolean;
}

/**
 * Compact identity and account context for the current authenticated portal
 * user. This keeps shell footer content minimal while making account metadata
 * available on the settings/profile surface.
 */
export function ProfileContextSection({
  environment: _environment,
  organization,
  session,
  showTitle = true,
}: ProfileContextSectionProps) {
  return (
    <section
      aria-labelledby={showTitle ? "profile-context-title" : undefined}
      className="portal-settings-profile"
    >
      {showTitle ? <h3 id="profile-context-title">Account context</h3> : null}
      <div className="portal-settings-profile__summary">
        <p className="portal-shell__eyebrow">Current profile</p>
        <p className="portal-settings-profile__name">
          {session.user.display_name}
        </p>
        <p>{session.user.email}</p>
      </div>

      <DetailFieldList
        items={[
          {
            key: "organization",
            label: "Organization",
            value: organization.organization_name,
          },
          {
            key: "access",
            label: "Access",
            value: getPortalAccessLabel(session.roles),
          },
          {
            key: "plan",
            label: "Plan",
            value: session.plan,
          },
        ]}
      />
    </section>
  );
}
