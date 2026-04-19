import {
  Card,
  DataTable,
  PageHeader,
  SectionContainer,
  StatusBadge,
  VerifyForGoodMantineProvider,
  verifyForGoodTokens,
  type DataTableColumn,
  type StatusBadgeStatus,
} from "@charity-status/shared-ui";
import { Paper, SimpleGrid, Stack, Text } from "@mantine/core";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { CSSProperties } from "react";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { CustomerAdminHomePanel } from "../dashboard/CustomerAdminHomePanel";

interface DashboardPageProps {
  pane?: CustomerAdminPortalPane | null;
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

type MetricTone = "primary" | "secondary" | "success" | "warning";

type DashboardMetric = {
  detail: string;
  tone: MetricTone;
  title: string;
  value: string;
};

type VerificationRow = {
  organization: string;
  requestedAt: string;
  status: StatusBadgeStatus;
  type: string;
};

type DashboardAlert = {
  detail: string;
  status: StatusBadgeStatus;
  title: string;
};

type TrendPoint = {
  label: string;
  value: number;
};

const semantic = verifyForGoodTokens.color.semantic.light;
const palette = verifyForGoodTokens.color.palette;
const dashboardMetrics: DashboardMetric[] = [
  {
    title: "Verifications this month",
    value: "1,284",
    detail: "12% ahead of the previous monthly run rate.",
    tone: "primary",
  },
  {
    title: "Verified organizations",
    value: "942",
    detail: "73% of reviewed organizations cleared verification.",
    tone: "success",
  },
  {
    title: "Flagged organizations",
    value: "38",
    detail: "Requires analyst follow-up across high-risk records.",
    tone: "warning",
  },
  {
    title: "API calls",
    value: "84.6K",
    detail: "Total requests across your organization this month.",
    tone: "secondary",
  },
];
const verificationTrend: TrendPoint[] = [
  { label: "Oct", value: 44 },
  { label: "Nov", value: 58 },
  { label: "Dec", value: 52 },
  { label: "Jan", value: 71 },
  { label: "Feb", value: 76 },
  { label: "Mar", value: 88 },
];
const recentVerifications: VerificationRow[] = [
  {
    organization: "American National Red Cross",
    type: "Profile refresh",
    requestedAt: "Mar 22, 2026",
    status: "verified",
  },
  {
    organization: "Feeding America",
    type: "New verification",
    requestedAt: "Mar 22, 2026",
    status: "pending",
  },
  {
    organization: "Community Housing Partners",
    type: "Risk review",
    requestedAt: "Mar 21, 2026",
    status: "flagged",
  },
  {
    organization: "Regional Literacy Fund",
    type: "Monitoring sync",
    requestedAt: "Mar 21, 2026",
    status: "inactive",
  },
];
const dashboardAlerts: DashboardAlert[] = [
  {
    title: "Flag queue above target",
    detail: "Seven records have exceeded the 24-hour review SLA.",
    status: "flagged",
  },
  {
    title: "Nightly sync pending approval",
    detail: "Connection settings were updated and need review.",
    status: "pending",
  },
  {
    title: "Monitoring baseline confirmed",
    detail: "Automated checks resumed for the top 50 tracked organizations.",
    status: "verified",
  },
];
const recentVerificationColumns: DataTableColumn<VerificationRow>[] = [
  {
    key: "organization",
    header: "Organization",
    render: (row) => row.organization,
  },
  {
    key: "type",
    header: "Verification type",
    render: (row) => row.type,
  },
  {
    key: "requestedAt",
    header: "Requested",
    render: (row) => row.requestedAt,
    sortable: true,
    sortValue: (row) => row.requestedAt,
  },
  {
    key: "status",
    header: "Status",
    render: (row) => <StatusBadge status={row.status} />,
  },
];

const spacing = verifyForGoodTokens.spacing.scale;
const pageStyle: CSSProperties = {
  display: "grid",
  gap: spacing.lg,
  minWidth: 0,
};
const metricValueStyle: CSSProperties = {
  color: semantic.text_primary,
  fontFamily: verifyForGoodTokens.typography.fontFamily.sans,
  fontSize: verifyForGoodTokens.typography.fontSize["4xl"],
  fontWeight: verifyForGoodTokens.typography.fontWeight.bold,
  letterSpacing: verifyForGoodTokens.typography.letterSpacing.tight,
  lineHeight: verifyForGoodTokens.typography.lineHeight.tight,
  margin: 0,
};
const metricDetailStyle: CSSProperties = {
  color: semantic.text_secondary,
  fontSize: verifyForGoodTokens.typography.fontSize.sm,
  lineHeight: verifyForGoodTokens.typography.lineHeight.normal,
  margin: 0,
};
const alertListStyle: CSSProperties = {
  display: "grid",
  gap: spacing.sm,
};
const alertItemStyle: CSSProperties = {
  backgroundColor: semantic.surface_subtle,
  border: `1px solid ${semantic.border}`,
  borderRadius: verifyForGoodTokens.radius.card,
  padding: spacing.sm,
};

export function DashboardPage({
  pane,
  runtimeConfig,
  session,
}: DashboardPageProps) {
  const showHomePageHeader =
    session.organization_membership?.role !== "admin" ||
    session.organization_membership?.status !== "active";

  if (pane === "home") {
    return (
      <VerifyForGoodMantineProvider>
        <div
          className="portal-authenticated-container portal-dashboard"
          data-testid="portal-page-container"
          style={pageStyle}
        >
          {showHomePageHeader ? (
            <PageHeader
              title="Organization Activity"
              description={`Recent activity, access changes, and important updates for ${session.organization_name}.`}
            />
          ) : null}
          <CustomerAdminHomePanel />
        </div>
      </VerifyForGoodMantineProvider>
    );
  }

  return (
    <VerifyForGoodMantineProvider>
      <div
        className="portal-authenticated-container portal-dashboard"
        data-testid="portal-page-container"
        style={pageStyle}
      >
        <PageHeader
          title="Verification Dashboard"
          description={`Track verification activity, usage, and current priorities for ${session.organization_name}.`}
        />

        <SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }} data-testid="dashboard-metrics-grid" spacing="md">
          {dashboardMetrics.map((metric) => (
            <MetricCard key={metric.title} metric={metric} />
          ))}
        </SimpleGrid>

