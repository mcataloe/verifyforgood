from __future__ import annotations

import json
import os
from typing import Any

from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.providers import CandidProvider, MockProvider
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.query import AthenaQueryClient, VerificationInput, verify_nonprofit
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.serving import DynamoProfileStore, RefreshConfig, refresh_materialized_profiles
from charity_status.serving.change_detection import normalize_mode, parse_explicit_eins

DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")
FORM990_FILINGS_TABLE = os.environ.get("FORM990_FILINGS_TABLE", "form990_metadata")
FORM990_METRICS_TABLE = os.environ.get("FORM990_METRICS_TABLE", "form990_metrics")
FORM990_GOVERNANCE_TABLE = os.environ.get("FORM990_GOVERNANCE_TABLE", "form990_governance")
FORM990_QUALITY_TABLE = os.environ.get("FORM990_QUALITY_TABLE", "form990_quality")

ENRICHMENT_MOCK_ENABLED = os.environ.get("ENRICHMENT_MOCK_ENABLED", "false").lower() == "true"
ENRICHMENT_CANDID_ENABLED = os.environ.get("ENRICHMENT_CANDID_ENABLED", "false").lower() == "true"
ENRICHMENT_CANDID_API_KEY = os.environ.get("ENRICHMENT_CANDID_API_KEY")
ENRICHMENT_CANDID_ENDPOINT = os.environ.get("ENRICHMENT_CANDID_ENDPOINT")
ENRICHMENT_TIMEOUT_SECONDS = int(os.environ.get("ENRICHMENT_TIMEOUT_SECONDS", "5"))

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

athena_client: AthenaQueryClient | None = None
enrichment_service: EnrichmentService | None = None
profile_store: DynamoProfileStore | None = None


def _get_athena_client() -> AthenaQueryClient:
    global athena_client
    if athena_client is None:
        athena_client = AthenaQueryClient(
            database=DATABASE,
            table=TABLE,
            workgroup=WORKGROUP,
            form990_filings_table=FORM990_FILINGS_TABLE,
            form990_metrics_table=FORM990_METRICS_TABLE,
            form990_governance_table=FORM990_GOVERNANCE_TABLE,
            form990_quality_table=FORM990_QUALITY_TABLE,
        )
    return athena_client


def _get_enrichment_service() -> EnrichmentService:
    global enrichment_service
    if enrichment_service is None:
        registry = ProviderRegistry(
            providers=[
                MockProvider(enabled=ENRICHMENT_MOCK_ENABLED),
                CandidProvider(
                    enabled=ENRICHMENT_CANDID_ENABLED,
                    api_key=ENRICHMENT_CANDID_API_KEY,
                    endpoint=ENRICHMENT_CANDID_ENDPOINT,
                    timeout_seconds=ENRICHMENT_TIMEOUT_SECONDS,
                ),
            ]
        )
        enrichment_service = EnrichmentService(registry=registry)
    return enrichment_service


def _get_profile_store() -> DynamoProfileStore:
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
        result = refresh_materialized_profiles(
            config=config,
            explicit_eins=explicit_eins,
            store=_get_profile_store(),
            profile_builder=_build_profile_for_ein,
            source_detector=lambda: _source_changed_eins(payload),
            source_page_fetcher=_source_population_page,
            bootstrap_start_after=_bootstrap_start_cursor(payload),
        )
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
