import {
  DetailFieldList,
  DetailStack,
  EntityDetailLayout,
  StatusBadge,
} from "@charity-status/shared-ui";
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
    <EntityDetailLayout
      actions={<StatusBadge status={detailStatus(detail)} />}
      description="Shared organization detail layout for trust-forward entity review."
      ein={detail.ein}
      name={detail.name}
      onPrimaryAction={() => undefined}
      primaryActionLabel="Queue review"
      status={detailStatus(detail)}
      summaryItems={buildSummaryItems(detail)}
      tabs={[
        {
          key: "overview",
          label: "Overview",
          content: <DetailFieldList items={buildOverviewItems(detail)} />,
        },
        {
          key: "filings",
          label: "Filings",
          content: <DetailFieldList items={buildFilingsItems(detail)} />,
        },
        {
          key: "compliance",
          label: "Compliance",
          content: <DetailFieldList items={buildComplianceItems(detail)} />,
        },
        {
          key: "sources",
          label: "Sources",
          content: <PortalNonprofitSourceSection detail={detail} />,
        },
        {
          key: "activity",
          label: "Activity Log",
          content: (
            <ul className="portal-list">
              <li>Initial lookup completed for this entity.</li>
              <li>
                Recent filing metadata has been attached to the review record.
              </li>
              <li>
                Detailed activity history can replace this placeholder once the
                event feed exists.
              </li>
            </ul>
          ),
        },
      ]}
    />
  );
}

export function PortalNonprofitEmbeddedDetail({
  detail,
}: PortalNonprofitDetailViewProps) {
  return (
    <article className="portal-nonprofit-embedded-detail">
      <header className="portal-nonprofit-embedded-detail__header">
        <div className="portal-nonprofit-embedded-detail__title-row">
          <h3>{detail.name}</h3>
          <StatusBadge status={detailStatus(detail)} />
        </div>
        <p className="portal-nonprofit-embedded-detail__identifier">
          EIN {detail.ein}
        </p>
        <DetailFieldList items={buildSummaryItems(detail)} />
      </header>

      <div className="portal-nonprofit-embedded-detail__sections">
        <DetailStack title="Overview">
          <DetailFieldList items={buildOverviewItems(detail)} />
        </DetailStack>
        <DetailStack title="Filings">
          <DetailFieldList items={buildFilingsItems(detail)} />
        </DetailStack>
        <DetailStack title="Compliance">
          <DetailFieldList items={buildComplianceItems(detail)} />
        </DetailStack>
        <DetailStack title="Sources">
          <PortalNonprofitSourceSection detail={detail} />
        </DetailStack>
        <DetailStack title="Activity">
          <ul className="portal-list">
            <li>Initial lookup completed for this entity.</li>
            <li>
              Recent filing metadata has been attached to the review record.
            </li>
            <li>
              Detailed activity history can replace this placeholder once the
              event feed exists.
            </li>
          </ul>
        </DetailStack>
      </div>
    </article>
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
      key: "model-source",
      label: "Model source",
      value: detail.modelSource,
    },
    {
      key: "model-version",
      label: "Model version",
      value: detail.modelVersion,
    },
    {
      key: "query-execution",
      label: "Query execution",
      value: detail.queryExecutionId,
    },
    {
      key: "source-checks",
      label: "Available source checks",
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
        <table className="portal-embedded-detail__table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Status</th>
              <th>Attempted</th>
            </tr>
          </thead>
          <tbody>
            {detail.sourceAvailability.map((source) => (
              <tr key={source.integrationId}>
                <td>{source.label}</td>
                <td>{formatSourceStatus(source)}</td>
                <td>{source.attempted ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="portal-detail-view__section-intro">
          No enrichment source availability metadata was returned for this
          nonprofit.
        </p>
      )}
    </>
  );
}

function formatSourceStatus(source: PortalNonprofitSourceAvailability) {
  switch (source.status) {
    case "tenant_disabled":
      return "Disabled for this workspace";
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
