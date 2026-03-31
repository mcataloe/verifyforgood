import { Panel } from "@charity-status/shared-ui";
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
  DetailPageLayout,
  PortalActionToolbar,
  PortalPageShell,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { AppearancePreferenceSection } from "../settings/AppearancePreferenceSection";
import { BudgetConfigurationPanel } from "../settings/BudgetConfigurationPanel";
import { BudgetLimitVisualization } from "../settings/BudgetLimitVisualization";
import { OrganizationProfileSettingsPanel } from "../settings/OrganizationProfileSettingsPanel";
import { ProfileContextSection } from "../settings/ProfileContextSection";
import { SupportHelpPanel } from "../settings/SupportHelpPanel";
import {
  usePortalBudgetSettings,
  type PortalBudgetSettingsController,
} from "../settings/usePortalBudgetSettings";
import {
  usePortalOrganizationProfileSettings,
  type PortalOrganizationProfileSettingsController,
} from "../settings/usePortalOrganizationProfileSettings";
import {
  usePortalSupport,
  type PortalSupportController,
} from "../settings/usePortalSupport";

interface SettingsPageProps {
  budgetController?: PortalBudgetSettingsController;
  endpoints: PortalEndpoints;
  organizationProfileController?: PortalOrganizationProfileSettingsController;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
  supportController?: PortalSupportController;
  usageController?: PortalUsageBillingController;
}

export function SettingsPage({
  budgetController,
  endpoints: _endpoints,
  organizationProfileController,
  pane,
  session,
  supportController,
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
  const defaultSupportController = usePortalSupport();
  const support = supportController ?? defaultSupportController;
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description="Manage your organization profile, usage controls, appearance preferences, and support settings."
      eyebrow={pane === "settings" ? "Customer admin settings" : "Portal settings"}
      title="Workspace settings"
      toolbar={
        <PortalActionToolbar>
          <div className="portal-action-toolbar__group">
            <span className="portal-shell__summary-pill">
              {organization.activeOrganization.organization_name}
            </span>
            <span className="portal-shell__summary-pill">
              {session.plan} plan
            </span>
          </div>
        </PortalActionToolbar>
      }
    >
      <DetailPageLayout>
        <SectionBlock>
          <Panel
            title="Organization Profile"
            subtitle="Update the name and contact details your team sees."
          >
            <OrganizationProfileSettingsPanel controller={organizationProfile} />
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Organization details"
            subtitle="Key information about your organization."
          >
            <dl className="portal-shell__details">
              <div>
                <dt>Display name</dt>
                <dd>{organization.activeOrganization.organization_name}</dd>
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
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Plan & access"
            subtitle="A quick summary of your current plan and access level."
          >
            <dl className="portal-shell__details">
              <div>
                <dt>Your role</dt>
                <dd>{organization.currentMembership?.role ?? "unknown"}</dd>
              </div>
              <div>
                <dt>Plan</dt>
                <dd>{session.plan}</dd>
              </div>
              <div>
                <dt>Last updated</dt>
                <dd>{organization.activeOrganization.updated_at ?? "Not recorded"}</dd>
              </div>
            </dl>
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Usage budget controls"
            subtitle="Set request limits and decide how usage should be handled at the threshold."
          >
            <BudgetConfigurationPanel controller={budget} />
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
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
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <ProfileContextSection
            organization={organization.activeOrganization}
            session={session}
          />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <AppearancePreferenceSection />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Support & Help"
            subtitle="Get help, review support information, and contact our team."
          >
            <SupportHelpPanel controller={support} />
          </Panel>
        </SectionBlock>
      </DetailPageLayout>
    </PortalPageShell>
  );
}
