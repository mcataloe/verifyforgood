from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from charity_status.form990.index import parse_index_records, parse_index_source_payload
from charity_status.form990.models import Form990IndexRecord
from charity_status.form990.storage import filing_catalog_key, filing_diff_key, state_manifest_key

TERMINAL_COMPLETE_STATUSES = {"parsed", "unsupported_return_type"}
REQUIRED_PARSED_ARTIFACT_KEYS = (
    "manifest_s3_key",
    "filing_records_s3_key",
    "metrics_s3_key",
    "governance_s3_key",
    "quality_s3_key",
    "relationships_s3_key",
)


@dataclass(frozen=True)
class FilingReconciliationResult:
    current_records: tuple[Form990IndexRecord, ...]
    selected_records: tuple[Form990IndexRecord, ...]
    latest_state_entries: tuple[dict[str, Any], ...]
    new_count: int
    changed_count: int
    unchanged_count: int
    incomplete_count: int
    catalog_key: str
    diff_key: str
    state_key: str


def reconcile_filing_catalog(
    *,
    s3_client: Any,
    bucket: str,
    manifest_prefix: str,
    run_id: str,
    csv_sources: list[dict[str, Any]],
    now: datetime | None = None,
) -> FilingReconciliationResult:
    now_dt = now or datetime.now(timezone.utc)
    previous_entries = load_filing_state(s3_client, bucket, manifest_prefix)
    current_records = load_csv_catalog_records(s3_client, bucket, csv_sources)
    current_records = sorted(current_records, key=lambda item: (item.source_year or "", _filing_identity(item)))
    selected_records, next_state_entries, diff_payload = _reconcile_records(
        current_records=current_records,
        previous_entries=previous_entries,
        inspected_years={str(item.get("source_year") or "").strip() for item in csv_sources if isinstance(item, dict)},
        run_id=run_id,
        generated_at=now_dt.isoformat(),
    )

    catalog_payload = {
        "generated_at": now_dt.isoformat(),
        "run_id": run_id,
        "count": len(current_records),
        "filings": [filing_record_to_state_entry(item) for item in current_records],
    }
    catalog_s3_key = filing_catalog_key(manifest_prefix, run_id)
    diff_s3_key = filing_diff_key(manifest_prefix, run_id)
    state_s3_key = state_manifest_key(manifest_prefix)
    s3_client.put_object(Bucket=bucket, Key=catalog_s3_key, Body=json.dumps(catalog_payload, sort_keys=True).encode("utf-8"))
    s3_client.put_object(Bucket=bucket, Key=diff_s3_key, Body=json.dumps(diff_payload, sort_keys=True).encode("utf-8"))
    s3_client.put_object(
        Bucket=bucket,
        Key=state_s3_key,
        Body=json.dumps({"generated_at": now_dt.isoformat(), "count": len(next_state_entries), "filings": next_state_entries}, sort_keys=True).encode("utf-8"),
    )

    return FilingReconciliationResult(
        current_records=tuple(current_records),
        selected_records=tuple(selected_records),
        latest_state_entries=tuple(next_state_entries),
        new_count=int(diff_payload["new_count"]),
        changed_count=int(diff_payload["changed_count"]),
        unchanged_count=int(diff_payload["unchanged_count"]),
        incomplete_count=int(diff_payload["incomplete_count"]),
        catalog_key=catalog_s3_key,
        diff_key=diff_s3_key,
        state_key=state_s3_key,
    )


def load_filing_state(s3_client: Any, bucket: str, manifest_prefix: str) -> list[dict[str, Any]]:
    try:
        payload = s3_client.get_object(Bucket=bucket, Key=state_manifest_key(manifest_prefix))["Body"].read().decode("utf-8")
        data = json.loads(payload)
    except Exception:
        return []
    filings = data.get("filings")
    if not isinstance(filings, list):
        return []
    return [item for item in filings if isinstance(item, dict)]


def load_csv_catalog_records(s3_client: Any, bucket: str, csv_sources: list[dict[str, Any]]) -> list[Form990IndexRecord]:
    records: list[Form990IndexRecord] = []
    for source in sorted(csv_sources, key=_source_sort_key):
        if not isinstance(source, dict):
            continue
        source_key = str(source.get("raw_source_s3_key") or "").strip()
        source_url = str(source.get("source_url") or "").strip()
        if not source_key or not source_url:
            continue
        body = s3_client.get_object(Bucket=bucket, Key=source_key)["Body"].read()
        rows = parse_index_source_payload(source_url, body)
        for record in parse_index_records(rows):
            archive_hint = str(record.source_archive or "").strip() or None
            records.append(
                Form990IndexRecord(
                    ein=record.ein,
                    tax_year=record.tax_year,
                    filing_date=record.filing_date,
                    return_type=record.return_type,
                    irs_object_id=record.irs_object_id,
                    xml_url=record.xml_url,
                    source_year=str(source.get("source_year") or record.source_year or "").strip() or None,
                    source_archive=archive_hint or str(source.get("source_archive_key") or source.get("source_filename") or "").strip() or None,
                    source_signature=filing_signature(record, source),
                )
            )
    deduped: dict[str, Form990IndexRecord] = {}
    for record in records:
        deduped[_filing_identity(record)] = record
    return list(deduped.values())


