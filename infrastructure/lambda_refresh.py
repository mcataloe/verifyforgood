from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import boto3
from charity_status.core.interfaces import EnrichmentProviderGateway, ProfileStoreAdapter, QueryRepository
from charity_status.ops import S3RunStore
from charity_status.platform import (
    QueryRuntimeConfig,
    RefreshRuntimeConfig,
    build_athena_client,
    build_enrichment_service,
    load_platform_integrations_config,
)
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.query import VerificationInput, verify_nonprofit
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.serving import (
    DynamoProfileStore,
    PostIngestRefreshConfig,
    RefreshConfig,
    refresh_from_ingest_output,
    refresh_materialized_profiles,
)
from charity_status.serving.change_detection import normalize_mode, parse_explicit_eins


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() == "true"


def _env_optional_bool(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw.lower() == "true"


DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")
FORM990_FILINGS_TABLE = os.environ.get("FORM990_FILINGS_TABLE", "form990_metadata")
FORM990_METRICS_TABLE = os.environ.get("FORM990_METRICS_TABLE", "form990_metrics")
FORM990_GOVERNANCE_TABLE = os.environ.get("FORM990_GOVERNANCE_TABLE", "form990_governance")
FORM990_QUALITY_TABLE = os.environ.get("FORM990_QUALITY_TABLE", "form990_quality")

ENRICHMENT_TIMEOUT_SECONDS = int(os.environ.get("ENRICHMENT_TIMEOUT_SECONDS", "5"))
PLATFORM_INTEGRATIONS = load_platform_integrations_config(os.environ)

APP_ENV = os.environ.get("APP_ENV", "dev")
PROFILE_TABLE_NAME = os.environ.get("PROFILE_TABLE_NAME", "")
REFRESH_MODE = os.environ.get("REFRESH_MODE", "refresh_changed")
REFRESH_BATCH_SIZE = int(os.environ.get("REFRESH_BATCH_SIZE", "100"))
FORCE_REFRESH = os.environ.get("FORCE_REFRESH", "false").lower() == "true"
REFRESH_SOURCE_DETECTION_ENABLED = os.environ.get("REFRESH_SOURCE_DETECTION_ENABLED", "false").lower() == "true"
REFRESH_EINS_CSV = os.environ.get("REFRESH_EINS_CSV", "")
BOOTSTRAP_NONPROD_OVERRIDE = os.environ.get("BOOTSTRAP_NONPROD_OVERRIDE", "false").lower() == "true"
BOOTSTRAP_START_AFTER_EIN = os.environ.get("BOOTSTRAP_START_AFTER_EIN")
BOOTSTRAP_MAX_BATCHES_PER_RUN = int(os.environ.get("BOOTSTRAP_MAX_BATCHES_PER_RUN", "0"))
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()

athena_client: QueryRepository | None = None
enrichment_service: EnrichmentProviderGateway | None = None
profile_store: ProfileStoreAdapter | None = None


def _get_athena_client() -> QueryRepository:
    global athena_client
    if athena_client is None:
        athena_client = build_athena_client(
            QueryRuntimeConfig(
                database=DATABASE,
                table=TABLE,
                workgroup=WORKGROUP,
                form990_filings_table=FORM990_FILINGS_TABLE,
                form990_metrics_table=FORM990_METRICS_TABLE,
                form990_governance_table=FORM990_GOVERNANCE_TABLE,
                form990_quality_table=FORM990_QUALITY_TABLE,
            )
        )
    return athena_client


def _get_enrichment_service() -> EnrichmentProviderGateway:
    global enrichment_service
    if enrichment_service is None:
        enrichment_service = build_enrichment_service(
            RefreshRuntimeConfig(
                database=DATABASE,
                table=TABLE,
                workgroup=WORKGROUP,
                form990_filings_table=FORM990_FILINGS_TABLE,
                form990_metrics_table=FORM990_METRICS_TABLE,
                form990_governance_table=FORM990_GOVERNANCE_TABLE,
                form990_quality_table=FORM990_QUALITY_TABLE,
                platform_integrations=PLATFORM_INTEGRATIONS,
                enrichment_timeout_seconds=ENRICHMENT_TIMEOUT_SECONDS,
                enrichment_mock_offered=_env_optional_bool("ENRICHMENT_MOCK_OFFERED"),
                enrichment_mock_enabled=_env_bool("ENRICHMENT_MOCK_ENABLED"),
                enrichment_candid_offered=_env_optional_bool("ENRICHMENT_CANDID_OFFERED"),
                enrichment_candid_enabled=_env_bool("ENRICHMENT_CANDID_ENABLED"),
                enrichment_candid_api_key=os.environ.get("ENRICHMENT_CANDID_API_KEY"),
                enrichment_candid_endpoint=os.environ.get("ENRICHMENT_CANDID_ENDPOINT"),
                enrichment_state_registry_offered=_env_optional_bool("ENRICHMENT_STATE_REGISTRY_OFFERED"),
                enrichment_state_registry_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_ENABLED"),
                enrichment_state_registry_mock_enabled=_env_bool("ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED"),
                enrichment_state_registry_endpoint=os.environ.get("ENRICHMENT_STATE_REGISTRY_ENDPOINT"),
                enrichment_state_business_offered=_env_optional_bool("ENRICHMENT_STATE_BUSINESS_OFFERED"),
                enrichment_state_business_enabled=_env_bool("ENRICHMENT_STATE_BUSINESS_ENABLED"),
                enrichment_state_business_mock_enabled=_env_bool("ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED"),
                enrichment_state_business_endpoint=os.environ.get("ENRICHMENT_STATE_BUSINESS_ENDPOINT"),
                enrichment_usaspending_offered=_env_optional_bool("ENRICHMENT_USASPENDING_OFFERED"),
                enrichment_usaspending_enabled=_env_bool("ENRICHMENT_USASPENDING_ENABLED"),
                enrichment_usaspending_mock_enabled=_env_bool("ENRICHMENT_USASPENDING_MOCK_ENABLED"),
                enrichment_usaspending_endpoint=os.environ.get("ENRICHMENT_USASPENDING_ENDPOINT"),
                enrichment_ofac_offered=_env_optional_bool("ENRICHMENT_OFAC_OFFERED"),
                enrichment_ofac_enabled=_env_bool("ENRICHMENT_OFAC_ENABLED"),
                enrichment_ofac_mock_enabled=_env_bool("ENRICHMENT_OFAC_MOCK_ENABLED"),
                enrichment_ofac_endpoint=os.environ.get("ENRICHMENT_OFAC_ENDPOINT"),
            )
        )
    return enrichment_service


def _get_profile_store() -> ProfileStoreAdapter:
    global profile_store
    if profile_store is None:
        profile_store = DynamoProfileStore(table_name=PROFILE_TABLE_NAME)
    return profile_store


def handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    del context
    payload = event if isinstance(event, dict) else {}
    explicit_eins = _build_explicit_ein_list(payload)
    config = _build_refresh_config(payload)

    if not PROFILE_TABLE_NAME:
        return _response(500, {"message": "PROFILE_TABLE_NAME is required"})

    try:
        if str(payload.get("mode") or "").strip().lower() == "post_ingest_refresh":
            ingest_output = payload.get("ingest_output")
            if not isinstance(ingest_output, dict):
                return _response(400, {"message": "ingest_output object is required for post_ingest_refresh mode"})
            result = refresh_from_ingest_output(
                config=PostIngestRefreshConfig(environment=APP_ENV),
                ingest_output=ingest_output,
                store=_get_profile_store(),
                profile_builder=_build_profile_for_ein,
                refresh_run_id=(str(payload.get("refresh_run_id")).strip() if payload.get("refresh_run_id") else None),
            )
            _persist_refresh_ops_run(result)
            return _response(200, result)

        result = refresh_materialized_profiles(
            config=config,
            explicit_eins=explicit_eins,
            store=_get_profile_store(),
            profile_builder=_build_profile_for_ein,
            source_detector=lambda: _source_changed_eins(payload),
            source_page_fetcher=_source_population_page,
            bootstrap_start_after=_bootstrap_start_cursor(payload),
        )
        _persist_refresh_ops_run(_normalize_refresh_result(result))
        return _response(200, result)
    except (ValueError, EINValidationError) as exc:
        return _response(400, {"message": str(exc)})
    except AthenaQueryTimeout as exc:
        return _response(504, {"message": str(exc)})
    except AthenaQueryError as exc:
        return _response(502, {"message": str(exc)})


def _build_refresh_config(payload: dict[str, Any]) -> RefreshConfig:
    mode = normalize_mode(str(payload.get("mode") or REFRESH_MODE))
    batch_size = int(payload.get("batch_size") or REFRESH_BATCH_SIZE)
    force_refresh = bool(payload.get("force_refresh", FORCE_REFRESH))
    source_detection_enabled = bool(payload.get("source_detection_enabled", REFRESH_SOURCE_DETECTION_ENABLED))
    allow_nonprod_bootstrap_override = bool(payload.get("bootstrap_nonprod_override", BOOTSTRAP_NONPROD_OVERRIDE))
    max_batches_per_run = int(payload.get("max_batches_per_run", BOOTSTRAP_MAX_BATCHES_PER_RUN))
    return RefreshConfig(
        environment=APP_ENV,
        mode=mode,
        batch_size=batch_size,
        force_refresh=force_refresh,
        source_detection_enabled=source_detection_enabled,
        allow_nonprod_bootstrap_override=allow_nonprod_bootstrap_override,
        max_batches_per_run=max_batches_per_run if max_batches_per_run > 0 else None,
    )


def _build_explicit_ein_list(payload: dict[str, Any]) -> list[str]:
    from_event = parse_explicit_eins(payload)
    if from_event:
        return [normalize_ein(ein) for ein in from_event]

    if REFRESH_EINS_CSV.strip():
        return [normalize_ein(part) for part in REFRESH_EINS_CSV.split(",") if part.strip()]

    return []


def _source_changed_eins(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("changed_eins")
    if isinstance(raw, list):
        return [normalize_ein(str(ein)) for ein in raw]
    return []


def _build_profile_for_ein(ein: str) -> dict[str, Any] | None:
    status_code, profile = verify_nonprofit(
        _get_athena_client(),
        VerificationInput(ein=ein),
        enrichment_service=_get_enrichment_service(),
    )
    if status_code != 200:
        return None
    return profile


def _bootstrap_start_cursor(payload: dict[str, Any]) -> str | None:
    start_after = payload.get("start_after_ein")
    if isinstance(start_after, str) and start_after.strip():
        return normalize_ein(start_after)
    if BOOTSTRAP_START_AFTER_EIN:
        return normalize_ein(BOOTSTRAP_START_AFTER_EIN)
    return None


def _source_population_page(start_after: str | None, page_size: int) -> tuple[list[str], str | None]:
    eins = _get_athena_client().list_nonprofit_eins_page(limit=page_size, start_after_ein=start_after)
    next_cursor = eins[-1] if len(eins) == page_size else None
    return eins, next_cursor


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _persist_refresh_ops_run(result: dict[str, Any]) -> None:
    if not OPS_METADATA_BUCKET:
        return
    run_id = str(result.get("refresh_run_id") or f"refresh_{result.get('mode')}_{result.get('started_at') or ''}")
    s3 = boto3.client("s3")
    store = S3RunStore(bucket=OPS_METADATA_BUCKET, prefix=OPS_METADATA_PREFIX, s3_client=s3)
    summary = {
        "refresh_run_id": run_id,
        "source_ingest_run_id": result.get("ingest_run_id"),
        "started_at": result.get("started_at"),
        "completed_at": result.get("completed_at"),
        "status": result.get("status") or ("completed_with_errors" if int(result.get("failed_count") or 0) > 0 else "completed"),
        "affected_ein_count": result.get("affected_ein_count") or result.get("selected") or result.get("total_seen") or 0,
        "refreshed_count": result.get("refreshed_count") or result.get("written") or result.get("updated") or 0,
        "unchanged_count": result.get("unchanged_count") or result.get("skipped") or 0,
        "failed_count": result.get("failed_count") or result.get("failed") or 0,
        "materialized_profiles_updated": result.get("refreshed_count") or result.get("written") or 0,
        "change_events_emitted": len(result.get("change_events") or []),
        "safe_error_summary": {"count": len(result.get("errors") or []), "samples": (result.get("errors") or [])[:10]},
        "mode": result.get("mode"),
    }
    store.write_refresh_run(run_id, summary)
    eins = result.get("results") or []
    if isinstance(eins, list):
        store.write_refresh_eins(run_id, [item for item in eins if isinstance(item, dict)])


def _normalize_refresh_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "refresh_run_id": result.get("refresh_run_id") or f"refresh_{(result.get('mode') or 'run')}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        "started_at": result.get("started_at"),
        "completed_at": result.get("completed_at"),
        "status": result.get("status"),
        "mode": result.get("mode"),
        "selected": result.get("selected"),
        "written": result.get("written"),
        "skipped": result.get("skipped"),
        "failed": result.get("failed"),
        "change_events": result.get("change_events") or [],
        "errors": result.get("errors") or [],
    }
