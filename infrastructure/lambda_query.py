from __future__ import annotations

import json
import logging
import os
from collections import Counter
from typing import Any

from charity_status.api import error_response, json_response
from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.providers import CandidProvider, MockProvider
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.policy import evaluate_policy
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
BATCH_VERIFY_MAX_SIZE = int(os.environ.get("BATCH_VERIFY_MAX_SIZE", "25"))

athena_client: AthenaQueryClient | None = None
enrichment_service: EnrichmentService | None = None
profile_store: DynamoProfileStore | None = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
    if method == "POST" and _is_batch_verify_request(event):
        return _handle_batch_verify(event)

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
            policy_id=verification_input.policy_id,
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
        logger.exception("Athena query error")
        return error_response(500, "Internal server error")
    except Exception:
        logger.exception("Unhandled exception in lambda_query handler")
        return error_response(500, "Internal server error")


def _parse_get_request(event: dict) -> VerificationInput:
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    return VerificationInput(
        ein=path_params.get("ein") or "",
        subsection=query_params.get("subsection"),
        policy_id=None,
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
    policy_id = payload.get("policy_id")
    if policy_id is not None and not isinstance(policy_id, str):
        raise ValueError("policy_id must be a string")

    return VerificationInput(
        ein=ein,
        provided_name=provided_name,
        policy_id=policy_id,
    )


def _is_filings_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/filings") or path.endswith("/filings")


def _is_batch_verify_request(event: dict) -> bool:
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/verify/batch") or path.endswith("/verify/batch")


def _handle_batch_verify(event: dict) -> dict[str, Any]:
    try:
        body = event.get("body")
        if not body:
            return error_response(400, "Request body is required")
        payload = json.loads(body)
    except json.JSONDecodeError:
        return error_response(400, "Request body must be valid JSON")

    items_input: list[Any]
    if isinstance(payload, list):
        items_input = payload
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        items_input = payload["items"]
    else:
        return error_response(400, "Request body must be an array or an object with items[]")

    if len(items_input) > BATCH_VERIFY_MAX_SIZE:
        return error_response(400, f"Batch size exceeds maximum of {BATCH_VERIFY_MAX_SIZE}")

    results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()

    for index, row in enumerate(items_input):
        item_result = _process_batch_item(index, row)
        results.append(item_result)
        status_counts[item_result["status"]] += 1
        if item_result["status"] == "ok":
            decision_counts[item_result.get("decision_status") or "unknown"] += 1
        else:
            error_counts[item_result.get("error_code") or "unknown_error"] += 1

    summary = {
        "total": len(items_input),
        "success": status_counts.get("ok", 0),
        "error": status_counts.get("error", 0),
        "counts_by_status": dict(status_counts),
        "counts_by_decision": dict(decision_counts),
        "counts_by_error": dict(error_counts),
        "max_batch_size": BATCH_VERIFY_MAX_SIZE,
    }
    return json_response(200, {"batch_summary": summary, "items": results})


def _process_batch_item(index: int, row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"index": index, "status": "error", "error_code": "invalid_item", "message": "Item must be an object"}

    ein = row.get("ein")
    if not ein:
        return {"index": index, "status": "error", "error_code": "missing_ein", "message": "Item must include ein"}

    provided_name = row.get("name")
    if provided_name is not None and not isinstance(provided_name, str):
        return {"index": index, "status": "error", "error_code": "invalid_name", "message": "name must be a string"}

    policy_id = row.get("policy_id")
    if policy_id is not None and not isinstance(policy_id, str):
        return {"index": index, "status": "error", "error_code": "invalid_policy_id", "message": "policy_id must be a string"}

    try:
        normalized_ein = normalize_ein(str(ein))
        payload = _verify_single_item(normalized_ein, provided_name, policy_id)
        return {
            "index": index,
            "ein": normalized_ein,
            "status": "ok",
            "decision_status": (payload.get("decision") or {}).get("status"),
            "final_recommendation": payload.get("final_recommendation"),
            "item": payload,
        }
    except EINValidationError as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "invalid_ein", "message": str(exc)}
    except ValueError as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "invalid_policy", "message": str(exc)}
    except AthenaQueryTimeout as exc:
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "athena_timeout", "message": str(exc)}
    except AthenaQueryError:
        logger.exception("Athena query error while processing batch item")
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "athena_error", "message": "Athena query failed"}
    except Exception:
        logger.exception("Unhandled exception while processing batch item")
        return {"index": index, "ein": str(ein), "status": "error", "error_code": "internal_error", "message": "Internal server error"}


def _verify_single_item(normalized_ein: str, provided_name: str | None, policy_id: str | None) -> dict[str, Any]:
    if provided_name is None:
        cached = _load_cached_profile(normalized_ein)
        if cached is not None:
            if policy_id:
                cached["policy_evaluation"] = evaluate_policy(cached, policy_id)
                cached["final_recommendation"] = cached["policy_evaluation"]["final_recommendation"]
            return cached

    verification_input = VerificationInput(
        ein=normalized_ein,
        provided_name=provided_name,
        policy_id=policy_id,
    )
    status_code, payload = verify_nonprofit(
        _get_athena_client(),
        verification_input,
        enrichment_service=_get_enrichment_service(),
    )
    if status_code != 200:
        raise ValueError(payload.get("message") or "Verification failed")
    return payload


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
        "evidence": item.get("evidence"),
        "policy_evaluation": item.get("policy_evaluation"),
        "final_recommendation": item.get("final_recommendation") or item.get("decision", {}).get("status"),
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
