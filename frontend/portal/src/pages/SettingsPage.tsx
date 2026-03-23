import { Grid, Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import {
  usePortalUsageBilling,
  type PortalUsageBillingController,
} from "../billing/usePortalUsageBilling";
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
  session: PortalAuthenticatedSession;
  usageController?: PortalUsageBillingController;
}

export function SettingsPage({
  budgetController,
  endpoints,
  session,
  usageController,
}: SettingsPageProps) {
  const defaultBudgetController = usePortalBudgetSettings();
  const budget = budgetController ?? defaultBudgetController;
  const defaultUsageController = usePortalUsageBilling(session);
  const usage = usageController ?? defaultUsageController;
  const organization = usePortalOrganization();

  return (
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

      <Panel
        title="Limit visualization"
        subtitle="Current usage relative to the configured monthly limit."
      >
        {usage.isLoading ? (
          <p>Loading current usage against the active plan.</p>
        ) : usage.error ? (
          <p className="portal-feedback portal-feedback--error">
            {usage.error}
          </p>
        ) : (
          <BudgetLimitVisualization
            allowOverage={budget.settings.allowOverage}
            configuredLimit={budget.settings.monthlyRequestCap}
            snapshot={usage.snapshot}
          />
        )}
      </Panel>

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
  );
}
