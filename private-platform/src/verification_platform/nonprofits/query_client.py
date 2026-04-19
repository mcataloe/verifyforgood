from __future__ import annotations

from typing import Any

from .sqlalchemy_repository import SqlAlchemyNonprofitRepository

EO_BMF_FILING_FORM_TYPE = "EO_BMF"


class PostgresNonprofitQueryClient:
    def __init__(self, *, repository: SqlAlchemyNonprofitRepository, delegate_client: Any) -> None:
        self._repository = repository
        self._delegate_client = delegate_client

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
        return self._delegate_client.lookup_form990_enrichment(ein)

    def list_form990_filings(self, ein: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        rows = self._repository.list_filings_by_ein(ein, limit=None)
        filtered = [row for row in rows if str(row.get("return_type") or "").strip().upper() != EO_BMF_FILING_FORM_TYPE]
        if limit is not None:
            filtered = filtered[:limit]
        return "postgres:list_form990_filings", filtered

    def lookup_peer_benchmark(self, group: dict[str, Any]) -> dict[str, Any]:
        return self._delegate_client.lookup_peer_benchmark(group)

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
