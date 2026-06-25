from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from verification.backend.shared.normalization import recent_990_on_file

from .sqlalchemy_repository import (
    NonprofitAdvisoryArtifactRecord,
    NonprofitDetailSnapshotRecord,
    NonprofitRecord,
    SqlAlchemyNonprofitRepository,
)


DETAIL_SNAPSHOT_SCHEMA_VERSION = "nonprofit_detail_snapshot.v1"
DETAIL_SNAPSHOT_RENDERER_VERSION = "advisory_copilot_detail.v1"
DETAIL_SNAPSHOT_TTL = timedelta(days=7)
ADVISORY_ARTIFACT_SCHEMA_VERSION = "nonprofit_advisory_artifact.v1"
ADVISORY_ARTIFACT_RENDERER_VERSION = "advisory_copilot_detail.v1"
ADVISORY_ARTIFACT_TYPE = "nonprofit_advisory_evaluation"


class NonprofitAdvisoryDetailService:
    def __init__(self, *, repository: SqlAlchemyNonprofitRepository) -> None:
        self._repository = repository

    def get_detail(self, ein: str) -> dict[str, Any] | None:
        nonprofit = self._repository.get_nonprofit_by_ein(ein)
        if nonprofit is None:
            return None

        inputs = self._load_snapshot_inputs(nonprofit)
        source_hash = _stable_hash(inputs)
        current = self._repository.get_nonprofit_detail_snapshot(nonprofit.ein)
        if _snapshot_is_fresh(current, source_hash):
            return dict(current.payload_json)

        payload = _build_detail_payload(inputs)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        payload["snapshot"] = {
            "materialized_at": now.isoformat(),
            "source_hash": source_hash,
            "schema_version": DETAIL_SNAPSHOT_SCHEMA_VERSION,
            "renderer_version": DETAIL_SNAPSHOT_RENDERER_VERSION,
        }
        stored = self._repository.upsert_nonprofit_detail_snapshot(
            NonprofitDetailSnapshotRecord(
                snapshot_id=current.snapshot_id if current is not None else None,
                nonprofit_id=nonprofit.nonprofit_id,
                ein=nonprofit.ein,
                payload_json=payload,
                source_hash=source_hash,
                schema_version=DETAIL_SNAPSHOT_SCHEMA_VERSION,
                renderer_version=DETAIL_SNAPSHOT_RENDERER_VERSION,
                materialized_at=now.isoformat(),
                expires_at=(now + DETAIL_SNAPSHOT_TTL).isoformat(),
                build_status="succeeded",
                last_error=None,
                created_at=current.created_at if current is not None else now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        return dict(stored.payload_json)

    def persist_advisory_artifact(
        self,
        *,
        ein: str,
        payload: dict[str, Any],
    ) -> NonprofitAdvisoryArtifactRecord | None:
        nonprofit = self._repository.get_nonprofit_by_ein(ein)
        if nonprofit is None or nonprofit.nonprofit_id is None:
            return None

        advisory_payload = _sanitize_verification_payload(payload)
        return self._repository.create_nonprofit_advisory_artifact(
            NonprofitAdvisoryArtifactRecord(
                artifact_id=None,
                nonprofit_id=nonprofit.nonprofit_id,
                ein=nonprofit.ein,
                artifact_type=ADVISORY_ARTIFACT_TYPE,
                payload_json=advisory_payload,
                source_hash=_stable_hash(advisory_payload),
                schema_version=ADVISORY_ARTIFACT_SCHEMA_VERSION,
                renderer_version=ADVISORY_ARTIFACT_RENDERER_VERSION,
                build_status="succeeded",
                error_json=None,
                created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            )
        )

    def _load_snapshot_inputs(self, nonprofit: NonprofitRecord) -> dict[str, Any]:
        filings = self._repository.list_filings_by_ein(nonprofit.ein)
        latest_filing = filings[0] if filings else None
        sources = self._repository.list_sources_by_ein(nonprofit.ein)
        latest_check = self._repository.latest_compliance_check_by_ein(nonprofit.ein)
        summarized_sources = _summarize_sources(sources)
        recent_filing = recent_990_on_file(
            (latest_filing or {}).get("tax_period") or nonprofit.last_seen_at
        )
        return {
            "nonprofit": {
                "ein": nonprofit.ein,
                "name": nonprofit.canonical_name,
                "entity_type": nonprofit.entity_type,
                "irs_status": nonprofit.irs_status,
                "ntee_category": nonprofit.ntee_category,
                "state": nonprofit.state,
                "subsection": nonprofit.subsection_code,
                "tax_deductible": nonprofit.tax_deductible,
                "canonical_source": nonprofit.canonical_source,
                "source_version": nonprofit.source_version,
                "last_seen_at": nonprofit.last_seen_at,
            },
            "filings": {
                "count": len(filings),
                "latest": latest_filing,
                "recent_990_on_file": recent_filing,
            },
            "sources": summarized_sources,
            "compliance": None
            if latest_check is None
            else {
                "check_type": latest_check.check_type,
                "status": latest_check.status,
                "evaluated_at": latest_check.evaluated_at,
                "summary": latest_check.summary_json,
                "flags": latest_check.flags_json,
                "reasons": latest_check.reasons_json,
            },
        }


def _snapshot_is_fresh(
    snapshot: NonprofitDetailSnapshotRecord | None,
    current_source_hash: str,
) -> bool:
    if snapshot is None or snapshot.build_status != "succeeded":
        return False
    if snapshot.source_hash != current_source_hash:
        return False
    if snapshot.schema_version != DETAIL_SNAPSHOT_SCHEMA_VERSION:
        return False
    if snapshot.renderer_version != DETAIL_SNAPSHOT_RENDERER_VERSION:
        return False
    expires_at = _parse_iso_timestamp(snapshot.expires_at)
    if expires_at is not None and expires_at <= datetime.now(timezone.utc):
        return False
    return True


def _build_detail_payload(inputs: dict[str, Any]) -> dict[str, Any]:
    nonprofit = inputs["nonprofit"]
    filings = inputs["filings"]
    latest_filing = filings["latest"] or {}
    sources = inputs["sources"]
    compliance = inputs["compliance"]

    appears_because = _build_appears_because(nonprofit, filings, sources)
    highlights = _build_highlights(nonprofit, latest_filing, filings, compliance)
    risk_indicators = _build_risk_indicators(nonprofit, latest_filing, filings, compliance)
    data_gaps = _build_data_gaps(nonprofit, latest_filing, filings, sources, compliance)

    return {
        "organization": {
            "ein": nonprofit["ein"],
            "name": nonprofit["name"],
        },
        "overview": {
            "entity_type": nonprofit["entity_type"],
            "irs_status": nonprofit["irs_status"],
            "ntee_category": nonprofit["ntee_category"],
            "state": nonprofit["state"],
            "subsection": nonprofit["subsection"],
            "tax_deductible": nonprofit["tax_deductible"],
            "canonical_source": nonprofit["canonical_source"],
            "source_version": nonprofit["source_version"],
        },
        "filings": {
            "count": filings["count"],
            "recent_990_on_file": filings["recent_990_on_file"],
            "latest": latest_filing,
        },
        "compliance": compliance,
        "sources": sources,
        "signals": {
            "appears_because": appears_because,
            "highlights": highlights,
            "risk_indicators": risk_indicators,
            "data_gaps": data_gaps,
        },
    }


def _build_appears_because(
    nonprofit: dict[str, Any],
    filings: dict[str, Any],
    sources: list[dict[str, Any]],
) -> list[str]:
    reasons = []
    if nonprofit.get("irs_status"):
        reasons.append(f"IRS records show a status of {nonprofit['irs_status']}.")
    latest = filings.get("latest") or {}
    if latest.get("return_type") or latest.get("tax_year"):
        form_type = latest.get("return_type") or "Form 990"
        tax_year = latest.get("tax_year") or "an unknown year"
        reasons.append(f"The latest filing on record is {form_type} for tax year {tax_year}.")
    if sources:
        reasons.append(f"{len(sources)} source checks are recorded for this nonprofit.")
    else:
        reasons.append("This nonprofit currently has no supplemental source checks recorded.")
    return reasons


def _build_highlights(
    nonprofit: dict[str, Any],
    latest_filing: dict[str, Any],
    filings: dict[str, Any],
    compliance: dict[str, Any] | None,
) -> list[str]:
    highlights: list[str] = []
    if str(nonprofit.get("irs_status") or "").strip().lower() == "active":
        highlights.append("IRS records indicate the organization is active.")
    if filings.get("recent_990_on_file") is True:
        highlights.append("A recent Form 990 period is on file.")
    if str(latest_filing.get("parse_status") or "").strip().lower() == "parsed":
        highlights.append("The latest filing parsed successfully.")
    if nonprofit.get("tax_deductible") is True:
        highlights.append("The record indicates contributions are tax deductible.")
    if compliance and str(compliance.get("status") or "").strip().lower() in {"pass", "matched", "active"}:
        highlights.append(f"Latest compliance snapshot status is {compliance['status']}.")
    return highlights


def _build_risk_indicators(
    nonprofit: dict[str, Any],
    latest_filing: dict[str, Any],
    filings: dict[str, Any],
    compliance: dict[str, Any] | None,
) -> list[str]:
    indicators: list[str] = []
    irs_status = str(nonprofit.get("irs_status") or "").strip().lower()
    if irs_status and irs_status != "active":
        indicators.append(f"IRS status is {nonprofit.get('irs_status')}.")
    parse_status = str(latest_filing.get("parse_status") or "").strip().lower()
    if parse_status and parse_status != "parsed":
        indicators.append(f"Latest filing parse status is {latest_filing.get('parse_status')}.")
    if filings.get("recent_990_on_file") is False:
        indicators.append("A recent Form 990 is not currently on file.")
    if compliance and str(compliance.get("status") or "").strip().lower() not in {"pass", "matched", "active"}:
        indicators.append(f"Latest compliance snapshot status is {compliance.get('status')}.")
    return indicators


def _build_data_gaps(
    nonprofit: dict[str, Any],
    latest_filing: dict[str, Any],
    filings: dict[str, Any],
    sources: list[dict[str, Any]],
    compliance: dict[str, Any] | None,
) -> list[str]:
    gaps: list[str] = []
    if not latest_filing:
        gaps.append("No Form 990 filing has been recorded yet.")
    if not nonprofit.get("ntee_category"):
        gaps.append("NTEE classification is unavailable.")
    if not sources:
        gaps.append("No source checks are recorded yet.")
    if compliance is None:
        gaps.append("No compliance snapshot is available yet.")
    if nonprofit.get("tax_deductible") is None:
        gaps.append("Tax deductibility is not recorded.")
    if not filings.get("count"):
        gaps.append("Filing history is limited to the current dataset.")
    return gaps


def _summarize_sources(source_rows: list[Any]) -> list[dict[str, Any]]:
    latest_by_source_id: dict[str, Any] = {}
    for row in source_rows:
        source_id = str(row.source_id or "").strip()
        if not source_id or source_id in latest_by_source_id:
            continue
        latest_by_source_id[source_id] = row

    return [
        {
            "source_name": row.source_id,
            "provider_name": row.provider_name,
            "category": row.category,
            "status": row.status,
            "retrieved_at": row.retrieved_at,
            "valid_as_of": row.valid_as_of,
            "explanation": row.explanation,
        }
        for row in latest_by_source_id.values()
    ]


def _sanitize_verification_payload(payload: dict[str, Any]) -> dict[str, Any]:
    organization = dict(payload.get("organization") or {})
    verification = dict(payload.get("verification") or {})
    filing_summary = dict(payload.get("filing_summary") or {})
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
    enrichment = dict(payload.get("enrichment") or {})
    integration_evaluation = dict(payload.get("integration_evaluation") or {})
    state_compliance = payload.get("state_compliance")
    external_signals = payload.get("external_signals")

    highlights = []
    for item in evidence[:5]:
        if isinstance(item, dict):
            message = str(item.get("message") or "").strip()
            if message:
                highlights.append(message)

    return {
        "organization": organization,
        "verification": verification,
        "filing_summary": filing_summary,
        "signals": {
            "highlights": highlights,
            "data_gaps": _artifact_data_gaps(verification, filing_summary, enrichment),
        },
        "evidence": evidence,
        "enrichment": enrichment,
        "integration_evaluation": integration_evaluation,
        "state_compliance": state_compliance,
        "external_signals": external_signals,
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _artifact_data_gaps(
    verification: dict[str, Any],
    filing_summary: dict[str, Any],
    enrichment: dict[str, Any],
) -> list[str]:
    gaps: list[str] = []
    if not filing_summary:
        gaps.append("No filing summary was available when this advisory artifact was captured.")
    if not verification.get("ntee_category"):
        gaps.append("NTEE classification was unavailable when this advisory artifact was captured.")
    failures = enrichment.get("failures")
    if isinstance(failures, list) and failures:
        gaps.append("One or more enrichment providers did not return data.")
    return gaps


def _stable_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _parse_iso_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
