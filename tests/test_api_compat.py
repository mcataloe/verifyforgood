from __future__ import annotations

import json
import importlib
import pathlib
import sys

from fastapi.testclient import TestClient


ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"
INFRASTRUCTURE_SRC = ROOT / "infrastructure"
BACKEND_API_SRC = ROOT / "backend" / "api" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"

for path in (PRIVATE_PLATFORM_SRC, INFRASTRUCTURE_SRC, BACKEND_API_SRC, BACKEND_SHARED_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def test_health_and_ready_endpoints():
    from verification_backend.api.app import create_app

    client = TestClient(create_app())

    health = client.get("/health")
    ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_compat_route_preserves_path_headers_and_query(monkeypatch):
    from verification_backend.api.app import create_app
    from verification_backend.api import runtime as api_runtime

    def fake_handle_api_event(event, context=None):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "X-Compat": "yes"},
            "body": json.dumps(
                {
                    "resource": event.get("resource"),
                    "path": event.get("path"),
                    "pathParameters": event.get("pathParameters"),
                    "queryStringParameters": event.get("queryStringParameters"),
                    "authorization": (event.get("headers") or {}).get("authorization"),
                }
            ),
        }

    monkeypatch.setattr(api_runtime, "handle_api_event", fake_handle_api_event)

    client = TestClient(create_app())
    response = client.get(
        "/v1/nonprofit/123456789",
        params={"subsection": "03"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.headers["x-compat"] == "yes"
    assert response.json() == {
        "resource": "/v1/nonprofit/{ein}",
        "path": "/v1/nonprofit/123456789",
        "pathParameters": {"ein": "123456789"},
        "queryStringParameters": {"subsection": "03"},
        "authorization": "Bearer test-token",
    }


def test_compat_route_preserves_json_body_for_portal_auth(monkeypatch):
    from verification_backend.api.app import create_app
    from verification_backend.api import runtime as api_runtime

    def fake_handle_api_event(event, context=None):
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "resource": event.get("resource"),
                    "method": event.get("httpMethod"),
                    "body": event.get("body"),
                }
            ),
        }

    monkeypatch.setattr(api_runtime, "handle_api_event", fake_handle_api_event)

    client = TestClient(create_app())
    response = client.post(
        "/v1/auth/register",
        json={"email": "person@example.com", "password": "secret"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "resource": "/v1/auth/register",
        "method": "POST",
        "body": "{\"email\":\"person@example.com\",\"password\":\"secret\"}",
    }


def test_webhook_route_preserves_raw_body_and_signature_header(monkeypatch):
    from verification_backend.api.app import create_app
    from verification_backend.api import runtime as api_runtime

    def fake_handle_api_event(event, context=None):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "resource": event.get("resource"),
                    "body": event.get("body"),
                    "rawBody": event.get("rawBody"),
                    "signature": (event.get("headers") or {}).get("stripe-signature"),
                }
            ),
        }

    monkeypatch.setattr(api_runtime, "handle_api_event", fake_handle_api_event)

    client = TestClient(create_app())
    payload = "{\"id\":\"evt_123\"}"
    response = client.post(
        "/v1/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "resource": "/v1/webhooks/stripe",
        "body": payload,
        "rawBody": payload,
        "signature": "sig_test",
    }


def test_private_platform_api_compat_reexports_backend_owned_app():
    from verification_backend.api.app import create_app as backend_create_app
    from verification_platform.runtime.api_compat import create_app as compat_create_app

    assert compat_create_app is backend_create_app


def test_backend_api_app_import_loads_shared_local_env(monkeypatch):
    from verification_backend.shared import local_dev

    calls: list[tuple[object, object, object]] = []

    def fake_loader(*, root=None, env_path=None, override=False):
        calls.append((root, env_path, override))
        return pathlib.Path("backend/.env.local")

    monkeypatch.setattr(local_dev, "load_backend_local_env", fake_loader)
    sys.modules.pop("verification_backend.api.app", None)

    try:
        importlib.import_module("verification_backend.api.app")
    finally:
        sys.modules.pop("verification_backend.api.app", None)

    assert calls == [(None, None, False)]

