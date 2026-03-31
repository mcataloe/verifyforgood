import {
  DetailFieldList,
  StatusBadge,
} from "@charity-status/shared-ui";
import {
  DetailPageLayout,
  SectionBlock,
  SectionDivider,
} from "../components/shell";
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
        <header className="portal-detail-layout__header">
          <p className="portal-shell__eyebrow">Entity review</p>
          <div className="portal-nonprofit-embedded-detail__title-row">
            <h1>{detail.name}</h1>
            <StatusBadge status={detailStatus(detail)} />
            <button className="portal-shell__action" onClick={() => undefined} type="button">
              Queue review
            </button>
          </div>
          <p className="portal-detail-layout__intro">
            Review the latest organization details, filings, and source checks.
          </p>
          <p className="portal-nonprofit-embedded-detail__identifier">
            EIN {detail.ein}
          </p>
        </header>
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
      </div>
    </article>
  );
}

function ActivityList() {
  return (
    <ul className="portal-list">
      <li>Initial review completed for this organization.</li>
      <li>Recent filing information is available in this record.</li>
      <li>Additional activity will appear here as more updates are recorded.</li>
    </ul>
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
          No source checks are available for this organization yet.
        </p>
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
