import { getPortalAccessLabel } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganizationContextValue } from "../organization/usePortalOrganization";

interface ProfileContextSectionProps {
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
        <p className="portal-settings-profile__name">{session.user.display_name}</p>
        <p>{session.user.email}</p>
      </div>

      <dl className="portal-settings-profile__details">
        <div>
          <dt>Organization</dt>
          <dd>{organization.organization_name}</dd>
        </div>
        <div>
          <dt>Account</dt>
          <dd>{organization.account_id}</dd>
        </div>
        <div>
          <dt>Workspace</dt>
          <dd>{organization.workspace_id}</dd>
        </div>
        <div>
          <dt>Access</dt>
          <dd>{getPortalAccessLabel(session.roles)}</dd>
        </div>
        <div>
          <dt>Plan</dt>
          <dd>{session.plan}</dd>
        </div>
        <div>
          <dt>Auth mode</dt>
          <dd>{session.auth_method.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Subject</dt>
          <dd>{session.user.subject_id}</dd>
        </div>
      </dl>
    </section>
  );
}
