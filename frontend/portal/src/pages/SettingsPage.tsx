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
import { PortalDetailList } from "../components/PortalPrimitives";
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
  pane: _pane,
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
      title="Workspace Settings"
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
            title="Plan & Access"
            subtitle="A quick summary of your current plan and access level."
          >
            <PortalDetailList
              items={[
                {
                  key: "role",
                  label: "Your role",
                  value: formatLabelValue(organization.currentMembership?.role),
                },
                {
                  key: "plan",
                  label: "Plan",
                  value: formatLabelValue(session.plan),
                },
                {
                  key: "updated-at",
                  label: "Last updated",
                  value: formatFriendlyDateTime(
                    organization.activeOrganization.updated_at,
                  ),
                },
              ]}
            />
          </Panel>
        </SectionBlock>
        <SectionDivider />
        <SectionBlock>
          <Panel
            title="Usage Budget Controls"
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
            title="Delete Organization"
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
