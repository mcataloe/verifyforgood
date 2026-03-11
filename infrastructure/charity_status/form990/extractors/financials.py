from __future__ import annotations

from typing import Any

from charity_status.form990.parser import ParsedXml
from charity_status.form990.resolver import resolve_decimal


FINANCIAL_SELECTORS = {
    "total_revenue": [".//{*}TotalRevenueAmt", ".//{*}CYTotalRevenueAmt"],
    "total_expenses": [".//{*}TotalExpensesAmt", ".//{*}CYTotalExpensesAmt"],
    "program_service_expenses": [".//{*}ProgramServiceExpensesAmt", ".//{*}CYProgramServiceExpnsAmt"],
    "management_general_expenses": [".//{*}ManagementAndGeneralAmt", ".//{*}CYManagementAndGeneralAmt"],
    "fundraising_expenses": [".//{*}FundraisingAmt", ".//{*}CYFundraisingAmt"],
    "contributions_revenue": [".//{*}ContributionsGrantsAmt", ".//{*}CYContributionsGrantsAmt"],
    "total_assets_eoy": [".//{*}TotalAssetsEOYAmt", ".//{*}EOYAssetsAmt"],
    "total_liabilities_eoy": [".//{*}TotalLiabilitiesEOYAmt", ".//{*}EOYLiabilitiesAmt"],
    "net_assets_eoy": [".//{*}NetAssetsOrFundBalancesEOYAmt", ".//{*}EOYNetAssetsOrFundBalancesAmt"],
    "grants_paid": [".//{*}GrantsAndSimilarPaidAmt", ".//{*}CYGrantsAndSimilarPaidAmt"],
    "officer_compensation": [".//{*}CompCurrentOfcrDirectorsKeyEmplAmt", ".//{*}CompCurrentOfficersDirectorsAmt"],
}


def extract_financial_fields(parsed_xml: ParsedXml) -> dict[str, Any]:
    root = parsed_xml.root
    return {
        field: resolve_decimal(root, paths)
        for field, paths in FINANCIAL_SELECTORS.items()
    }
