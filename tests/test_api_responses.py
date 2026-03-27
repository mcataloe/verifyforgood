from __future__ import annotations

import json

from charity_status.api import DeprecationMetadata, build_response_context, error_response, json_response


def test_json_response_wraps_payload_with_standard_envelope():
    response_context = build_response_context(
        {"requestContext": {"requestId": "req-123"}},
        None,
        plan="growth",
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
        "plan": "growth",
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


def test_error_response_includes_configured_support_metadata_for_server_errors(monkeypatch):
    monkeypatch.setenv("PUBLIC_BRAND_NAME", "VerifyForGood")
    monkeypatch.setenv("SUPPORT_EMAIL", "support@verifyforgood.com")
    monkeypatch.setenv("DOMAIN", "api.verifyforgood.com")
    response_context = build_response_context(None, None, plan="growth")

    response = error_response(502, "Upstream provider failed", response_context=response_context, code="billing_provider_error")
    body = json.loads(response["body"])

    assert body["meta"]["support"] == {
        "brand_name": "VerifyForGood",
        "support_email": "support@verifyforgood.com",
        "domain": "api.verifyforgood.com",
        "homepage_url": "https://api.verifyforgood.com",
    }


def test_json_response_reflects_allowed_cors_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,https://dev.charitystatusapi.com")
    response_context = build_response_context(
        {
            "headers": {
                "Origin": "http://localhost:5173",
            }
        },
        None,
        plan="portal",
    )

    response = json_response(200, {"result": "ok"}, response_context=response_context)

    assert response["headers"]["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response["headers"]["Access-Control-Allow-Headers"] == "Content-Type,Authorization,X-Portal-Account-Id,X-Portal-Workspace-Id"
    assert response["headers"]["Access-Control-Allow-Methods"] == "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    assert response["headers"]["Vary"] == "Origin"


def test_error_response_omits_cors_headers_for_disallowed_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    response_context = build_response_context(
        {
            "headers": {
                "Origin": "https://example.com",
            }
        },
        None,
        plan="portal",
    )

    response = error_response(400, "Bad request", response_context=response_context)

    assert "Access-Control-Allow-Origin" not in response["headers"]
    assert "Access-Control-Allow-Headers" not in response["headers"]
    assert "Access-Control-Allow-Methods" not in response["headers"]
