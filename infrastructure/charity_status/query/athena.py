from __future__ import annotations

import time
from typing import Any

import boto3


class AthenaQueryError(RuntimeError):
    pass


class AthenaQueryTimeout(AthenaQueryError):
    pass


class AthenaQueryClient:
    def __init__(
        self,
        database: str,
        table: str,
        workgroup: str | None = None,
        poll_interval_seconds: int = 1,
        max_wait_seconds: int = 25,
        form990_filings_table: str | None = None,
        form990_metrics_table: str | None = None,
        form990_governance_table: str | None = None,
        form990_quality_table: str | None = None,
    ) -> None:
        self._database = database
        self._table = table
        self._workgroup = workgroup
        self._poll_interval_seconds = poll_interval_seconds
        self._max_wait_seconds = max_wait_seconds
        self._form990_filings_table = form990_filings_table
        self._form990_metrics_table = form990_metrics_table
        self._form990_governance_table = form990_governance_table
        self._form990_quality_table = form990_quality_table
        self._athena = boto3.client("athena")

    def lookup_nonprofit(self, ein: str, subsection: str | None = None) -> tuple[str, dict[str, Any] | None]:
        where_clause = f"ein = '{ein}'"
        if subsection:
            where_clause += f" AND subsection = '{self._escape_literal(subsection)}'"

        query = f"SELECT * FROM {self._table} WHERE {where_clause} LIMIT 1"
        return self._run_query_single(query)

    def lookup_form990_enrichment(self, ein: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        filings = self._lookup_latest(self._form990_filings_table, ein)
        metrics = self._lookup_latest(self._form990_metrics_table, ein)
        governance = self._lookup_latest(self._form990_governance_table, ein)
        quality = self._lookup_latest(self._form990_quality_table, ein)
        return filings, metrics, governance, quality

    def list_form990_filings(self, ein: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        if not self._form990_filings_table:
            return "", []
        query = (
            f"SELECT ein, tax_year, return_type, filing_date, amended_return, parse_status "
            f"FROM {self._form990_filings_table} "
            f"WHERE ein = '{self._escape_literal(ein)}' "
            f"ORDER BY try_cast(tax_year as integer) DESC "
            f"LIMIT {int(limit)}"
        )
        return self._run_query_many(query)

    def lookup_peer_benchmark(self, peer_group: dict[str, Any]) -> dict[str, Any]:
        if not self._form990_metrics_table:
            return {"count": 0, "metrics": {}}

        conditions: list[str] = []
        ntee = peer_group.get("ntee")
        org_type = peer_group.get("org_type")
        revenue_band = peer_group.get("revenue_band")

        if ntee and ntee != "unknown":
            conditions.append(f"substr(coalesce(e.ntee_cd, ''), 1, 1) = '{self._escape_literal(str(ntee))}'")
        if org_type and org_type != "unknown":
            conditions.append(f"coalesce(e.subsection, '') = '{self._escape_literal(str(org_type))}'")
        if revenue_band and revenue_band != "unknown":
            conditions.append(self._revenue_band_condition(revenue_band))

        where_clause = " AND ".join([c for c in conditions if c]) if conditions else "1=1"
        query = f"""
        SELECT
          count(*) AS count,
          avg(m.programExpenseRatio) AS programExpenseRatio_mean,
          approx_percentile(m.programExpenseRatio, 0.5) AS programExpenseRatio_median,
          approx_percentile(m.programExpenseRatio, 0.25) AS programExpenseRatio_p25,
          approx_percentile(m.programExpenseRatio, 0.75) AS programExpenseRatio_p75,
          min(m.programExpenseRatio) AS programExpenseRatio_min,
          max(m.programExpenseRatio) AS programExpenseRatio_max,
          avg(m.liabilitiesToAssetsRatio) AS liabilitiesToAssetsRatio_mean,
          approx_percentile(m.liabilitiesToAssetsRatio, 0.5) AS liabilitiesToAssetsRatio_median,
          approx_percentile(m.liabilitiesToAssetsRatio, 0.25) AS liabilitiesToAssetsRatio_p25,
          approx_percentile(m.liabilitiesToAssetsRatio, 0.75) AS liabilitiesToAssetsRatio_p75,
          min(m.liabilitiesToAssetsRatio) AS liabilitiesToAssetsRatio_min,
          max(m.liabilitiesToAssetsRatio) AS liabilitiesToAssetsRatio_max,
          avg(m.operatingMargin) AS operatingMargin_mean,
          approx_percentile(m.operatingMargin, 0.5) AS operatingMargin_median,
          approx_percentile(m.operatingMargin, 0.25) AS operatingMargin_p25,
          approx_percentile(m.operatingMargin, 0.75) AS operatingMargin_p75,
          min(m.operatingMargin) AS operatingMargin_min,
          max(m.operatingMargin) AS operatingMargin_max,
          avg(m.monthsOfRunway) AS monthsOfRunway_mean,
          approx_percentile(m.monthsOfRunway, 0.5) AS monthsOfRunway_median,
          approx_percentile(m.monthsOfRunway, 0.25) AS monthsOfRunway_p25,
          approx_percentile(m.monthsOfRunway, 0.75) AS monthsOfRunway_p75,
          min(m.monthsOfRunway) AS monthsOfRunway_min,
          max(m.monthsOfRunway) AS monthsOfRunway_max
        FROM {self._form990_metrics_table} m
        JOIN {self._table} e ON e.ein = m.ein
        JOIN {self._form990_filings_table} f ON f.ein = m.ein AND f.tax_year = m.tax_year
        WHERE {where_clause}
        """
        _, row = self._run_query_single(query)
        if not row:
            return {"count": 0, "metrics": {}}

        return {
            "count": _to_int(row.get("count")) or 0,
            "metrics": {
                "programExpenseRatio": _metric_block(row, "programExpenseRatio"),
                "liabilitiesToAssetsRatio": _metric_block(row, "liabilitiesToAssetsRatio"),
                "operatingMargin": _metric_block(row, "operatingMargin"),
                "monthsOfRunway": _metric_block(row, "monthsOfRunway"),
            },
        }

    def _lookup_latest(self, table_name: str | None, ein: str) -> dict[str, Any] | None:
        if not table_name:
            return None
        query = (
            f"SELECT * FROM {table_name} "
            f"WHERE ein = '{self._escape_literal(ein)}' "
            f"ORDER BY try_cast(tax_year as integer) DESC "
            "LIMIT 1"
        )
        _, row = self._run_query_single(query)
        return row

    def _run_query_single(self, query: str) -> tuple[str, dict[str, Any] | None]:
        execution_id = self._start_query(query)
        self._ensure_succeeded(execution_id)
        results = self._athena.get_query_results(QueryExecutionId=execution_id)
        rows = self._rows_to_dicts(results.get("ResultSet", {}))
        return execution_id, (rows[0] if rows else None)

    def _run_query_many(self, query: str) -> tuple[str, list[dict[str, Any]]]:
        execution_id = self._start_query(query)
        self._ensure_succeeded(execution_id)
        results = self._athena.get_query_results(QueryExecutionId=execution_id)
        rows = self._rows_to_dicts(results.get("ResultSet", {}))
        return execution_id, rows

    def _start_query(self, query: str) -> str:
        execution_args: dict[str, Any] = {
            "QueryString": query,
            "QueryExecutionContext": {"Database": self._database},
        }
        if self._workgroup:
            execution_args["WorkGroup"] = self._workgroup

        start_response = self._athena.start_query_execution(**execution_args)
        return start_response["QueryExecutionId"]

    def _ensure_succeeded(self, query_execution_id: str) -> None:
        execution = self._wait_for_query(query_execution_id)
        state = execution["QueryExecution"]["Status"]["State"]
        if state != "SUCCEEDED":
            reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "Unknown Athena failure")
            raise AthenaQueryError(f"Athena query failed: {state} ({reason})")

    def _wait_for_query(self, query_execution_id: str) -> dict[str, Any]:
        deadline = time.time() + self._max_wait_seconds
        while time.time() < deadline:
            execution = self._athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = execution["QueryExecution"]["Status"]["State"]
            if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                return execution
            time.sleep(self._poll_interval_seconds)
        raise AthenaQueryTimeout("Athena query timed out before completion")

    @staticmethod
    def _rows_to_dicts(result_set: dict[str, Any]) -> list[dict[str, Any]]:
        rows = result_set.get("Rows", [])
        if not rows:
            return []

        headers = [col.get("VarCharValue", "") for col in rows[0].get("Data", [])]

        records: list[dict[str, Any]] = []
        for row in rows[1:]:
            values = [col.get("VarCharValue") for col in row.get("Data", [])]
            if len(values) < len(headers):
                values.extend([None] * (len(headers) - len(values)))
            records.append(dict(zip(headers, values)))
        return records

    @staticmethod
    def _escape_literal(value: str) -> str:
        return value.replace("'", "''")

    @staticmethod
    def _revenue_band_condition(band: str) -> str:
        if band == "under_250k":
            return "try_cast(f.total_revenue as double) < 250000"
        if band == "250k_to_1m":
            return "try_cast(f.total_revenue as double) >= 250000 AND try_cast(f.total_revenue as double) < 1000000"
        if band == "1m_to_10m":
            return "try_cast(f.total_revenue as double) >= 1000000 AND try_cast(f.total_revenue as double) < 10000000"
        if band == "10m_to_100m":
            return "try_cast(f.total_revenue as double) >= 10000000 AND try_cast(f.total_revenue as double) < 100000000"
        if band == "100m_plus":
            return "try_cast(f.total_revenue as double) >= 100000000"
        return "1=1"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _metric_block(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "mean": _to_float(row.get(f"{prefix}_mean")),
        "median": _to_float(row.get(f"{prefix}_median")),
        "p25": _to_float(row.get(f"{prefix}_p25")),
        "p75": _to_float(row.get(f"{prefix}_p75")),
        "min": _to_float(row.get(f"{prefix}_min")),
        "max": _to_float(row.get(f"{prefix}_max")),
    }
