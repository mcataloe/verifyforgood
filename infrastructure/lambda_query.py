from __future__ import annotations

import json
import logging
import os
from collections import Counter
from typing import Any

import boto3
from charity_status.api import error_response, json_response
from charity_status.auth import AuthenticationError, AuthorizationError, InMemoryUsageStore, QuotaExceededError
from charity_status.core.hooks import NoopAuthContextProvider, NoopQuotaMeteringHook
from charity_status.core.interfaces import AuthContextProvider, EnrichmentProviderGateway, ProfileStoreAdapter, QueryRepository, QuotaMeteringHook
from charity_status.enrichments import EvaluationContext, TenantIntegrationSettingsResolver, load_tenant_integration_settings
from charity_status.enrichments.compliance import extract_state_compliance
from charity_status.enrichments.external_signals import extract_external_signals
from charity_status.platform import (
    ApiKeyAuthContextProvider,
    ApiKeyOrOAuthAuthContextProvider,
    ApiKeyQuotaMeteringHook,
    QueryRuntimeConfig,
    RefreshRuntimeConfig,
    build_athena_client,
    build_enrichment_service,
    load_api_key_store,
    load_oauth_token_store,
)
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.policy import evaluate_policy
from charity_status.query import VerificationInput, apply_evaluation_overlay, get_nonprofit_filings, search_nonprofit_summaries, verify_nonprofit
from charity_status.query.ops_views import (
    get_ingest_run,
    get_ingest_run_filings,
    get_nonprofit_pipeline_status,
    get_refresh_run,
    get_refresh_run_eins,
    list_ingest_runs,
    list_refresh_runs,
)
from charity_status.query.source_views import (
    get_nonprofit_compliance_view,
    get_nonprofit_federal_awards_view,
    get_nonprofit_single_source_view,
    get_nonprofit_sources_view,
)
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.serving import DynamoProfileStore, materialize_profile_item
from charity_status.serving.writer import MaterializedProfileWriter


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

