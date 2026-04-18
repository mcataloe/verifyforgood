import { Panel } from "@charity-status/shared-ui";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import {
  usePortalUsageBilling,
  type PortalUsageBillingController,
} from "../billing/usePortalUsageBilling";
import {
  DetailPageLayout,
  PortalPageShell,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { BudgetConfigurationPanel } from "../settings/BudgetConfigurationPanel";
import { OrganizationProfileSettingsPanel } from "../settings/OrganizationProfileSettingsPanel";
import { OrganizationDeletionPanel } from "../settings/OrganizationDeletionPanel";
import {
  usePortalBudgetSettings,
  type PortalBudgetSettingsController,
} from "../settings/usePortalBudgetSettings";
import {
  usePortalOrganizationProfileSettings,
  type PortalOrganizationProfileSettingsController,
} from "../settings/usePortalOrganizationProfileSettings";
import {
  usePortalOrganizationDeletion,
  type PortalOrganizationDeletionController,
} from "../settings/usePortalOrganizationDeletion";

interface SettingsPageProps {
  budgetController?: PortalBudgetSettingsController;
  deletionController?: PortalOrganizationDeletionController;
  endpoints: PortalEndpoints;
  organizationProfileController?: PortalOrganizationProfileSettingsController;
  pane?: CustomerAdminPortalPane | null;
  session: PortalAuthenticatedSession;
  usageController?: PortalUsageBillingController;
}

export function SettingsPage({
  budgetController,
  deletionController,
  endpoints: _endpoints,
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
  const defaultDeletionController = usePortalOrganizationDeletion();
  const deletion = deletionController ?? defaultDeletionController;
  const organization = usePortalOrganization();

  return (
    <PortalPageShell
      description="Manage your organization profile, plan access, and usage controls."
      eyebrow={pane === "settings" ? "Customer admin settings" : "Portal settings"}
      title="Workspace settings"
    >
      <DetailPageLayout>
        <SectionBlock>
          <Panel
            title="Organization Profile"
            subtitle="Update the display name, slug, and contact details your team sees."
          >
            <OrganizationProfileSettingsPanel controller={organizationProfile} />
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
                <dd>{formatLabelValue(organization.currentMembership?.role)}</dd>
              </div>
              <div>
                <dt>Plan</dt>
                <dd>{formatLabelValue(session.plan)}</dd>
              </div>
              <div>
                <dt>Last updated</dt>
                <dd>
                  {formatFriendlyDateTime(
                    organization.activeOrganization.updated_at,
                  )}
                </dd>
              </div>
            </dl>
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Usage budget controls"
            subtitle="Set an optional organization request cap and decide whether requests stop when that threshold is reached."
          >
            <BudgetConfigurationPanel
              controller={budget}
              includedPlanLimit={
                usage.snapshot?.includedLimits?.monthlyRequests ??
                usage.snapshot?.usage.limit ??
                null
              }
            />
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Delete organization"
            subtitle="Remove this organization from the portal when it is no longer needed."
          >
            <OrganizationDeletionPanel
              controller={deletion}
              session={session}
            />
          </Panel>
        </SectionBlock>
      </DetailPageLayout>
    </PortalPageShell>
  );
}

function formatLabelValue(value: string | null | undefined): string {
  const candidate = String(value ?? "").trim();
  if (!candidate) {
    return "Unknown";
  }

  return candidate
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1).toLowerCase())
    .join(" ");
}

function formatFriendlyDateTime(value: string | null | undefined): string {
  const candidate = String(value ?? "").trim();
  if (!candidate) {
    return "Not recorded";
  }

  const parsed = Date.parse(candidate);
  if (Number.isNaN(parsed)) {
    return candidate;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(parsed));
}
