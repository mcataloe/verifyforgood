import type { StatusBadgeStatus } from "@charity-status/shared-ui";
import type {
  PortalNonprofitDetail,
  PortalNonprofitSearchSummary,
} from "./nonprofitSearch";

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
  if (detail.irsStatus.toLowerCase().includes("inactive")) return "inactive";
  if (
    detail.filingParseStatus.toLowerCase() !== "parsed" ||
    detail.recent990OnFile.toLowerCase() !== "true"
  ) {
    return "flagged";
  }
  if (detail.irsStatus.toLowerCase().includes("active")) return "verified";
  return "pending";
}

export function summarizeRisk(detail: PortalNonprofitDetail) {
  const risks: string[] = [];
  if (detail.filingParseStatus.toLowerCase() !== "parsed") {
    risks.push("Parsing needs review");
  }
  if (detail.recent990OnFile.toLowerCase() !== "true") {
    risks.push("Recent 990 unavailable");
  }
  return risks.length ? risks.join(" | ") : "No immediate flags";
}