ENRICHMENT_MOCK_OFFERED = _env_optional_bool("ENRICHMENT_MOCK_OFFERED")
ENRICHMENT_MOCK_ENABLED = _env_bool("ENRICHMENT_MOCK_ENABLED")
ENRICHMENT_CANDID_OFFERED = _env_optional_bool("ENRICHMENT_CANDID_OFFERED")
ENRICHMENT_CANDID_ENABLED = _env_bool("ENRICHMENT_CANDID_ENABLED")
ENRICHMENT_CANDID_API_KEY = os.environ.get("ENRICHMENT_CANDID_API_KEY")
ENRICHMENT_CANDID_ENDPOINT = os.environ.get("ENRICHMENT_CANDID_ENDPOINT")
ENRICHMENT_TIMEOUT_SECONDS = int(os.environ.get("ENRICHMENT_TIMEOUT_SECONDS", "5"))
ENRICHMENT_STATE_REGISTRY_OFFERED = _env_optional_bool("ENRICHMENT_STATE_REGISTRY_OFFERED")
ENRICHMENT_STATE_REGISTRY_ENABLED = _env_bool("ENRICHMENT_STATE_REGISTRY_ENABLED")
ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED = _env_bool("ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED")
ENRICHMENT_STATE_REGISTRY_ENDPOINT = os.environ.get("ENRICHMENT_STATE_REGISTRY_ENDPOINT")
ENRICHMENT_STATE_BUSINESS_OFFERED = _env_optional_bool("ENRICHMENT_STATE_BUSINESS_OFFERED")
ENRICHMENT_STATE_BUSINESS_ENABLED = _env_bool("ENRICHMENT_STATE_BUSINESS_ENABLED")
ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED = _env_bool("ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED")
ENRICHMENT_STATE_BUSINESS_ENDPOINT = os.environ.get("ENRICHMENT_STATE_BUSINESS_ENDPOINT")
ENRICHMENT_USASPENDING_OFFERED = _env_optional_bool("ENRICHMENT_USASPENDING_OFFERED")
ENRICHMENT_USASPENDING_ENABLED = _env_bool("ENRICHMENT_USASPENDING_ENABLED")
ENRICHMENT_USASPENDING_MOCK_ENABLED = _env_bool("ENRICHMENT_USASPENDING_MOCK_ENABLED")
ENRICHMENT_USASPENDING_ENDPOINT = os.environ.get("ENRICHMENT_USASPENDING_ENDPOINT")
ENRICHMENT_OFAC_OFFERED = _env_optional_bool("ENRICHMENT_OFAC_OFFERED")
ENRICHMENT_OFAC_ENABLED = _env_bool("ENRICHMENT_OFAC_ENABLED")
ENRICHMENT_OFAC_MOCK_ENABLED = _env_bool("ENRICHMENT_OFAC_MOCK_ENABLED")
ENRICHMENT_OFAC_ENDPOINT = os.environ.get("ENRICHMENT_OFAC_ENDPOINT")
PROFILE_TABLE_NAME = os.environ.get("PROFILE_TABLE_NAME")
APP_ENV = os.environ.get("APP_ENV", "dev")
SERVING_DDB_ENABLED = _env_bool("SERVING_DDB_ENABLED")
BATCH_VERIFY_MAX_SIZE = int(os.environ.get("BATCH_VERIFY_MAX_SIZE", "25"))
SEARCH_MAX_LIMIT = int(os.environ.get("SEARCH_MAX_LIMIT", "50"))
SEARCH_DEFAULT_LIMIT = int(os.environ.get("SEARCH_DEFAULT_LIMIT", "20"))
API_AUTH_ENABLED = _env_bool("API_AUTH_ENABLED")
API_KEY_RECORDS_JSON = os.environ.get("API_KEY_RECORDS_JSON", "")
OAUTH_M2M_ENABLED = _env_bool("OAUTH_M2M_ENABLED")
OAUTH_TOKEN_RECORDS_JSON = os.environ.get("OAUTH_TOKEN_RECORDS_JSON", "")
OPS_METADATA_BUCKET = os.environ.get("OPS_METADATA_BUCKET", "").strip()
OPS_METADATA_PREFIX = os.environ.get("OPS_METADATA_PREFIX", "ops").strip()
TENANT_INTEGRATION_SETTINGS_JSON = os.environ.get("TENANT_INTEGRATION_SETTINGS_JSON", "")

athena_client: QueryRepository | None = None
enrichment_service: EnrichmentProviderGateway | None = None
profile_store: ProfileStoreAdapter | None = None
auth_context_provider: AuthContextProvider | None = None
quota_metering_hook: QuotaMeteringHook | None = None
usage_store: InMemoryUsageStore | None = None
ops_run_store: Any | None = None
tenant_integration_settings_resolver: TenantIntegrationSettingsResolver | None = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
                enrichment_mock_offered=ENRICHMENT_MOCK_OFFERED,
                enrichment_mock_enabled=ENRICHMENT_MOCK_ENABLED,
                enrichment_candid_offered=ENRICHMENT_CANDID_OFFERED,
                enrichment_candid_enabled=ENRICHMENT_CANDID_ENABLED,
                enrichment_candid_api_key=ENRICHMENT_CANDID_API_KEY,
                enrichment_candid_endpoint=ENRICHMENT_CANDID_ENDPOINT,
                enrichment_timeout_seconds=ENRICHMENT_TIMEOUT_SECONDS,
                enrichment_state_registry_offered=ENRICHMENT_STATE_REGISTRY_OFFERED,
                enrichment_state_registry_enabled=ENRICHMENT_STATE_REGISTRY_ENABLED,
                enrichment_state_registry_mock_enabled=ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED,
                enrichment_state_registry_endpoint=ENRICHMENT_STATE_REGISTRY_ENDPOINT,
                enrichment_state_business_offered=ENRICHMENT_STATE_BUSINESS_OFFERED,
                enrichment_state_business_enabled=ENRICHMENT_STATE_BUSINESS_ENABLED,
                enrichment_state_business_mock_enabled=ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED,
                enrichment_state_business_endpoint=ENRICHMENT_STATE_BUSINESS_ENDPOINT,
                enrichment_usaspending_offered=ENRICHMENT_USASPENDING_OFFERED,
                enrichment_usaspending_enabled=ENRICHMENT_USASPENDING_ENABLED,
                enrichment_usaspending_mock_enabled=ENRICHMENT_USASPENDING_MOCK_ENABLED,
                enrichment_usaspending_endpoint=ENRICHMENT_USASPENDING_ENDPOINT,
                enrichment_ofac_offered=ENRICHMENT_OFAC_OFFERED,
                enrichment_ofac_enabled=ENRICHMENT_OFAC_ENABLED,
                enrichment_ofac_mock_enabled=ENRICHMENT_OFAC_MOCK_ENABLED,
                enrichment_ofac_endpoint=ENRICHMENT_OFAC_ENDPOINT,
            )
        )
    return enrichment_service


