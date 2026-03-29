import { Grid, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import {
  usePortalUsageBilling,
  type PortalUsageBillingController,
} from "../billing/usePortalUsageBilling";
import {
  PortalErrorState,
  PortalLoadingState,
} from "../components/feedback";
import {
  PortalActionToolbar,
  PortalPageShell,
} from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { AppearancePreferenceSection } from "../settings/AppearancePreferenceSection";
import { BudgetConfigurationPanel } from "../settings/BudgetConfigurationPanel";
import { BudgetLimitVisualization } from "../settings/BudgetLimitVisualization";
import { OrganizationProfileSettingsPanel } from "../settings/OrganizationProfileSettingsPanel";
import { ProfileContextSection } from "../settings/ProfileContextSection";
import {
  usePortalBudgetSettings,
  type PortalBudgetSettingsController,
} from "../settings/usePortalBudgetSettings";
import {
  usePortalOrganizationProfileSettings,
  type PortalOrganizationProfileSettingsController,
} from "../settings/usePortalOrganizationProfileSettings";

interface SettingsPageProps {
  budgetController?: PortalBudgetSettingsController;
  endpoints: PortalEndpoints;
  organizationProfileController?: PortalOrganizationProfileSettingsController;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
  usageController?: PortalUsageBillingController;
}

export function SettingsPage({
  budgetController,
  endpoints,
  organizationProfileController,
  pane,
  session,
  usageController,
}: SettingsPageProps) {
  const defaultBudgetController = usePortalBudgetSettings();
  const budget = budgetController ?? defaultBudgetController;
  const defaultOrganizationProfileController =
    usePortalOrganizationProfileSettings();
  const organizationProfile =
    organizationProfileController ?? defaultOrganizationProfileController;
  const defaultUsageController = usePortalUsageBilling(session);
  const usage = usageController ?? defaultUsageController;
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description="Review the current portal identity, appearance defaults, and organization budget controls from one shared settings surface."
      eyebrow={pane === "settings" ? "Customer admin settings" : "Portal settings"}
      title="Workspace settings"
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              Org {organization.activeOrganization.organization_name}
            </span>
            <span className="portal-shell__summary-pill">
              Role {organization.currentMembership?.role ?? "unknown"}
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <Grid className="portal-page-grid">
        <Panel
          title="Organization Profile"
          subtitle="Editable organization metadata for the active customer-admin workspace."
        >
          <OrganizationProfileSettingsPanel controller={organizationProfile} />
        </Panel>

        <Panel
          title="Organization Details"
          subtitle="Stable identifiers and read-only organization context for the active workspace."
        >
          <dl className="portal-shell__details">
            <div>
              <dt>Display name</dt>
              <dd>{organization.activeOrganization.organization_name}</dd>
            </div>
            <div>
              <dt>Slug</dt>
              <dd>{organization.activeOrganization.slug ?? "Not assigned"}</dd>
            </div>
            <div>
              <dt>Organization</dt>
              <dd>
                {organization.activeOrganization.organization_id ??
                  organization.activeOrganization.workspace_id}
              </dd>
            </div>
            <div>
              <dt>Account</dt>
              <dd>{organization.activeOrganization.account_id}</dd>
            </div>
            <div>
              <dt>Workspace</dt>
              <dd>{organization.activeOrganization.workspace_id}</dd>
            </div>
            <div>
              <dt>Contact email</dt>
              <dd>
                {organization.activeOrganization.contact_email ??
                  "No contact email configured"}
              </dd>
            </div>
          </dl>
        </Panel>

        <Panel
          title="Administrative Metadata"
          subtitle="Read-only metadata intended for early customer administration and support handoff."
        >
          <dl className="portal-shell__details">
            <div>
              <dt>Settings source</dt>
              <dd>{organization.activeOrganization.settings_source}</dd>
            </div>
            <div>
              <dt>Settings updated</dt>
              <dd>{organization.activeOrganization.updated_at ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Organization created</dt>
              <dd>{organization.activeOrganization.created_at ?? "Not recorded"}</dd>
            </div>
            <div>
              <dt>Organization updated</dt>
              <dd>
                {organization.activeOrganization.organization_updated_at ??
                  "Not recorded"}
              </dd>
            </div>
            <div>
              <dt>Current role</dt>
              <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
            </div>
            <div>
              <dt>Current plan</dt>
              <dd>{session.plan}</dd>
            </div>
          </dl>
        </Panel>

        <Panel
          title="Usage budget controls"
          subtitle="Persisted through the existing organization settings contract."
        >
          <BudgetConfigurationPanel controller={budget} />
        </Panel>

        {usage.isLoading ? (
          <PortalLoadingState
            subtitle="Current usage relative to the configured monthly limit."
            title="Loading limit visualization"
          >
            <p>Loading current usage against the active plan.</p>
          </PortalLoadingState>
        ) : usage.error ? (
          <PortalErrorState
            actionLabel="Retry limit view"
            message={usage.error}
            onAction={() => {
              void usage.reload();
            }}
            subtitle="Current usage relative to the configured monthly limit."
            title="Limit visualization unavailable"
          />
        ) : (
          <Panel
            title="Limit visualization"
            subtitle="Current usage relative to the configured monthly limit."
          >
            <BudgetLimitVisualization
              allowOverage={budget.settings.allowOverage}
              configuredLimit={budget.settings.monthlyRequestCap}
              snapshot={usage.snapshot}
            />
          </Panel>
        )}

        <Panel
          title="Profile & preferences"
          subtitle="User identity, account context, and local appearance preferences for the current portal session."
        >
          <div className="portal-settings-page__profile-stack">
            <ProfileContextSection
              organization={organization.activeOrganization}
              session={session}
            />
            <AppearancePreferenceSection />
          </div>
        </Panel>

        <Panel
          title="Current backend anchor"
          subtitle="Organization profile and budget controls remain explicit about persistence and compatibility."
        >
          <p>
            Organization settings load from and persist to{" "}
            <code>{endpoints.organizationSettings}</code>.
          </p>
          <ul className="portal-list">
            <li>
              Display name and contact email live in the current organization
              settings contract.
            </li>
            <li>Monthly usage caps are still stored per account.</li>
            <li>Slug remains visible but read-only in this phase.</li>
          </ul>
        </Panel>
      </Grid>
    </PortalPageShell>
  );
}
