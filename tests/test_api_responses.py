from __future__ import annotations

import json

from charity_status.api import DeprecationMetadata, build_response_context, error_response, json_response


def test_json_response_wraps_payload_with_standard_envelope():
    response_context = build_response_context(
        {"requestContext": {"requestId": "req-123"}},
        None,
        plan="team",
    )

    response = json_response(200, {"result": "ok"}, response_context=response_context, meta={"count": 1})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    assert body == {
        "api_version": "v1",
        "api_release": "1.0.0",
        "request_id": "req-123",
        "deprecation": {
            "status": "active",
            "sunset_date": None,
            "recommended_version": None,
        },
        "plan": "team",
        "data": {"result": "ok"},
        "meta": {"count": 1},
        "errors": [],
    }


def test_error_response_sets_deprecation_headers_when_endpoint_is_deprecated():
    response_context = build_response_context(
        None,
        None,
        plan="public",
        deprecation=DeprecationMetadata(
            status="deprecated",
            sunset_date="2026-12-31",
            recommended_version="v2",
        ),
    )

    response = error_response(410, "Endpoint retired", response_context=response_context, code="gone")
    body = json.loads(response["body"])

    assert response["headers"]["Deprecation"] == "true"
    assert response["headers"]["Sunset"] == "2026-12-31"
    assert body["errors"] == [{"code": "gone", "message": "Endpoint retired"}]
    assert body["deprecation"]["recommended_version"] == "v2"
