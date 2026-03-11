from __future__ import annotations

import json
import os

from charity_status.api import error_response, json_response
from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.providers import CandidProvider, MockProvider
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.query import AthenaQueryClient, VerificationInput, get_nonprofit_filings, verify_nonprofit
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.serving import DynamoProfileStore, materialize_profile_item
from charity_status.serving.writer import MaterializedProfileWriter

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
PROFILE_TABLE_NAME = os.environ.get("PROFILE_TABLE_NAME")
APP_ENV = os.environ.get("APP_ENV", "dev")
SERVING_DDB_ENABLED = os.environ.get("SERVING_DDB_ENABLED", "false").lower() == "true"

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


def _get_profile_store() -> DynamoProfileStore | None:
    global profile_store
    if not SERVING_DDB_ENABLED or not PROFILE_TABLE_NAME:
        return None
    if profile_store is None:
        profile_store = DynamoProfileStore(table_name=PROFILE_TABLE_NAME)
    return profile_store


def handler(event, context):
    method = (event.get("httpMethod") or "GET").upper()

    try:
        if method == "POST":
            verification_input = _parse_post_request(event)
        else:
            verification_input = _parse_get_request(event)
    except EINValidationError as exc:
        return error_response(400, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))

    try:
        normalized_ein = normalize_ein(verification_input.ein)

        if _is_filings_request(event, method):
            status_code, payload = get_nonprofit_filings(_get_athena_client(), normalized_ein)
            return json_response(status_code, payload)

        if method == "GET":
            cached = _load_cached_profile(normalized_ein)
            if cached is not None:
                return json_response(200, cached)

        verification_input = VerificationInput(
            ein=normalized_ein,
            provided_name=verification_input.provided_name,
            subsection=verification_input.subsection,
        )
        status_code, payload = verify_nonprofit(
            _get_athena_client(),
            verification_input,
            enrichment_service=_get_enrichment_service(),
        )
        if status_code == 200 and method == "GET":
            _materialize_profile(normalized_ein, payload)
        return json_response(status_code, payload)
    except EINValidationError as exc:
        return error_response(400, str(exc))
    except AthenaQueryTimeout as exc:
        return json_response(504, {"message": str(exc)})
    except AthenaQueryError:
        return error_response(500, "Internal server error")
    except Exception:
        return error_response(500, "Internal server error")


def _parse_get_request(event: dict) -> VerificationInput:
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    return VerificationInput(
        ein=path_params.get("ein") or "",
        subsection=query_params.get("subsection"),
    )


def _parse_post_request(event: dict) -> VerificationInput:
    body = event.get("body")
    if not body:
        raise ValueError("Request body is required")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON")

    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")

    ein = payload.get("ein")
    if not ein:
        raise ValueError("Request body must include ein")

    provided_name = payload.get("name")
    if provided_name is not None and not isinstance(provided_name, str):
        raise ValueError("name must be a string")

    return VerificationInput(
        ein=ein,
        provided_name=provided_name,
    )


def _is_filings_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/filings") or path.endswith("/filings")


def _load_cached_profile(ein: str) -> dict | None:
    store = _get_profile_store()
    if store is None:
        return None
    item = store.get_profile(ein)
    if not item:
        return None
    return {
        "organization": item.get("organization"),
        "verification": item.get("verification"),
        "scores": item.get("scores"),
        "score_explanation": item.get("score_explanation"),
        "model": {"version": item.get("model_version"), "source": "materialized_dynamodb"},
        "filing_summary": item.get("latest_filing"),
        "enrichment": item.get("enrichment") or {"providers": [], "failures": []},
        "decision": item.get("decision"),
        "audit": item.get("audit"),
        "summary": item.get("summary"),
    }


def _materialize_profile(ein: str, payload: dict) -> None:
    store = _get_profile_store()
    if store is None:
        return
    source_versions = {
        "model_version": payload.get("score_explanation", {}).get("model_version"),
        "score_data_sources": payload.get("score_explanation", {}).get("score_data_sources"),
    }
    item = materialize_profile_item(
        ein=ein,
        response_payload=payload,
        environment=APP_ENV,
        source_data_versions=source_versions,
    )
    MaterializedProfileWriter(store).write_if_needed(ein=ein, item=item)
