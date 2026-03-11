from __future__ import annotations

from typing import Any

from charity_status.form990.parser import ParsedXml
from charity_status.form990.resolver import resolve_bool


GOVERNANCE_SELECTORS = {
    "independent_board_majority": [".//{*}IndBoardMajorityInd"],
    "conflict_of_interest_policy": [".//{*}ConflictOfInterestPolicyInd"],
    "whistleblower_policy": [".//{*}WhistleblowerPolicyInd"],
    "records_retention_policy": [".//{*}DocumentRetentionPolicyInd", ".//{*}RecordsRetentionPolicyInd"],
    "contemporaneous_board_minutes": [".//{*}ContemporaneousMeetingsInd"],
    "material_diversion_reported": [".//{*}MaterialDiversionOrMisuseInd"],
    "compensation_review_process": [".//{*}CompensationProcessCEOAndKeyEmplInd"],
    "public_disclosure_available": [".//{*}GoverningDocumentsDiscloseInd", ".//{*}Form990ProvidedToPublicInd"],
    "audited_financials_indicator": [".//{*}AuditOrReviewInd", ".//{*}IndependentAuditFinancialStmtInd"],
}


def extract_governance_fields(parsed_xml: ParsedXml) -> dict[str, Any]:
    root = parsed_xml.root
    return {
        field: resolve_bool(root, paths)
        for field, paths in GOVERNANCE_SELECTORS.items()
    }
