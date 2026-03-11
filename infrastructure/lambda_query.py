from __future__ import annotations

import os
import json

from charity_status.api import error_response, json_response
from charity_status.normalization import EINValidationError, normalize_ein
from charity_status.query import AthenaQueryClient, VerificationInput, verify_nonprofit
from charity_status.query.athena import AthenaQueryError, AthenaQueryTimeout

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
        verification_input = VerificationInput(
            ein=normalized_ein,
            provided_name=verification_input.provided_name,
            subsection=verification_input.subsection,
        )
        status_code, payload = verify_nonprofit(_get_athena_client(), verification_input)
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
