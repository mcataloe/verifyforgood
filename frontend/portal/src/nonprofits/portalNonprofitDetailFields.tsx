import { DetailFieldList } from "@charity-status/shared-ui";
import type {
  PortalNonprofitDetail,
  PortalNonprofitSourceAvailability,
} from "./nonprofitSearch";
import { summarizeRisk } from "./portalNonprofitStatus";

export function buildSummaryItems(detail: PortalNonprofitDetail) {
  return [
    { key: "irs", label: "IRS status", value: detail.irsStatus },
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

export function buildOverviewItems(detail: PortalNonprofitDetail) {
  return [
    { key: "entity-type", label: "Entity type", value: detail.entityType },
    { key: "state", label: "State", value: detail.state },
    { key: "subsection", label: "Subsection", value: detail.subsection },
    {
      key: "tax-deductible",
      label: "Tax deductible",
      value: detail.taxDeductible,
    },
  ];
}

export function buildFilingsItems(detail: PortalNonprofitDetail) {
  return [
    { key: "filing-form", label: "Filing form", value: detail.filingFormType },
    { key: "filing-year", label: "Filing year", value: detail.filingTaxYear },
    { key: "filing-date", label: "Filing date", value: detail.filingDate },
    {
      key: "filings-count",
      label: "Known filings",
      value: String(detail.filingsCount),
    },
  ];
}

export function buildComplianceItems(detail: PortalNonprofitDetail) {
  return [
    { key: "irs-status", label: "IRS status", value: detail.irsStatus },
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
    { key: "tax-period", label: "Tax period", value: detail.taxPeriod },
  ];
}

function buildSourceItems(detail: PortalNonprofitDetail) {
  return [
    { key: "model-source", label: "Model source", value: detail.modelSource },
    { key: "model-version", label: "Model version", value: detail.modelVersion },
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

export function PortalNonprofitSourceSection({
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
