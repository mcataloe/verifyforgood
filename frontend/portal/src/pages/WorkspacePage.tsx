import { Grid, OnboardingLayout, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { TeamManagementPanel } from "../organization/TeamManagementPanel";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface WorkspacePageProps {
  endpoints: PortalEndpoints;
  session: PortalAuthenticatedSession;
}

export function WorkspacePage({ endpoints, session }: WorkspacePageProps) {
  const organization = usePortalOrganization();

  return (
    <Grid className="portal-page-grid">
      <OnboardingLayout
        steps={[
          {
            key: "welcome",
            label: "Welcome",
            status: "complete",
            description:
              "Your organization context is active and ready for the first product workflow.",
            action: (
              <button className="portal-shell__action" type="button">
                Review workspace scope
              </button>
            ),
          },
          {
            key: "verification",
            label: "Create first verification",
            status: "current",
            description:
              "Run the first EIN or organization-name search to establish the review workflow for your team.",
          },
          {
            key: "api-key",
            label: "Generate API key",
            status: "upcoming",
            description:
              "Create a key only when you are ready to connect internal systems or automate checks.",
          },
          {
            key: "invite",
            label: "Invite team member",
            status: "upcoming",
            description:
              "Add teammates after ownership and review responsibilities are clear.",
          },
        ]}
        subtitle="A calm first-run checklist for new portal customers."
        title="Workspace onboarding"
      />

      <Panel
        title="Workspace context"
        subtitle="Ready for tenant, account, and membership-aware slices."
      >
        <p>
          The portal now carries an active organization context that future
          slices can access through a shared provider instead of re-deriving
          tenant scope from page-local props.
        </p>
        <dl className="portal-shell__details">
          <div>
            <dt>Organization</dt>
            <dd>{organization.activeOrganization.organization_name}</dd>
          </div>
          <div>
            <dt>Workspace ID</dt>
            <dd>{organization.activeOrganization.workspace_id}</dd>
          </div>
          <div>
            <dt>Account ID</dt>
            <dd>{organization.activeOrganization.account_id}</dd>
          </div>
          <div>
            <dt>Settings source</dt>
            <dd>{organization.activeOrganization.settings_source}</dd>
          </div>
        </dl>
      </Panel>

      <Panel
        title="Current backend anchor"
        subtitle="Settings are already keyed to workspace/account context."
      >
        <p>
          Future organization management slices should align to the existing
          settings contract at <code>{endpoints.organizationSettings}</code>.
        </p>
        <ul className="portal-list">
          <li>
            Active scope status: <strong>{organization.status}</strong>.
          </li>
          <li>
            Billing overage allowed:{" "}
            <strong>
              {organization.activeOrganization.billing_allow_overage === null
                ? "not loaded"
                : String(organization.activeOrganization.billing_allow_overage)}
            </strong>
            .
          </li>
          <li>Integration toggles are workspace-aware.</li>
          <li>Billing overage preferences are account-wide.</li>
          <li>
            Defaults remain backward compatible when nothing has been persisted.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Signed-in operator"
        subtitle="Session identity stays separate from the active organization boundary."
      >
        <dl className="portal-shell__details">
          <div>
            <dt>User</dt>
            <dd>{session.user.display_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{session.user.email}</dd>
          </div>
          <div>
            <dt>Scope source</dt>
            <dd>{organization.activeOrganization.scope_source}</dd>
          </div>
        </dl>
      </Panel>

      <TeamManagementPanel />
    </Grid>
  );
}
