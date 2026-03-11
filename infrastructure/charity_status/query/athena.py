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
