import { EntityDetailLayout, StatusBadge } from "@charity-status/shared-ui";
import type {
  PortalNonprofitDetail,
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
      summaryItems={[
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
      ]}
      tabs={[
        {
          key: "overview",
          label: "Overview",
          content: (
            <dl className="portal-shell__details">
              <div>
                <dt>Entity type</dt>
                <dd>{detail.entityType}</dd>
              </div>
              <div>
                <dt>State</dt>
                <dd>{detail.state}</dd>
              </div>
              <div>
                <dt>Subsection</dt>
                <dd>{detail.subsection}</dd>
              </div>
              <div>
                <dt>Tax deductible</dt>
                <dd>{detail.taxDeductible}</dd>
              </div>
            </dl>
          ),
        },
        {
          key: "filings",
          label: "Filings",
          content: (
            <dl className="portal-shell__details">
              <div>
                <dt>Filing form</dt>
                <dd>{detail.filingFormType}</dd>
              </div>
              <div>
                <dt>Filing year</dt>
                <dd>{detail.filingTaxYear}</dd>
              </div>
              <div>
                <dt>Filing date</dt>
                <dd>{detail.filingDate}</dd>
              </div>
              <div>
                <dt>Known filings</dt>
                <dd>{String(detail.filingsCount)}</dd>
              </div>
            </dl>
          ),
        },
        {
          key: "compliance",
          label: "Compliance",
          content: (
            <dl className="portal-shell__details">
              <div>
                <dt>IRS status</dt>
                <dd>{detail.irsStatus}</dd>
              </div>
              <div>
                <dt>Recent 990 on file</dt>
                <dd>{detail.recent990OnFile}</dd>
              </div>
              <div>
                <dt>Parse status</dt>
                <dd>{detail.filingParseStatus}</dd>
              </div>
              <div>
                <dt>Tax period</dt>
                <dd>{detail.taxPeriod}</dd>
              </div>
            </dl>
          ),
        },
        {
          key: "sources",
          label: "Sources",
          content: (
            <dl className="portal-shell__details">
              <div>
                <dt>Model source</dt>
                <dd>{detail.modelSource}</dd>
              </div>
              <div>
                <dt>Model version</dt>
                <dd>{detail.modelVersion}</dd>
              </div>
              <div>
                <dt>Query execution</dt>
                <dd>{detail.queryExecutionId}</dd>
              </div>
            </dl>
          ),
        },
        {
          key: "activity",
          label: "Activity Log",
          content: (
            <ul className="portal-list">
              <li>Initial lookup completed for this entity.</li>
              <li>Recent filing metadata has been attached to the review record.</li>
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

export function summaryStatus(
  row: PortalNonprofitSearchSummary,
): StatusBadgeStatus {
  if (row.active === false || row.irsStatus.toLowerCase().includes("inactive")) {
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
