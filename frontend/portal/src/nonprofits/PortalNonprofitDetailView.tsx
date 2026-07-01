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
import { DetailPageLayout, SectionBlock } from "../components/shell";
import { PortalButton } from "../components/PortalPrimitives";
import type {
  PortalNonprofitDetail,
  PortalReviewCheck,
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
              <StatusBadge
                label={`Evidence review: ${formatReviewStatus(
                  detail.review?.evidenceReview.status ?? "not_recorded",
                )}`}
                status={reviewBadgeStatus(
                  detail.review?.evidenceReview.status ?? "not_recorded",
                )}
              />
            </Group>
            <PortalButton
              onClick={() => undefined}
              tone="secondary"
              type="button"
            >
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
              emptyText="No risk indicators are recorded from available source facts."
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
        <SectionBlock title="Sources">
          <PortalNonprofitSourceSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Evidence review">
          <PortalEvidenceReviewSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Customer requirements">
          <PortalRequirementsSection detail={detail} />
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
          <StatusBadge
            label={`Evidence review: ${formatReviewStatus(
              detail.review?.evidenceReview.status ?? "not_recorded",
            )}`}
            status={reviewBadgeStatus(
              detail.review?.evidenceReview.status ?? "not_recorded",
            )}
          />
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
        <SectionBlock title="Sources">
          <PortalNonprofitSourceSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Evidence review">
          <PortalEvidenceReviewSection detail={detail} />
        </SectionBlock>
        <SectionBlock title="Customer requirements">
          <PortalRequirementsSection detail={detail} />
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
      key: "evidence-review",
      label: "Evidence review",
      value: formatReviewStatus(
        detail.review?.evidenceReview.status ?? "not_recorded",
      ),
      detail: detail.review
        ? `Contract ${detail.review.contractVersion}`
        : "Review contract not returned",
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

function PortalEvidenceReviewSection({
  detail,
}: {
  detail: PortalNonprofitDetail;
}) {
  const review = detail.review?.evidenceReview;
  if (!review) {
    return (
      <Text c="dimmed">
        Evidence review was not returned for this nonprofit response.
      </Text>
    );
  }

  return (
    <Stack gap="md">
      <DetailFieldList
        items={[
          {
            key: "status",
            label: "Evidence review",
            value: formatReviewStatus(review.status),
          },
          {
            key: "required",
            label: "Required checks",
            value: String(review.sourceCoverage.required.length),
            detail: `${review.sourceCoverage.completed.length} completed`,
          },
          {
            key: "unavailable",
            label: "Unavailable checks",
            value: String(review.sourceCoverage.unavailable.length),
          },
          {
            key: "not-checked",
            label: "Not checked",
            value: String(review.sourceCoverage.notChecked.length),
          },
          {
            key: "customer-decision",
            label: "Customer decision",
            value: detail.review?.customerDecision ?? "Not recorded",
          },
        ]}
      />
      <ReviewIssueList detail={detail} />
      <ReviewCheckTable checks={review.checks} />
    </Stack>
  );
}

function PortalRequirementsSection({
  detail,
}: {
  detail: PortalNonprofitDetail;
}) {
  const evaluation = detail.review?.requirementsEvaluation;
  if (!evaluation) {
    return (
      <Stack gap="xs">
        <Text c="dimmed">
          No customer-owned requirements policy is recorded for this review.
        </Text>
        <Text c="dimmed">Customer decision: Not recorded</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <DetailFieldList
        items={[
          {
            key: "policy",
            label: "Customer policy",
            value: evaluation.policyId,
            detail: `Version ${evaluation.policyVersion}`,
          },
          {
            key: "owner",
            label: "Policy owner",
            value: evaluation.policyOwner,
            detail: evaluation.adoptionStatus,
          },
          {
            key: "result",
            label: "Requirements result",
            value: formatReviewStatus(evaluation.result),
          },
          {
            key: "decision",
            label: "Customer decision",
            value: detail.review?.customerDecision ?? "Not recorded",
          },
        ]}
      />
      <List spacing="xs">
        {evaluation.requirements.map((requirement) => (
          <List.Item key={requirement.requirementId}>
            <Text fw={600}>
              {requirement.description}:{" "}
              {formatReviewStatus(requirement.result)}
            </Text>
            <Text c="dimmed" fz="sm">
              {requirement.explanation}
            </Text>
          </List.Item>
        ))}
      </List>
    </Stack>
  );
}

function ReviewIssueList({ detail }: { detail: PortalNonprofitDetail }) {
  const issues = detail.review?.evidenceReview.issues ?? [];
  if (!issues.length) {
    return <Text c="dimmed">No evidence-review issues are recorded.</Text>;
  }

  return (
    <List spacing="xs">
      {issues.map((issue) => (
        <List.Item key={issue.code}>
          <Text fw={600}>{formatReviewStatus(issue.severity)}</Text>
          <Text>{issue.message}</Text>
        </List.Item>
      ))}
    </List>
  );
}

function ReviewCheckTable({ checks }: { checks: PortalReviewCheck[] }) {
  if (!checks.length) {
    return <Text c="dimmed">No evidence checks are recorded.</Text>;
  }

  return (
    <Table highlightOnHover withColumnBorders withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Check</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Source</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {checks.map((check) => (
          <Table.Tr key={check.checkId}>
            <Table.Td>
              <Stack gap={2}>
                <Text fw={500}>{check.label}</Text>
                <Text c="dimmed" fz="sm">
                  {check.category}
                </Text>
              </Stack>
            </Table.Td>
            <Table.Td>
              <Stack gap={2}>
                <Text>{formatReviewStatus(check.status)}</Text>
                <Text c="dimmed" fz="sm">
                  Observed: {check.observedValue}
                </Text>
              </Stack>
            </Table.Td>
            <Table.Td>
              <Stack gap={2}>
                <Text>{formatCheckSources(check)}</Text>
                <Text c="dimmed" fz="sm">
                  Retrieved: {check.retrievedAt}
                </Text>
              </Stack>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
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

function reviewBadgeStatus(status: string): StatusBadgeStatus {
  const normalized = status.toLowerCase();
  if (
    normalized === "complete" ||
    normalized === "incomplete" ||
    normalized === "stale" ||
    normalized === "conflicting" ||
    normalized === "review_required" ||
    normalized === "source_unavailable"
  ) {
    return normalized;
  }
  return "not_recorded";
}

function formatReviewStatus(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatCheckSources(check: PortalReviewCheck) {
  if (!check.sourceReferences.length) {
    return "Unknown source";
  }
  return check.sourceReferences
    .map((source) => source.providerName || source.sourceName)
    .join(", ");
}
