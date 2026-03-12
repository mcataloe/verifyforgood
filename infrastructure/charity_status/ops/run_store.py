from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
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


class S3RunStore:
    def __init__(self, bucket: str, prefix: str, s3_client: Any):
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._s3 = s3_client

    def write_ingest_run(self, run_id: str, payload: dict[str, Any]) -> str:
        key = f"{self._prefix}/ingest/runs/{run_id}.json"
        self._put_json(key, payload)
        return key

    def write_ingest_filings(self, run_id: str, filings: list[dict[str, Any]]) -> str:
        key = f"{self._prefix}/ingest/runs/{run_id}/filings.jsonl"
        lines = "\n".join(json.dumps(item, sort_keys=True) for item in filings) + ("\n" if filings else "")
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=lines.encode("utf-8"))
        return key

    def write_refresh_run(self, run_id: str, payload: dict[str, Any]) -> str:
        key = f"{self._prefix}/refresh/runs/{run_id}.json"
        self._put_json(key, payload)
        return key

    def write_refresh_eins(self, run_id: str, eins: list[dict[str, Any]]) -> str:
        key = f"{self._prefix}/refresh/runs/{run_id}/eins.jsonl"
        lines = "\n".join(json.dumps(item, sort_keys=True) for item in eins) + ("\n" if eins else "")
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=lines.encode("utf-8"))
        return key

    def list_run_summaries(self, run_type: str, limit: int = 50) -> list[dict[str, Any]]:
        prefix = f"{self._prefix}/{run_type}/runs/"
        response = self._s3.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        keys = sorted(
            [obj["Key"] for obj in response.get("Contents", []) if obj.get("Key", "").endswith(".json")],
            reverse=True,
        )[: max(1, limit)]
        return [self._get_json(key) for key in keys]

    def get_run(self, run_type: str, run_id: str) -> dict[str, Any] | None:
        key = f"{self._prefix}/{run_type}/runs/{run_id}.json"
        return self._try_get_json(key)

    def get_run_items(self, run_type: str, run_id: str, item_name: str) -> list[dict[str, Any]] | None:
        key = f"{self._prefix}/{run_type}/runs/{run_id}/{item_name}.jsonl"
        try:
            body = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read().decode("utf-8")
        except Exception:
            return None
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        return [json.loads(line) for line in lines]

    def _put_json(self, key: str, payload: dict[str, Any]) -> None:
        if "updated_at" not in payload:
            payload = {**payload, "updated_at": datetime.now(timezone.utc).isoformat()}
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=json.dumps(payload, sort_keys=True).encode("utf-8"))

    def _get_json(self, key: str) -> dict[str, Any]:
        body = self._s3.get_object(Bucket=self._bucket, Key=key)["Body"].read().decode("utf-8")
        return json.loads(body)

    def _try_get_json(self, key: str) -> dict[str, Any] | None:
        try:
            return self._get_json(key)
        except Exception:
            return None


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
