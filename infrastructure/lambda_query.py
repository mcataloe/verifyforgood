from __future__ import annotations

import os

from charity_status.api import error_response, json_response
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.query import AthenaQueryClient, map_nonprofit_record
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout
from charity_status.scoring import calculate_v1_scores

DATABASE = os.environ.get("DATABASE", "irs_nonprofits")
TABLE = os.environ.get("TABLE", "eo_bmf")
WORKGROUP = os.environ.get("WORKGROUP")

athena_client: AthenaQueryClient | None = None


def _get_athena_client() -> AthenaQueryClient:
    global athena_client
    if athena_client is None:
        athena_client = AthenaQueryClient(
            database=DATABASE,
            table=TABLE,
            workgroup=WORKGROUP,
        )
    return athena_client


def handler(event, context):
    path_params = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}

    raw_ein = path_params.get("ein")
    subsection = query_params.get("subsection")

    try:
        normalized_ein = normalize_ein(raw_ein)
    except EINValidationError as exc:
        return error_response(400, str(exc))

    try:
        query_execution_id, record = _get_athena_client().lookup_nonprofit(normalized_ein, subsection=subsection)
    except AthenaQueryTimeout as exc:
        return json_response(504, {"message": str(exc)})
    except AthenaQueryError:
        return error_response(500, "Internal server error")
    except Exception:
        return error_response(500, "Internal server error")

    if not record:
        return json_response(404, {"message": "Nonprofit not found", "ein": normalized_ein})

    mapped = map_nonprofit_record(normalized_ein, record)
    score_result = calculate_v1_scores(record=record, verification=mapped.verification, ein_valid=True)

    payload = mapped.to_dict()
    payload["scores"] = score_result.scores
    payload["score_explanation"] = score_result.explanation
    payload["queryExecutionId"] = query_execution_id

    return json_response(200, payload)