        <SimpleGrid
          className="portal-dashboard__content"
          cols={{ base: 1, lg: 2 }}
          data-testid="dashboard-content-layout"
          spacing="md"
        >
          <Stack className="portal-dashboard__main" data-testid="dashboard-main-column" gap="md">
            <SectionContainer
              title="Recent Verifications"
              description="Recent verification requests across your organization."
            >
              <DataTable
                columns={recentVerificationColumns}
                getSearchText={(row) =>
                  `${row.organization} ${row.type} ${row.requestedAt} ${row.status}`
                }
                initialSort={{ columnKey: "requestedAt", direction: "desc" }}
                pageSize={5}
                rows={recentVerifications}
                searchPlaceholder="Search verifications"
              />
            </SectionContainer>
          </Stack>

          <Stack className="portal-dashboard__sidebar" data-testid="dashboard-sidebar-column" gap="md">
            <SectionContainer
              title="Verification Trend"
              description="Monthly verification volume."
            >
              <TrendChartPlaceholder />
            </SectionContainer>

            <SectionContainer
              title="Alerts"
              description={`Important updates for your ${session.plan} plan.`}
            >
              <AlertsPanel />
            </SectionContainer>
          </Stack>
        </SimpleGrid>
      </div>
    </VerifyForGoodMantineProvider>
  );
}

function MetricCard({ metric }: { metric: DashboardMetric }) {
  const toneStyles = metricToneStyles[metric.tone];

  return (
    <Card
      description={metric.detail}
      style={{
        borderTop: `${verifyForGoodTokens.spacing.baseUnit / 2}px solid ${toneStyles.border}`,
        minWidth: 0,
      }}
      title={metric.title}
    >
      <div style={{ display: "grid", gap: spacing.sm }}>
        <p style={metricValueStyle}>{metric.value}</p>
        <div
          aria-hidden="true"
          style={{
            backgroundColor: toneStyles.track,
            borderRadius: verifyForGoodTokens.radius.button,
            height: `${verifyForGoodTokens.spacing.baseUnit}px`,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              backgroundColor: toneStyles.bar,
              borderRadius: verifyForGoodTokens.radius.button,
              height: "100%",
              width: toneStyles.width,
            }}
          />
        </div>
      </div>
    </Card>
  );
}

function TrendChartPlaceholder() {
  return (
    <Card
      description="Monthly verification activity."
      title="Monthly throughput"
      withBorder
    >
      <SimpleGrid
        aria-label="Verification trend chart"
        className="portal-dashboard__chart-placeholder"
        cols={verificationTrend.length}
        spacing="sm"
        role="img"
      >
        {verificationTrend.map((point) => (
          <Stack align="center" gap="xs" key={point.label}>
            <Paper
              aria-hidden="true"
              p="xs"
              radius="md"
              style={{
                background:
                  "linear-gradient(180deg, rgba(219, 234, 254, 0.45) 0%, rgba(219, 234, 254, 0.12) 100%)",
                minHeight: `${verifyForGoodTokens.spacing.baseUnit * 18}px`,
                width: "100%",
                display: "flex",
                alignItems: "end",
              }}
            >
              <div
                style={{
                  background:
                    "linear-gradient(180deg, #3277d6 0%, #197a83 100%)",
                  height: `${point.value}%`,
                  minHeight: `${verifyForGoodTokens.spacing.baseUnit * 2}px`,
                  width: "100%",
                  borderRadius: verifyForGoodTokens.radius.button,
                }}
              />
            </Paper>
            <Text
              c="dimmed"
              fw={500}
              size="xs"
              style={{
                textAlign: "center",
              }}
            >
              {point.label}
            </Text>
          </Stack>
        ))}
      </SimpleGrid>
    </Card>
  );
}

function AlertsPanel() {
  return (
    <Stack gap="sm" style={alertListStyle}>
      {dashboardAlerts.map((alert) => (
        <Paper
          key={alert.title}
          p="sm"
          radius="md"
          withBorder
          style={alertItemStyle}
        >
          <div
            style={{
              alignItems: "center",
              display: "flex",
              gap: spacing.sm,
              justifyContent: "space-between",
              marginBottom: spacing.xs,
            }}
          >
            <Text
              component="strong"
              style={{
                color: semantic.text_primary,
                fontSize: verifyForGoodTokens.typography.fontSize.sm,
              }}
            >
              {alert.title}
            </Text>
            <StatusBadge status={alert.status} />
          </div>
          <Text style={metricDetailStyle}>{alert.detail}</Text>
        </Paper>
      ))}
    </Stack>
  );
}

const metricToneStyles: Record<
  MetricTone,
  { bar: string; border: string; track: string; width: string }
> = {
  primary: {
    bar: palette.primary[500],
    border: palette.primary[500],
    track: palette.primary[100],
    width: "78%",
  },
  secondary: {
    bar: palette.secondary[500],
    border: palette.secondary[500],
    track: palette.secondary[100],
    width: "66%",
  },
  success: {
    bar: palette.success[500],
    border: palette.success[500],
    track: palette.success[100],
    width: "73%",
  },
  warning: {
    bar: palette.warning[500],
    border: palette.warning[500],
    track: palette.warning[100],
    width: "34%",
  },
};
