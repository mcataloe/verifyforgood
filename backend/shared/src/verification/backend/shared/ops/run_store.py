from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def safe_error_summary(errors: list[dict[str, Any]] | None) -> dict[str, Any]:
    items = errors or []
    redacted = []
    for item in items[:50]:
        code = str(item.get("code") or item.get("error_code") or "error")
        message = str(item.get("error") or item.get("message") or "")[:180]
        lowered = message.lower()
        if "secret" in lowered or "token" in lowered or "password" in lowered:
            message = "redacted_sensitive_error"
        redacted.append({"code": code, "message": message})
    return {"count": len(items), "samples": redacted[:10]}


@dataclass
class InMemoryRunStore:
    ingest_runs: dict[str, dict[str, Any]]
    ingest_filings: dict[str, list[dict[str, Any]]]
    refresh_runs: dict[str, dict[str, Any]]
    refresh_eins: dict[str, list[dict[str, Any]]]

    def __init__(self) -> None:
        self.ingest_runs = {}
        self.ingest_filings = {}
        self.refresh_runs = {}
        self.refresh_eins = {}

    def write_ingest_run(self, run_id: str, payload: dict[str, Any]) -> str:
        self.ingest_runs[run_id] = payload
        return run_id

    def write_ingest_filings(self, run_id: str, filings: list[dict[str, Any]]) -> str:
        self.ingest_filings[run_id] = filings
        return run_id

    def write_refresh_run(self, run_id: str, payload: dict[str, Any]) -> str:
        self.refresh_runs[run_id] = payload
        return run_id

    def write_refresh_eins(self, run_id: str, eins: list[dict[str, Any]]) -> str:
        self.refresh_eins[run_id] = eins
        return run_id

    def list_run_summaries(self, run_type: str, limit: int = 50) -> list[dict[str, Any]]:
        source = self.ingest_runs if run_type == "ingest" else self.refresh_runs
        return list(source.values())[: max(1, limit)]

    def get_run(self, run_type: str, run_id: str) -> dict[str, Any] | None:
        source = self.ingest_runs if run_type == "ingest" else self.refresh_runs
        return source.get(run_id)

    def get_run_items(self, run_type: str, run_id: str, item_name: str) -> list[dict[str, Any]] | None:
        if run_type == "ingest" and item_name == "filings":
            return self.ingest_filings.get(run_id)
        if run_type == "refresh" and item_name == "eins":
            return self.refresh_eins.get(run_id)
        return None