def _get_profile_store() -> ProfileStoreAdapter | None:
    global profile_store
    if not SERVING_DDB_ENABLED or not PROFILE_TABLE_NAME:
        return None
    if profile_store is None:
        profile_store = DynamoProfileStore(table_name=PROFILE_TABLE_NAME)
    return profile_store


def _get_auth_context_provider() -> AuthContextProvider:
    global auth_context_provider
    if auth_context_provider is None:
        if API_AUTH_ENABLED:
            api_key_store = load_api_key_store(API_KEY_RECORDS_JSON)
            if OAUTH_M2M_ENABLED:
                auth_context_provider = ApiKeyOrOAuthAuthContextProvider(
                    api_key_store=api_key_store,
                    oauth_store=load_oauth_token_store(OAUTH_TOKEN_RECORDS_JSON),
                )
            else:
                auth_context_provider = ApiKeyAuthContextProvider(api_key_store)
        else:
            auth_context_provider = NoopAuthContextProvider()
    return auth_context_provider


def _get_quota_metering_hook() -> QuotaMeteringHook:
    global quota_metering_hook, usage_store
    if quota_metering_hook is None:
        if API_AUTH_ENABLED:
            usage_store = usage_store or InMemoryUsageStore()
            quota_metering_hook = ApiKeyQuotaMeteringHook(usage_store=usage_store)
        else:
            quota_metering_hook = NoopQuotaMeteringHook()
    return quota_metering_hook


def _get_ops_run_store() -> Any | None:
    global ops_run_store
    if not OPS_METADATA_BUCKET:
        return None
    if ops_run_store is None:
        ops_run_store = S3RunStore(bucket=OPS_METADATA_BUCKET, prefix=OPS_METADATA_PREFIX, s3_client=boto3.client("s3"))
    return ops_run_store


def _get_tenant_integration_settings_resolver() -> TenantIntegrationSettingsResolver:
    global tenant_integration_settings_resolver
    if tenant_integration_settings_resolver is None:
        tenant_integration_settings_resolver = load_tenant_integration_settings(TENANT_INTEGRATION_SETTINGS_JSON)
    return tenant_integration_settings_resolver


def _resolve_evaluation_context(auth_context: Any) -> EvaluationContext:
    return _get_tenant_integration_settings_resolver().resolve(
        workspace_id=getattr(auth_context, "workspace_id", None),
        account_id=getattr(auth_context, "account_id", None),
    )