def filing_record_to_state_entry(record: Form990IndexRecord) -> dict[str, Any]:
    entry = asdict(record)
    entry.update(
        {
            "filing_id": _filing_identity(record),
            "filing_signature": record.source_signature,
            "raw_source_present": bool(record.source_year and record.source_archive),
            "raw_xml_present": False,
            "normalized_complete": False,
            "completion_status": "pending",
            "parse_status": None,
            "completed_at": None,
            "raw_s3_key": None,
            "manifest_s3_key": None,
            "filing_records_s3_key": None,
            "metrics_s3_key": None,
            "governance_s3_key": None,
            "quality_s3_key": None,
            "relationships_s3_key": None,
        }
    )
    return entry


def update_filing_state_from_ingest_result(
    *,
    s3_client: Any,
    bucket: str,
    manifest_prefix: str,
    input_records: list[dict[str, Any]],
    ingest_result: dict[str, Any],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current_state = load_filing_state(s3_client, bucket, manifest_prefix)
    current_by_id = {_entry_filing_id(item): dict(item) for item in current_state}
    input_index_records = parse_index_records(input_records)
    result_records = ingest_result.get("records")
    if not isinstance(result_records, list):
        result_records = []

    for idx, input_record in enumerate(input_index_records):
        filing_id = _filing_identity(input_record)
        existing = dict(current_by_id.get(filing_id) or filing_record_to_state_entry(input_record))
        result_record = result_records[idx] if idx < len(result_records) and isinstance(result_records[idx], dict) else {}
        updated = {
            **existing,
            "ein": input_record.ein,
            "tax_year": input_record.tax_year,
            "filing_date": input_record.filing_date,
            "return_type": input_record.return_type,
            "irs_object_id": input_record.irs_object_id,
            "xml_url": input_record.xml_url,
            "source_year": input_record.source_year,
            "source_archive": input_record.source_archive,
            "filing_id": filing_id,
            "filing_signature": input_record.source_signature or existing.get("filing_signature"),
            "raw_source_present": bool(input_record.source_year and input_record.source_archive),
            "raw_xml_present": bool(result_record.get("raw_s3_key")),
            "raw_s3_key": result_record.get("raw_s3_key"),
            "parse_status": result_record.get("parse_status"),
            "parse_error": result_record.get("parse_error"),
            "completed_at": (now or datetime.now(timezone.utc)).isoformat(),
            "manifest_s3_key": ingest_result.get("manifest_s3_key"),
            "filing_records_s3_key": ingest_result.get("filing_records_s3_key"),
            "metrics_s3_key": ingest_result.get("metrics_s3_key"),
            "governance_s3_key": ingest_result.get("governance_s3_key"),
            "quality_s3_key": ingest_result.get("quality_s3_key"),
            "relationships_s3_key": ingest_result.get("relationships_s3_key"),
        }
        completion_status = str(updated.get("parse_status") or "").strip()
        normalized_complete = filing_processing_complete(updated)
        updated["normalized_complete"] = normalized_complete
        updated["completion_status"] = completion_status if normalized_complete else "incomplete"
        current_by_id[filing_id] = updated

    merged = sorted(current_by_id.values(), key=_state_sort_key)
    s3_client.put_object(
        Bucket=bucket,
        Key=state_manifest_key(manifest_prefix),
        Body=json.dumps({"generated_at": (now or datetime.now(timezone.utc)).isoformat(), "count": len(merged), "filings": merged}, sort_keys=True).encode("utf-8"),
    )
    return merged


def filing_processing_complete(entry: dict[str, Any]) -> bool:
    status = str(entry.get("parse_status") or entry.get("completion_status") or "").strip()
    if status == "parsed":
        return bool(entry.get("raw_s3_key")) and all(entry.get(key) for key in REQUIRED_PARSED_ARTIFACT_KEYS)
    if status == "unsupported_return_type":
        return bool(entry.get("completed_at"))
    return False


def filing_signature(record: Form990IndexRecord, source: dict[str, Any] | None = None) -> str:
    values = [
        _normalize_text(record.irs_object_id),
        _normalize_text(record.ein),
        _normalize_text(record.tax_year),
        _normalize_text(record.return_type),
        _normalize_text(record.filing_date),
        _normalize_text(record.xml_url),
        _normalize_text(record.source_year or (source or {}).get("source_year")),
        _normalize_text(record.source_archive or (source or {}).get("source_archive_key") or (source or {}).get("source_filename")),
    ]
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def _reconcile_records(
    *,
    current_records: list[Form990IndexRecord],
    previous_entries: list[dict[str, Any]],
    inspected_years: set[str],
    run_id: str,
    generated_at: str,
) -> tuple[list[Form990IndexRecord], list[dict[str, Any]], dict[str, Any]]:
    previous_by_id = {_entry_filing_id(item): item for item in previous_entries if _entry_filing_id(item)}
    selected_records: list[Form990IndexRecord] = []
    next_state_entries: list[dict[str, Any]] = []
    new_entries: list[dict[str, Any]] = []
    changed_entries: list[dict[str, Any]] = []
    incomplete_entries: list[dict[str, Any]] = []
    unchanged_count = 0

    for record in current_records:
        filing_id = _filing_identity(record)
        previous = previous_by_id.get(filing_id)
        if previous is None:
            entry = filing_record_to_state_entry(record)
            next_state_entries.append(entry)
            selected_records.append(record)
            new_entries.append(entry)
            continue

        same_signature = str(previous.get("filing_signature") or previous.get("source_signature") or "") == str(record.source_signature or "")
        merged = _merge_previous_entry(record, previous, preserve_completion=same_signature)
        next_state_entries.append(merged)

        if not same_signature:
            selected_records.append(record)
            changed_entries.append({"before": previous, "after": merged})
            continue
        if not filing_processing_complete(merged):
            selected_records.append(record)
            incomplete_entries.append(merged)
            continue
        unchanged_count += 1

    preserved_previous = [item for item in previous_entries if str(item.get("source_year") or "").strip() not in inspected_years]
    latest_state_entries = sorted([*preserved_previous, *next_state_entries], key=_state_sort_key)
    diff_payload = {
        "generated_at": generated_at,
        "run_id": run_id,
        "catalog_count": len(current_records),
        "selected_count": len(selected_records),
        "new_count": len(new_entries),
        "changed_count": len(changed_entries),
        "unchanged_count": unchanged_count,
        "incomplete_count": len(incomplete_entries),
        "new_filings": new_entries,
        "changed_filings": changed_entries,
        "incomplete_filings": incomplete_entries,
    }
    return selected_records, latest_state_entries, diff_payload


def _merge_previous_entry(record: Form990IndexRecord, previous: dict[str, Any], preserve_completion: bool) -> dict[str, Any]:
    entry = {
        **filing_record_to_state_entry(record),
        "raw_source_present": True,
    }
    if preserve_completion:
        merged = {
            **previous,
            **entry,
            "raw_xml_present": bool(previous.get("raw_xml_present")),
            "normalized_complete": bool(previous.get("normalized_complete")) and filing_processing_complete(previous),
            "completion_status": previous.get("completion_status"),
            "parse_status": previous.get("parse_status"),
            "parse_error": previous.get("parse_error"),
            "completed_at": previous.get("completed_at"),
            "raw_s3_key": previous.get("raw_s3_key"),
            "manifest_s3_key": previous.get("manifest_s3_key"),
            "filing_records_s3_key": previous.get("filing_records_s3_key"),
            "metrics_s3_key": previous.get("metrics_s3_key"),
            "governance_s3_key": previous.get("governance_s3_key"),
            "quality_s3_key": previous.get("quality_s3_key"),
            "relationships_s3_key": previous.get("relationships_s3_key"),
        }
        merged["normalized_complete"] = filing_processing_complete(merged)
        if not merged["normalized_complete"] and str(merged.get("completion_status") or "").strip() in TERMINAL_COMPLETE_STATUSES:
            merged["completion_status"] = "incomplete"
        return merged
    return entry


def _entry_filing_id(entry: dict[str, Any]) -> str:
    return str(entry.get("filing_id") or "").strip()


def _filing_identity(record: Form990IndexRecord) -> str:
    object_id = _normalize_text(record.irs_object_id)
    if object_id:
        return f"irs_object_id:{object_id}"
    composite = "|".join(
        [
            _normalize_text(record.ein),
            _normalize_text(record.tax_year),
            _normalize_text(record.return_type),
            _normalize_text(record.filing_date),
            _normalize_text(record.source_year),
            _normalize_text(record.source_archive),
        ]
    )
    return f"composite:{hashlib.sha256(composite.encode('utf-8')).hexdigest()}"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _source_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or "").strip(),
        str(entry.get("source_archive_key") or entry.get("source_filename") or "").strip(),
        str(entry.get("raw_source_s3_key") or "").strip(),
    )


def _state_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or "").strip(),
        str(entry.get("source_archive") or "").strip(),
        _entry_filing_id(entry),
    )
