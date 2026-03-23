import { getPortalAccessLabel } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganizationContextValue } from "../organization/usePortalOrganization";

interface ProfileContextSectionProps {
  organization: PortalOrganizationContextValue["activeOrganization"];
  session: PortalAuthenticatedSession;
}

/**
 * Compact identity and account context for the current authenticated portal
 * user. This keeps shell footer content minimal while making account metadata
 * available on the settings/profile surface.
 */
export function ProfileContextSection({
  organization,
  session,
}: ProfileContextSectionProps) {
  return (
    <section className="portal-settings-profile" aria-labelledby="profile-context-title">
      <div className="portal-settings-profile__hero">
        <p className="portal-shell__eyebrow">Current profile</p>
        <h3 id="profile-context-title">{session.user.display_name}</h3>
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
