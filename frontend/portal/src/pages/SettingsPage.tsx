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
import { ProfileContextSection } from "../settings/ProfileContextSection";
import {
  usePortalBudgetSettings,
  type PortalBudgetSettingsController,
} from "../settings/usePortalBudgetSettings";

interface SettingsPageProps {
  budgetController?: PortalBudgetSettingsController;
  endpoints: PortalEndpoints;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
  usageController?: PortalUsageBillingController;
}

export function SettingsPage({
  budgetController,
  endpoints,
  pane,
  session,
  usageController,
}: SettingsPageProps) {
  const defaultBudgetController = usePortalBudgetSettings();
  const budget = budgetController ?? defaultBudgetController;
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
          title="Current backend anchor"
          subtitle="Budget controls and session-scoped settings remain explicit about persistence and consequences."
        >
          <p>
            Budget configuration loads from and persists to{" "}
            <code>{endpoints.organizationSettings}</code>.
          </p>
          <ul className="portal-list">
            <li>Monthly usage caps are stored per account.</li>
            <li>
              Hard-stop enforcement is backed by the existing billing overage
              setting.
            </li>
            <li>
              Workspace and account identifiers remain explicit in the shell.
            </li>
          </ul>
          <dl className="portal-shell__details">
            <div>
              <dt>Plan</dt>
              <dd>{session.plan}</dd>
            </div>
            <div>
              <dt>Current theme storage</dt>
              <dd>
                <code>verifyforgood-color-scheme</code>
              </dd>
            </div>
          </dl>
        </Panel>
      </Grid>
    </PortalPageShell>
  );
}
