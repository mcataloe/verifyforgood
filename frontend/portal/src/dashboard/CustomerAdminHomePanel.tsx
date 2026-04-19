import { DataTable, SectionContainer, type DataTableColumn } from "@charity-status/shared-ui";
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
    sortable: true,
    sortValue: (row) => row.occurred_at,
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
      <PortalNotice title="Activity Visibility Unavailable" tone="empty">
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
        title="Loading Activity"
      >
        <p>Fetching recent API, membership, invitation, settings, and nonprofit access activity.</p>
      </PortalLoadingState>
    );
  }

  if (activity.error && activity.items.length === 0) {
    return (
      <PortalErrorState
        actionLabel="Retry"
        message={activity.error}
        onAction={() => {
          void activity.reload();
        }}
        subtitle="The portal could not load recent organization activity."
        title="Activity Unavailable"
      />
    );
  }

  return (
    <div className="portal-dashboard__activity-grid">
      <SectionContainer
        title="Organization Activity"
        description={`Recent activity, access changes, and important updates for ${organization.activeOrganization.organization_name}.`}
      >
        {activity.error ? (
          <PortalNotice tone="warning">
            <p>{activity.error}</p>
          </PortalNotice>
        ) : null}

        {activity.items.length === 0 ? (
          <PortalEmptyState
            subtitle="Activity appears here once the organization starts inviting teammates, managing keys, updating settings, or accessing nonprofit data."
            title="No Organization Activity Yet"
          >
            <p>The current organization does not have any visible audit activity yet.</p>
          </PortalEmptyState>
        ) : (
          <>
            <DataTable
              columns={activityColumns}
              getSearchText={(row) =>
                [
                  row.title,
                  row.description,
                  row.actor.display_name,
                  row.actor.email,
                  row.target.display_name,
                  row.target.email,
                  row.target.user_id,
                ]
                  .filter(Boolean)
                  .join(" ")
              }
              initialSort={{ columnKey: "occurred_at", direction: "desc" }}
              pageSize={10}
              rowKey={(row) => row.activity_id}
              rows={activity.items}
              searchPlaceholder="Search activity"
            />
            {activity.hasMore ? (
              <div className="portal-form__actions">
                <Button
                  loading={activity.isLoadingMore}
                  onClick={() => {
                    void activity.loadMore();
                  }}
                  variant="default"
                >
                  Load More
                </Button>
              </div>
            ) : null}
          </>
        )}
      </SectionContainer>
    </div>
  );
}

function formatDateTime(value: string) {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  return new Date(parsed).toLocaleString();
}
