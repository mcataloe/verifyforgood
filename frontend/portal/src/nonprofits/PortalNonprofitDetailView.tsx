import {
  DetailFieldList,
  StatusBadge,
} from "@charity-status/shared-ui";
import { Group, List, Stack, Table, Text, Title } from "@mantine/core";
import {
  DetailPageLayout,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
import { PortalButton } from "../components/PortalPrimitives";
import type {
  PortalNonprofitDetail,
  PortalNonprofitSourceAvailability,
  PortalNonprofitSearchSummary,
} from "./nonprofitSearch";
import type { StatusBadgeStatus } from "@charity-status/shared-ui";

interface PortalNonprofitDetailViewProps {
  detail: PortalNonprofitDetail;
}

export function PortalNonprofitDetailView({
  detail,
}: PortalNonprofitDetailViewProps) {
  return (
    <DetailPageLayout
      header={
        <Stack gap="sm">
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
            Review the latest organization details, filings, and source checks.
          </Text>
          <Text c="dimmed" fw={600}>
            EIN {detail.ein}
          </Text>
        </Stack>
      }
    >
      <SectionBlock title="Summary">
        <DetailFieldList items={buildSummaryItems(detail)} />
      </SectionBlock>
      <SectionDivider />
      <SectionBlock title="Overview">
        <DetailFieldList items={buildOverviewItems(detail)} />
      </SectionBlock>
      <SectionDivider />
      <SectionBlock title="Filings">
        <DetailFieldList items={buildFilingsItems(detail)} />
      </SectionBlock>
      <SectionDivider />
      <SectionBlock title="Compliance">
        <DetailFieldList items={buildComplianceItems(detail)} />
      </SectionBlock>
      <SectionDivider />
      <SectionBlock title="Data sources">
        <PortalNonprofitSourceSection detail={detail} />
      </SectionBlock>
      <SectionDivider />
      <SectionBlock title="Activity">
        <ActivityList />
      </SectionBlock>
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
        <DetailFieldList items={buildSummaryItems(detail)} />
      </Stack>

      <Stack gap="md">
        <SectionBlock title="Overview">
          <DetailFieldList items={buildOverviewItems(detail)} />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock title="Filings">
          <DetailFieldList items={buildFilingsItems(detail)} />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock title="Compliance">
          <DetailFieldList items={buildComplianceItems(detail)} />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock title="Sources">
          <PortalNonprofitSourceSection detail={detail} />
        </SectionBlock>
        <SectionDivider />
        <SectionBlock title="Activity">
          <ActivityList />
        </SectionBlock>
      </Stack>
    </Stack>
  );
}

function ActivityList() {
  return (
    <List spacing="xs">
      <List.Item>Initial review completed for this organization.</List.Item>
      <List.Item>Recent filing information is available in this record.</List.Item>
      <List.Item>
        Additional activity will appear here as more updates are recorded.
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
      key: "risk",
      label: "Risk indicators",
      value: summarizeRisk(detail),
      detail: detail.filingParseStatus,
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
    },
  ];
}

function buildComplianceItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "irs-status",
      label: "IRS status",
      value: detail.irsStatus,
    },
    {
      key: "recent-990",
      label: "Recent 990 on file",
      value: detail.recent990OnFile,
    },
    {
      key: "parse-status",
      label: "Parse status",
      value: detail.filingParseStatus,
    },
    {
      key: "tax-period",
      label: "Tax period",
      value: detail.taxPeriod,
    },
  ];
}

function buildSourceItems(detail: PortalNonprofitDetail) {
  return [
    {
      key: "source-checks",
      label: "Source checks",
      value: String(detail.sourceAvailability.length),
    },
  ];
}

function PortalNonprofitSourceSection({
  detail,
}: {
  detail: PortalNonprofitDetail;
}) {
  return (
    <>
      <DetailFieldList items={buildSourceItems(detail)} />
      {detail.sourceAvailability.length > 0 ? (
        <Table highlightOnHover withColumnBorders withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Source</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Attempted</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {detail.sourceAvailability.map((source) => (
              <Table.Tr key={source.integrationId}>
                <Table.Td>{source.label}</Table.Td>
                <Table.Td>{formatSourceStatus(source)}</Table.Td>
                <Table.Td>{source.attempted ? "Yes" : "No"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed">
          No source checks are available for this organization yet.
        </Text>
      )}
    </>
  );
}

function formatSourceStatus(source: PortalNonprofitSourceAvailability) {
  switch (source.status) {
    case "tenant_disabled":
      return "Not enabled for your organization";
    case "matched":
      return "Matched";
    case "no_match":
      return "No match found";
    case "missing_credentials":
      return "Provider unavailable";
    case "failed":
      return "Request failed";
    case "not_offered":
      return "Not offered";
    default:
      return source.status.replaceAll("_", " ");
  }
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

function summarizeRisk(detail: PortalNonprofitDetail) {
  const risks: string[] = [];

  if (detail.filingParseStatus.toLowerCase() !== "parsed") {
    risks.push("Parsing needs review");
  }

  if (detail.recent990OnFile.toLowerCase() !== "true") {
    risks.push("Recent 990 unavailable");
  }

  return risks.length ? risks.join(" | ") : "No immediate flags";
}
