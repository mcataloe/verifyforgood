from __future__ import annotations

from typing import Any

from verification.backend.ingest.federal.form990.metrics import compute_derived_metrics
from verification.backend.ingest.federal.form990.quality import compute_filing_quality
from verification.backend.shared.scoring.peer_stats import compute_peer_stats

from .sqlalchemy_repository import SqlAlchemyNonprofitRepository

EO_BMF_FILING_FORM_TYPE = "EO_BMF"


class PostgresNonprofitQueryClient:
    def __init__(self, *, repository: SqlAlchemyNonprofitRepository) -> None:
        self._repository = repository

    def lookup_nonprofit(self, ein: str, subsection: str | None = None) -> tuple[str, dict[str, Any] | None]:
        row = self._repository.get_nonprofit_snapshot_by_ein(ein)
        if row is None:
            return "postgres:lookup_nonprofit", None
        if subsection and str(row.get("subsection") or "").strip() != str(subsection).strip():
            return "postgres:lookup_nonprofit", None
        return "postgres:lookup_nonprofit", row

    def lookup_form990_enrichment(
        self,
        ein: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        nonprofit = self._repository.get_nonprofit_by_ein(ein)
        if nonprofit is None or nonprofit.nonprofit_id is None:
            return None, None, None, None

        filings = self._repository.list_filings_for_nonprofit(nonprofit.nonprofit_id)
        latest_filing = next(
            (filing for filing in filings if str(filing.form_type or "").strip().upper() != EO_BMF_FILING_FORM_TYPE),
            None,
        )
        if latest_filing is None:
            return None, None, None, None

        latest_payload = _filing_enrichment_payload(latest_filing)
        history_payloads = [
            _filing_enrichment_payload(filing)
            for filing in reversed(filings)
            if filing is not latest_filing and str(filing.form_type or "").strip().upper() != EO_BMF_FILING_FORM_TYPE
        ]

        metrics = compute_derived_metrics(latest_payload, history=history_payloads)
        governance = {
            "independent_board_majority": latest_payload.get("independent_board_majority"),
            "conflict_of_interest_policy": latest_payload.get("conflict_of_interest_policy"),
            "whistleblower_policy": latest_payload.get("whistleblower_policy"),
            "records_retention_policy": latest_payload.get("records_retention_policy"),
            "contemporaneous_board_minutes": latest_payload.get("contemporaneous_board_minutes"),
            "material_diversion_reported": latest_payload.get("material_diversion_reported"),
            "compensation_review_process": latest_payload.get("compensation_review_process"),
            "public_disclosure_available": latest_payload.get("public_disclosure_available"),
            "audited_financials_indicator": latest_payload.get("audited_financials_indicator"),
        }
        quality = compute_filing_quality(latest_payload, history=history_payloads)
        return latest_payload, metrics, governance, quality

    def list_form990_filings(self, ein: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        rows = self._repository.list_filings_by_ein(ein, limit=None)
        filtered = [
            _form990_filing_summary(row)
            for row in rows
            if str(row.get("return_type") or "").strip().upper() != EO_BMF_FILING_FORM_TYPE
        ]
        if limit is not None:
            filtered = filtered[:limit]
        return "postgres:list_form990_filings", filtered

    def lookup_peer_benchmark(self, group: dict[str, Any]) -> dict[str, Any]:
        rows = self._repository.list_peer_benchmark_filings(
            ntee=_stringify(group.get("ntee")),
            org_type=_stringify(group.get("org_type")),
            revenue_band=_stringify(group.get("revenue_band")),
        )
        metric_rows = []
        for row in rows:
            payload = row.get("raw_payload")
            if not isinstance(payload, dict) or not payload:
                continue
            metric_rows.append(compute_derived_metrics(payload))
        return compute_peer_stats(
            metric_rows,
            ["programExpenseRatio", "liabilitiesToAssetsRatio", "operatingMargin", "monthsOfRunway"],
        )

    def list_nonprofit_eins_page(self, limit: int, start_after_ein: str | None = None) -> list[str]:
        return self._repository.list_nonprofit_eins_page(limit=limit, start_after_ein=start_after_ein)

    def search_nonprofits(
        self,
        *,
        name_query: str,
        limit: int,
        state: str | None = None,
        subsection: str | None = None,
        active_only: bool = False,
        cursor_name: str | None = None,
        cursor_ein: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        rows = self._repository.search_nonprofit_summaries(
            name_query=name_query,
            limit=limit,
            state=state,
            subsection=subsection,
            active_only=active_only,
            cursor_name=cursor_name,
            cursor_ein=cursor_ein,
        )
        return "postgres:search_nonprofits", rows


__all__ = ["PostgresNonprofitQueryClient"]


def _filing_enrichment_payload(filing: Any) -> dict[str, Any]:
    payload = dict(filing.raw_payload or {})
    if not payload:
        payload = {}

    payload.setdefault("ein", None)
    payload["tax_year"] = payload.get("tax_year") or _stringify(filing.tax_year)
    payload["return_type"] = payload.get("return_type") or filing.form_type
    payload["filing_date"] = payload.get("filing_date") or filing.filing_date
    payload["amended_return"] = payload.get("amended_return")
    if payload["amended_return"] is None:
        payload["amended_return"] = filing.amended
    payload["parse_status"] = payload.get("parse_status") or filing.parse_status
    payload["total_assets_eoy"] = payload.get("total_assets_eoy")
    if payload["total_assets_eoy"] is None:
        payload["total_assets_eoy"] = filing.total_assets
    payload["total_income"] = payload.get("total_income")
    if payload["total_income"] is None:
        payload["total_income"] = filing.total_income
    payload["total_revenue"] = payload.get("total_revenue")
    if payload["total_revenue"] is None:
        payload["total_revenue"] = filing.total_revenue
    return payload


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _form990_filing_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ein": row.get("ein"),
        "tax_year": row.get("tax_year"),
        "return_type": row.get("return_type"),
        "filing_date": row.get("filing_date"),
        "amended_return": row.get("amended_return"),
        "parse_status": row.get("parse_status"),
    }
