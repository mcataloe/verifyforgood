import {
  Card,
  DataTable,
  SectionContainer,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import { Button } from "@mantine/core";
import {
  PortalEmptyState,
  PortalErrorState,
  PortalLoadingState,
  PortalNotice,
} from "../components/feedback";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import { usePortalActivity } from "./usePortalActivity";
import type { PortalOrganizationActivityItem } from "./portalActivity";

const activityColumns: DataTableColumn<PortalOrganizationActivityItem>[] = [
  {
    key: "title",
    header: "Activity",
    render: (row) => (
      <div>
        <strong>{row.title}</strong>
        <div>{row.description}</div>
      </div>
    ),
  },
  {
    key: "actor",
    header: "Actor",
    render: (row) =>
      row.actor.display_name ?? row.actor.email ?? row.actor.user_id ?? "System",
  },
  {
    key: "target",
    header: "Target",
    render: (row) =>
      row.target.display_name ?? row.target.email ?? row.target.user_id ?? "Organization",
  },
  {
    key: "occurred_at",
    header: "Occurred",
    render: (row) => formatDateTime(row.occurred_at),
  },
];

export function CustomerAdminHomePanel() {
  const organization = usePortalOrganization();
  const canViewActivity =
    organization.currentMembership?.role === "admin" &&
    organization.currentMembership?.status === "active";
  const activity = usePortalActivity({ enabled: canViewActivity });

  if (!canViewActivity) {
    return (
      <PortalNotice title="Activity visibility unavailable" tone="empty">
        <p>
          Organization activity is visible only to active organization admins.
        </p>
      </PortalNotice>
    );
  }

  if (activity.isLoading) {
    return (
      <PortalLoadingState
        subtitle="Loading recent organization activity."
        title="Loading activity"
      >
        <p>Fetching recent API, membership, invitation, settings, and nonprofit access activity.</p>
      </PortalLoadingState>
    );
  }

  if (activity.error && activity.items.length === 0) {
    return (
      <PortalErrorState
        actionLabel="Retry activity"
        message={activity.error}
        onAction={() => {
          void activity.reload();
        }}
        subtitle="The portal could not load recent organization activity."
        title="Activity unavailable"
      />
    );
  }

  return (
    <div className="portal-dashboard__activity-grid">
      <SectionContainer
        title="Recent organization activity"
        description="Newest-first activity across API keys, team changes, organization settings, invitations, and nonprofit access."
      >
        {activity.error ? (
          <PortalNotice tone="warning">
            <p>{activity.error}</p>
          </PortalNotice>
        ) : null}

        {activity.items.length === 0 ? (
          <PortalEmptyState
            subtitle="Activity appears here once the organization starts inviting teammates, managing keys, updating settings, or accessing nonprofit data."
            title="No organization activity yet"
          >
            <p>The current organization does not have any visible audit activity yet.</p>
          </PortalEmptyState>
        ) : (
          <>
            <DataTable columns={activityColumns} rows={activity.items} />
            {activity.hasMore ? (
              <div className="portal-form__actions">
                <Button
                  loading={activity.isLoadingMore}
                  onClick={() => {
                    void activity.loadMore();
                  }}
                  variant="default"
                >
                  Load more activity
                </Button>
              </div>
            ) : null}
          </>
        )}
      </SectionContainer>

      <SectionContainer
        title="Activity categories"
        description="The current phase focuses on readable, sanitized organization events."
      >
        <div className="portal-dashboard__metrics">
          <SummaryCard label="Organization" value={organization.activeOrganization.organization_name} />
          <SummaryCard label="Role" value={organization.currentMembership?.role ?? "unknown"} />
          <SummaryCard label="Scope" value={organization.activeOrganization.organization_id ?? organization.activeOrganization.account_id} />
          <SummaryCard label="Feed order" value="Newest first" />
        </div>
      </SectionContainer>
    </div>
  );
}

function SummaryCard(input: { label: string; value: string }) {
  return (
    <Card title={input.label} withBorder>
      <strong>{input.value}</strong>
    </Card>
  );
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}
