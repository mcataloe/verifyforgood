import { DetailFieldList, StatusBadge } from "@charity-status/shared-ui";
import {
  Anchor,
  Breadcrumbs,
  Group,
  List,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import {
  DetailPageLayout,
  SectionBlock,
} from "../components/shell";
import { PortalButton } from "../components/PortalPrimitives";
import type {
  PortalNonprofitDetail,
  PortalNonprofitSearchSummary,
  PortalNonprofitSourceSummary,
} from "./nonprofitSearch";
import type { StatusBadgeStatus } from "@charity-status/shared-ui";

interface PortalNonprofitDetailViewProps {
  detail: PortalNonprofitDetail;
  onBackToSearch?: () => void;
}

export function PortalNonprofitDetailView({
  detail,
  onBackToSearch,
}: PortalNonprofitDetailViewProps) {
  return (
    <DetailPageLayout
      header={
        <Stack gap="sm">
          <Breadcrumbs>
            {onBackToSearch ? (
              <Anchor
                component="button"
                onClick={onBackToSearch}
                size="sm"
                type="button"
              >
                Search results
              </Anchor>
            ) : (
              <Text c="dimmed" size="sm">
                Nonprofit Search
              </Text>
            )}
            <Text c="dimmed" size="sm">
              {detail.name}
            </Text>
          </Breadcrumbs>
          <Group align="center" gap="sm" justify="space-between" wrap="wrap">
            <Group align="center" gap="sm" wrap="wrap">
              <Title order={1}>{detail.name}</Title>
              <StatusBadge status={detailStatus(detail)} />
            </Group>
            <PortalButton onClick={() => undefined} tone="secondary" type="button">
              Queue review
            </PortalButton>
          </Group>
          <Text c="dimmed">
            Review nonprofit facts, signals, and data gaps before deciding how
            to proceed.
          </Text>
          <Text c="dimmed" fw={600}>
            EIN {detail.ein}
          </Text>
        </Stack>
      }
    >
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" verticalSpacing="xl">
        <SectionBlock title="Summary">
          <Stack gap="lg">
            <DetailFieldList items={buildSummaryItems(detail)} />
            <SignalList
              emptyText="No summary explanation is available yet."
              items={detail.appearsBecause}
              title="Appears because"
            />
            <SignalList
              emptyText="No standout highlights are recorded yet."
              items={detail.highlights}
              title="Highlights"
            />
            <SignalList
              emptyText="No immediate risk indicators are recorded."
              items={detail.riskIndicators}
              title="Risk indicators"
            />
            <SignalList
              emptyText="No material data gaps are recorded."
              items={detail.dataGaps}
              title="Data gaps"
            />
          </Stack>
        </SectionBlock>
        <SectionBlock title="Overview">
          <DetailFieldList items={buildOverviewItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Filings">
          <DetailFieldList items={buildFilingsItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Data sources">
          <PortalNonprofitSourceSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Compliance">
          <DetailFieldList items={buildComplianceItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Activity">
          <ActivityList detail={detail} />
        </SectionBlock>
      </SimpleGrid>
    </DetailPageLayout>
  );
}

export function PortalNonprofitEmbeddedDetail({
  detail,
}: PortalNonprofitDetailViewProps) {
  return (
    <Stack component="article" gap="md">
      <Stack gap="md">
        <Group align="center" gap="sm" wrap="wrap">
          <Title order={3}>{detail.name}</Title>
          <StatusBadge status={detailStatus(detail)} />
        </Group>
        <Text c="dimmed" fw={600}>
          EIN {detail.ein}
        </Text>
      </Stack>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl" verticalSpacing="xl">
        <SectionBlock title="Summary">
          <DetailFieldList items={buildSummaryItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Overview">
          <DetailFieldList items={buildOverviewItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Filings">
          <DetailFieldList items={buildFilingsItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Data sources">
          <PortalNonprofitSourceSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Compliance">
          <DetailFieldList items={buildComplianceItems(detail)} />
        </SectionBlock>
        <SectionBlock title="Activity">
          <ActivityList detail={detail} />
        </SectionBlock>
      </SimpleGrid>
    </Stack>
  );
}

function SignalList({
  emptyText,
  items,
  title,
}: {
  emptyText: string;
  items: string[];
  title: string;
}) {
  return (
    <Stack gap="xs">
      <Text c="dimmed" fw={700} fz="xs" tt="uppercase">
        {title}
      </Text>
      {items.length > 0 ? (
        <List spacing="xs">
          {items.map((item) => (
            <List.Item key={`${title}-${item}`}>{item}</List.Item>
          ))}
        </List>
      ) : (
        <Text c="dimmed">{emptyText}</Text>
      )}
    </Stack>
  );
}

function ActivityList({ detail }: { detail: PortalNonprofitDetail }) {
  return (
    <List spacing="xs">
      <List.Item>
        Advisory detail snapshot refreshed at {detail.snapshotMaterializedAt}.
      </List.Item>
      <List.Item>
        Filing history currently includes {detail.filingsCount} known filing
        {detail.filingsCount === 1 ? "" : "s"}.
      </List.Item>
      <List.Item>
        {detail.sourceSummaries.length > 0
          ? `${detail.sourceSummaries.length} source summaries are available for follow-up review.`
          : "Additional source summaries will appear here as more checks are recorded."}
      </List.Item>
    </List>
  );
}

function buildSummaryItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "irs",
      label: "IRS status",
      value: detail.irsStatus,
    },
    {
      key: "filing",
      label: "Most recent filing year",
      value: detail.filingTaxYear,
      detail: detail.filingDate,
    },
    {
      key: "classification",
      label: "Classification",
      value: detail.nteeCategory,
      detail: detail.entityType,
    },
    {
      key: "snapshot",
      label: "Snapshot refreshed",
      value: detail.snapshotMaterializedAt,
      detail: detail.modelVersion,
    },
  ];
}

function buildOverviewItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "entity-type",
      label: "Entity type",
      value: detail.entityType,
    },
    {
      key: "state",
      label: "State",
      value: detail.state,
    },
    {
      key: "subsection",
      label: "Subsection",
      value: detail.subsection,
    },
    {
      key: "tax-deductible",
      label: "Tax deductible",
      value: detail.taxDeductible,
    },
  ];
}

function buildFilingsItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "filing-form",
      label: "Filing form",
      value: detail.filingFormType,
    },
    {
      key: "filing-year",
      label: "Filing year",
      value: detail.filingTaxYear,
    },
    {
      key: "filing-date",
      label: "Filing date",
      value: detail.filingDate,
    },
    {
      key: "filings-count",
      label: "Known filings",
      value: String(detail.filingsCount),
      detail: `Recent 990 on file: ${detail.recent990OnFile}`,
    },
  ];
}

function buildComplianceItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "compliance-status",
      label: "Latest status",
      value: detail.complianceStatus,
    },
    {
      key: "check-type",
      label: "Check type",
      value: detail.complianceCheckType,
    },
    {
      key: "checked-at",
      label: "Checked at",
      value: detail.complianceCheckedAt,
    },
    {
      key: "tax-period",
      label: "Tax period",
      value: detail.taxPeriod,
    },
  ];
}

function PortalNonprofitSourceSection({
  detail,
}: {
  detail: PortalNonprofitDetail;
}) {
  return detail.sourceSummaries.length > 0 ? (
    <Table highlightOnHover withColumnBorders withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Source</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Retrieved</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {detail.sourceSummaries.map((source) => (
          <Table.Tr key={source.sourceName}>
            <Table.Td>
              <Stack gap={2}>
                <Text fw={500}>{source.providerName}</Text>
                <Text c="dimmed" fz="sm">
                  {source.category}
                </Text>
              </Stack>
            </Table.Td>
            <Table.Td>
              <Stack gap={2}>
                <Text>{formatSourceStatus(source)}</Text>
                <Text c="dimmed" fz="sm">
                  {source.explanation}
                </Text>
              </Stack>
            </Table.Td>
            <Table.Td>{source.retrievedAt}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  ) : (
    <Text c="dimmed">
      No source summaries are available for this organization yet.
    </Text>
  );
}

function formatSourceStatus(source: PortalNonprofitSourceSummary) {
  return source.status.replaceAll("_", " ");
}

export function summaryStatus(
  row: PortalNonprofitSearchSummary,
): StatusBadgeStatus {
  if (
    row.active === false ||
    row.irsStatus.toLowerCase().includes("inactive")
  ) {
    return "inactive";
  }

  if (row.active === true || row.irsStatus.toLowerCase().includes("active")) {
    return "verified";
  }

  return "pending";
}

export function detailStatus(detail: PortalNonprofitDetail): StatusBadgeStatus {
  if (detail.irsStatus.toLowerCase().includes("inactive")) {
    return "inactive";
  }

  if (
    detail.riskIndicators.length > 0 ||
    detail.filingParseStatus.toLowerCase() !== "parsed" ||
    detail.recent990OnFile.toLowerCase() !== "true"
  ) {
    return "flagged";
  }

  if (detail.irsStatus.toLowerCase().includes("active")) {
    return "verified";
  }

  return "pending";
}