def handler(event, context):
    route_key = _route_key(event or {})
    try:
        auth_context = _get_auth_context_provider().extract_context(event or {})
        _get_quota_metering_hook().on_request(auth_context, route_key)
    except AuthenticationError as exc:
        return error_response(exc.status_code, str(exc))
    except AuthorizationError as exc:
        return error_response(exc.status_code, str(exc))
    except QuotaExceededError as exc:
        return error_response(exc.status_code, str(exc))
    evaluation_context = _resolve_evaluation_context(auth_context)
    method = (event.get("httpMethod") or "GET").upper()
    if _is_ops_request(event, method):
        status_code, payload = _handle_ops_request(event)
        response = json_response(status_code, payload)
        _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
        return response
    if method == "POST" and _is_batch_verify_request(event):
        response = _handle_batch_verify(event, evaluation_context=evaluation_context)
        try:
            body = json.loads(response.get("body") or "{}")
            total = ((body.get("batch_summary") or {}).get("total"))
            if isinstance(total, int):
                auth_context.metadata["batch_items_count"] = str(total)
        except Exception:
            pass
        _get_quota_metering_hook().on_response(auth_context, route_key, int(response.get("statusCode") or 500))
        return response

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
        if _is_search_request(event, method):
            status_code, payload = _handle_search_request(event)
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        normalized_ein = normalize_ein(verification_input.ein)
        if _is_sources_list_request(event, method):
            status_code, payload = get_nonprofit_sources_view(
                _get_athena_client(),
                _get_enrichment_service(),
                normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_sources_detail_request(event, method):
            source_name = _extract_source_name(event)
            status_code, payload = get_nonprofit_single_source_view(
                _get_athena_client(),
                _get_enrichment_service(),
                normalized_ein,
                source_name=source_name,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_compliance_request(event, method):
            status_code, payload = get_nonprofit_compliance_view(
                _get_athena_client(),
                _get_enrichment_service(),
                normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response
        if _is_federal_awards_request(event, method):
            status_code, payload = get_nonprofit_federal_awards_view(
                _get_athena_client(),
                _get_enrichment_service(),
                normalized_ein,
                subsection=verification_input.subsection,
                evaluation_context=evaluation_context,
            )
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        if _is_filings_request(event, method):
            status_code, payload = get_nonprofit_filings(_get_athena_client(), normalized_ein)
            response = json_response(status_code, payload)
            _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
            return response

        if method == "GET":
            cached = _load_cached_profile(normalized_ein)
            if cached is not None:
                if policy_id_required(verification_input) or evaluation_context.has_non_default_integrations() or not cached.get("integration_evaluation"):
                    cached = apply_evaluation_overlay(
                        payload=cached,
                        policy_id=verification_input.policy_id,
                        enrichment_service=_get_enrichment_service(),
                        evaluation_context=evaluation_context,
                        ein=normalized_ein,
                    )
                response = json_response(200, cached)
                _get_quota_metering_hook().on_response(auth_context, route_key, 200)
                return response

        verification_input = VerificationInput(
            ein=normalized_ein,
            provided_name=verification_input.provided_name,
            subsection=verification_input.subsection,
            policy_id=verification_input.policy_id,
            weighting_profile=verification_input.weighting_profile,
        )
        status_code, payload = verify_nonprofit(
            _get_athena_client(),
            verification_input,
            enrichment_service=_get_enrichment_service(),
            evaluation_context=evaluation_context,
        )
        if status_code == 200 and method == "GET" and not evaluation_context.has_non_default_integrations():
            _materialize_profile(normalized_ein, payload)
        response = json_response(status_code, payload)
        _get_quota_metering_hook().on_response(auth_context, route_key, status_code)
        return response
    except EINValidationError as exc:
        response = error_response(400, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, 400)
        return response
    except ValueError as exc:
        response = error_response(400, str(exc))
        _get_quota_metering_hook().on_response(auth_context, route_key, 400)
        return response
    except AthenaQueryTimeout as exc:
        response = json_response(504, {"message": str(exc)})
        _get_quota_metering_hook().on_response(auth_context, route_key, 504)
        return response
    except AthenaQueryError:
        logger.exception("Athena query error")
        response = error_response(500, "Internal server error")
        _get_quota_metering_hook().on_response(auth_context, route_key, 500)
        return response
    except Exception:
        logger.exception("Unhandled exception in lambda_query handler")
        response = error_response(500, "Internal server error")
        _get_quota_metering_hook().on_response(auth_context, route_key, 500)
        return response


def _parse_get_request(event: dict) -> VerificationInput:
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    return VerificationInput(
        ein=path_params.get("ein") or "",
        subsection=query_params.get("subsection"),
        policy_id=None,
        weighting_profile=(query_params.get("weighting_profile") if query_params else None),
    )


def _route_key(event: dict[str, Any]) -> str:
    method = str(event.get("httpMethod") or "GET").upper()
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return f"{method} {resource or path or '/'}"


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
    weighting_profile = payload.get("weighting_profile")
    if weighting_profile is not None and not isinstance(weighting_profile, str):
        raise ValueError("weighting_profile must be a string")

    return VerificationInput(
        ein=ein,
        provided_name=provided_name,
        policy_id=policy_id,
        weighting_profile=weighting_profile,
    )


def _is_filings_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/filings") or path.endswith("/filings")


def _is_search_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/nonprofits/search") or path.endswith("/nonprofits/search")


def _is_batch_verify_request(event: dict) -> bool:
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/verify/batch") or path.endswith("/verify/batch")


def _is_ops_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.startswith("/ops/") or path.startswith("/ops/")


def _handle_ops_request(event: dict) -> tuple[int, dict[str, Any]]:
    run_store = _get_ops_run_store()
    if run_store is None:
        return 503, {"message": "Operational run store not configured"}
    resource = str(event.get("resource") or "")
    path_params = event.get("pathParameters") or {}
    query = event.get("queryStringParameters") or {}
    try:
        limit = int(str(query.get("limit"))) if query.get("limit") else 50
    except ValueError:
        return 400, {"message": "limit must be an integer"}

    if resource.endswith("/ops/ingest/runs"):
        return list_ingest_runs(run_store, limit=limit)
    if resource.endswith("/ops/ingest/runs/{ingest_run_id}"):
        return get_ingest_run(run_store, str(path_params.get("ingest_run_id") or ""))
    if resource.endswith("/ops/ingest/runs/{ingest_run_id}/filings"):
        return get_ingest_run_filings(run_store, str(path_params.get("ingest_run_id") or ""))
    if resource.endswith("/ops/refresh/runs"):
        return list_refresh_runs(run_store, limit=limit)
    if resource.endswith("/ops/refresh/runs/{refresh_run_id}"):
        return get_refresh_run(run_store, str(path_params.get("refresh_run_id") or ""))
    if resource.endswith("/ops/refresh/runs/{refresh_run_id}/eins"):
        return get_refresh_run_eins(run_store, str(path_params.get("refresh_run_id") or ""))
    if resource.endswith("/ops/nonprofits/{ein}/pipeline-status"):
        ein = str(path_params.get("ein") or "")
        return get_nonprofit_pipeline_status(run_store, _get_profile_store(), ein)
    return 404, {"message": "Ops route not found"}


def _is_sources_list_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/nonprofits/{ein}/sources") or path.endswith("/sources")


def _is_sources_detail_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/nonprofits/{ein}/sources/{source_name}") or "/sources/" in path


def _is_compliance_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/nonprofits/{ein}/compliance") or path.endswith("/compliance")


def _is_federal_awards_request(event: dict, method: str) -> bool:
    if method != "GET":
        return False
    resource = str(event.get("resource") or "")
    path = str(event.get("path") or "")
    return resource.endswith("/nonprofits/{ein}/federal-awards") or path.endswith("/federal-awards")


def _extract_source_name(event: dict) -> str:
    path_params = event.get("pathParameters") or {}
    direct = path_params.get("source_name")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    path = str(event.get("path") or "")
    marker = "/sources/"
    if marker in path:
        return path.split(marker, 1)[1].strip("/")
    raise ValueError("source_name is required")


def _handle_search_request(event: dict) -> tuple[int, dict[str, Any]]:
    query = event.get("queryStringParameters") or {}
    name_query = str(query.get("q") or query.get("name") or "").strip()
    if not name_query:
        raise ValueError("Search query parameter q is required")
    if len(name_query) < 2:
        raise ValueError("Search query must be at least 2 characters")

    limit = SEARCH_DEFAULT_LIMIT
    if query.get("limit") is not None:
        try:
            limit = int(str(query.get("limit")))
        except ValueError as exc:
            raise ValueError("limit must be an integer") from exc
    if limit < 1 or limit > SEARCH_MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {SEARCH_MAX_LIMIT}")

    active_only = _parse_bool(query.get("active_only"), default=False)
    state = str(query.get("state")).strip().upper() if query.get("state") else None
    subsection = str(query.get("subsection")).strip() if query.get("subsection") else None
    cursor = str(query.get("cursor")).strip() if query.get("cursor") else None

    return search_nonprofit_summaries(
        client=_get_athena_client(),
        name_query=name_query,
        limit=limit,
        state=state,
        subsection=subsection,
        active_only=active_only,
        cursor=cursor,
    )


def _handle_batch_verify(event: dict, evaluation_context: EvaluationContext) -> dict[str, Any]:
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
        item_result = _process_batch_item(index, row, evaluation_context=evaluation_context)
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


def _process_batch_item(index: int, row: Any, evaluation_context: EvaluationContext) -> dict[str, Any]:
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
    weighting_profile = row.get("weighting_profile")
    if weighting_profile is not None and not isinstance(weighting_profile, str):
        return {"index": index, "status": "error", "error_code": "invalid_weighting_profile", "message": "weighting_profile must be a string"}

    try:
        normalized_ein = normalize_ein(str(ein))
        payload = _verify_single_item(normalized_ein, provided_name, policy_id, weighting_profile, evaluation_context)
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


def _verify_single_item(
    normalized_ein: str,
    provided_name: str | None,
    policy_id: str | None,
    weighting_profile: str | None = None,
    evaluation_context: EvaluationContext | None = None,
) -> dict[str, Any]:
    context = evaluation_context or EvaluationContext()
    if provided_name is None:
        cached = _load_cached_profile(normalized_ein)
        if cached is not None:
            if policy_id or context.has_non_default_integrations() or not cached.get("integration_evaluation"):
                cached = apply_evaluation_overlay(
                    payload=cached,
                    policy_id=policy_id,
                    enrichment_service=_get_enrichment_service(),
                    evaluation_context=context,
                    ein=normalized_ein,
                )
            return cached

    verification_input = VerificationInput(
        ein=normalized_ein,
        provided_name=provided_name,
        policy_id=policy_id,
        weighting_profile=weighting_profile,
    )
    status_code, payload = verify_nonprofit(
        _get_athena_client(),
        verification_input,
        enrichment_service=_get_enrichment_service(),
        evaluation_context=context,
    )
    if status_code != 200:
        raise ValueError(payload.get("message") or "Verification failed")
    payload["state_compliance"] = extract_state_compliance(payload.get("enrichment"))
    payload["external_signals"] = extract_external_signals(payload.get("enrichment"))
    return payload


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    candidate = str(value).strip().lower()
    if candidate in {"true", "1", "yes"}:
        return True
    if candidate in {"false", "0", "no"}:
        return False
    raise ValueError("active_only must be a boolean")


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
        "state_compliance": item.get("state_compliance"),
        "external_signals": item.get("external_signals"),
        "integration_evaluation": item.get("integration_evaluation"),
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
from charity_status.ops import S3RunStore


def policy_id_required(verification_input: VerificationInput) -> bool:
    return bool(verification_input.policy_id)
