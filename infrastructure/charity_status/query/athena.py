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
    ) -> None:
        self._database = database
        self._table = table
        self._workgroup = workgroup
        self._poll_interval_seconds = poll_interval_seconds
        self._max_wait_seconds = max_wait_seconds
        self._athena = boto3.client("athena")

    def lookup_nonprofit(self, ein: str, subsection: str | None = None) -> tuple[str, dict[str, Any] | None]:
        where_clause = f"ein = '{ein}'"
        if subsection:
            where_clause += f" AND subsection = '{self._escape_literal(subsection)}'"

        query = f"SELECT * FROM {self._table} WHERE {where_clause} LIMIT 1"

        execution_args: dict[str, Any] = {
            "QueryString": query,
            "QueryExecutionContext": {"Database": self._database},
        }
        if self._workgroup:
            execution_args["WorkGroup"] = self._workgroup

        start_response = self._athena.start_query_execution(**execution_args)
        query_execution_id = start_response["QueryExecutionId"]
        execution = self._wait_for_query(query_execution_id)

        state = execution["QueryExecution"]["Status"]["State"]
        if state != "SUCCEEDED":
            reason = execution["QueryExecution"]["Status"].get("StateChangeReason", "Unknown Athena failure")
            raise AthenaQueryError(f"Athena query failed: {state} ({reason})")

        results = self._athena.get_query_results(QueryExecutionId=query_execution_id)
        rows = self._rows_to_dicts(results.get("ResultSet", {}))
        first = rows[0] if rows else None
        return query_execution_id, first

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
