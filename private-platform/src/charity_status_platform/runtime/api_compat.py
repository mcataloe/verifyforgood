from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from infrastructure import lambda_query


@dataclass(frozen=True)
class ApiRouteSpec:
    path: str
    resource: str
    methods: tuple[str, ...]


API_ROUTE_SPECS: tuple[ApiRouteSpec, ...] = (
    ApiRouteSpec("/v1/auth/register", "/v1/auth/register", ("POST",)),
    ApiRouteSpec("/v1/auth/login", "/v1/auth/login", ("POST",)),
    ApiRouteSpec("/v1/auth/me", "/v1/auth/me", ("GET",)),
    ApiRouteSpec("/v1/invitations/accept", "/v1/invitations/accept", ("POST",)),
    ApiRouteSpec("/v1/nonprofit/{ein}", "/v1/nonprofit/{ein}", ("GET",)),
    ApiRouteSpec("/v1/nonprofit/{ein}/filings", "/v1/nonprofit/{ein}/filings", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/search", "/v1/nonprofits/search", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/{ein}", "/v1/nonprofits/{ein}", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/{ein}/sources", "/v1/nonprofits/{ein}/sources", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/{ein}/sources/{source_name}", "/v1/nonprofits/{ein}/sources/{source_name}", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/{ein}/compliance", "/v1/nonprofits/{ein}/compliance", ("GET",)),
    ApiRouteSpec("/v1/nonprofits/{ein}/federal-awards", "/v1/nonprofits/{ein}/federal-awards", ("GET",)),
    ApiRouteSpec("/v1/verify", "/v1/verify", ("POST",)),
    ApiRouteSpec("/v1/verify/batch", "/v1/verify/batch", ("POST",)),
    ApiRouteSpec("/v1/oauth/token", "/v1/oauth/token", ("POST",)),
    ApiRouteSpec("/v1/webhooks/stripe", "/v1/webhooks/stripe", ("POST",)),
    ApiRouteSpec("/v1/plans", "/v1/plans", ("GET",)),
    ApiRouteSpec("/v1/organizations", "/v1/organizations", ("POST",)),
    ApiRouteSpec("/v1/organizations/current", "/v1/organizations/current", ("DELETE",)),
    ApiRouteSpec("/v1/organizations/current/members", "/v1/organizations/current/members", ("GET",)),
    ApiRouteSpec("/v1/organizations/current/invitations", "/v1/organizations/current/invitations", ("GET", "POST")),
    ApiRouteSpec("/v1/organizations/current/members/{memberId}", "/v1/organizations/current/members/{memberId}", ("PATCH", "DELETE")),
    ApiRouteSpec("/v1/organizations/current/api-keys", "/v1/organizations/current/api-keys", ("GET", "POST")),
    ApiRouteSpec("/v1/organizations/current/api-keys/{keyId}", "/v1/organizations/current/api-keys/{keyId}", ("DELETE",)),
    ApiRouteSpec("/v1/organization/settings", "/v1/organization/settings", ("GET", "PUT")),
    ApiRouteSpec("/v1/organization/usage", "/v1/organization/usage", ("GET",)),
    ApiRouteSpec("/v1/organization/activity", "/v1/organization/activity", ("GET",)),
    ApiRouteSpec("/v1/organization/support", "/v1/organization/support", ("GET",)),
    ApiRouteSpec("/v1/organization/support-requests", "/v1/organization/support-requests", ("POST",)),
    ApiRouteSpec("/v1/organization/billing/customer-bootstrap", "/v1/organization/billing/customer-bootstrap", ("POST",)),
    ApiRouteSpec("/v1/organization/billing/checkout-session", "/v1/organization/billing/checkout-session", ("POST",)),
    ApiRouteSpec("/v1/organization/billing/plan-change", "/v1/organization/billing/plan-change", ("POST",)),
    ApiRouteSpec("/v1/organization/billing/portal-session", "/v1/organization/billing/portal-session", ("POST",)),
    ApiRouteSpec("/v1/organization/billing/subscription", "/v1/organization/billing/subscription", ("GET",)),
    ApiRouteSpec("/v1/admin/accounts", "/v1/admin/accounts", ("GET", "POST")),
    ApiRouteSpec("/v1/admin/accounts/{accountId}", "/v1/admin/accounts/{accountId}", ("GET", "PATCH")),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/subscription", "/v1/admin/accounts/{accountId}/subscription", ("GET", "PUT")),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/billing/reconcile", "/v1/admin/accounts/{accountId}/billing/reconcile", ("POST",)),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/suspend", "/v1/admin/accounts/{accountId}/suspend", ("POST",)),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/activate", "/v1/admin/accounts/{accountId}/activate", ("POST",)),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/api-keys", "/v1/admin/accounts/{accountId}/api-keys", ("GET", "POST")),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/api-keys/{keyId}", "/v1/admin/accounts/{accountId}/api-keys/{keyId}", ("DELETE",)),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/api-keys/{keyId}/rotate", "/v1/admin/accounts/{accountId}/api-keys/{keyId}/rotate", ("POST",)),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/oauth-clients", "/v1/admin/accounts/{accountId}/oauth-clients", ("GET", "POST")),
    ApiRouteSpec("/v1/admin/accounts/{accountId}/oauth-clients/{clientId}", "/v1/admin/accounts/{accountId}/oauth-clients/{clientId}", ("DELETE",)),
    ApiRouteSpec("/v1/ops/ingest/runs", "/v1/ops/ingest/runs", ("GET",)),
    ApiRouteSpec("/v1/ops/ingest/runs/{ingest_run_id}", "/v1/ops/ingest/runs/{ingest_run_id}", ("GET",)),
    ApiRouteSpec("/v1/ops/ingest/runs/{ingest_run_id}/filings", "/v1/ops/ingest/runs/{ingest_run_id}/filings", ("GET",)),
    ApiRouteSpec("/v1/ops/form990/runs", "/v1/ops/form990/runs", ("POST",)),
    ApiRouteSpec("/v1/ops/refresh/runs", "/v1/ops/refresh/runs", ("GET",)),
    ApiRouteSpec("/v1/ops/refresh/runs/{refresh_run_id}", "/v1/ops/refresh/runs/{refresh_run_id}", ("GET",)),
    ApiRouteSpec("/v1/ops/refresh/runs/{refresh_run_id}/eins", "/v1/ops/refresh/runs/{refresh_run_id}/eins", ("GET",)),
    ApiRouteSpec("/v1/ops/nonprofits/{ein}/pipeline-status", "/v1/ops/nonprofits/{ein}/pipeline-status", ("GET",)),
)


def build_api_gateway_event(
    request: Request,
    *,
    resource: str,
    body: str | None,
) -> dict[str, Any]:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    headers = {key: value for key, value in request.headers.items()}
    query_params = dict(request.query_params.items())
    path_params = {str(key): str(value) for key, value in request.path_params.items()}
    return {
        "httpMethod": request.method.upper(),
        "path": request.url.path,
        "resource": resource,
        "headers": headers,
        "queryStringParameters": query_params or None,
        "pathParameters": path_params or None,
        "body": body,
        "rawBody": body or "",
        "isBase64Encoded": False,
        "requestContext": {
            "requestId": request_id,
        },
    }


def lambda_response_to_http(response: dict[str, Any]) -> Response:
    body = response.get("body")
    if body is None:
        body = ""
    if not isinstance(body, (str, bytes)):
        body = json.dumps(body)
    headers = {
        str(key): str(value)
        for key, value in (response.get("headers") or {}).items()
        if str(key).lower() != "content-length"
    }
    return Response(
        content=body,
        status_code=int(response.get("statusCode") or 500),
        headers=headers,
    )


async def _dispatch_compat_request(request: Request, *, resource: str) -> Response:
    raw_body = await request.body()
    body = raw_body.decode("utf-8") if raw_body else None
    event = build_api_gateway_event(request, resource=resource, body=body)
    return lambda_response_to_http(lambda_query.handle_api_event(event, None))


def create_app() -> FastAPI:
    app = FastAPI(title="Charity Status API", version="1.0.0")

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/ready")
    async def ready() -> JSONResponse:
        return JSONResponse({"status": "ready"})

    def register_route(spec: ApiRouteSpec) -> None:
        async def endpoint(request: Request) -> Response:
            return await _dispatch_compat_request(request, resource=spec.resource)

        methods = sorted(set(spec.methods) | {"OPTIONS"})
        endpoint_name = f"compat_{'_'.join(methods).lower()}_{spec.resource.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        app.add_api_route(spec.path, endpoint, methods=methods, name=endpoint_name)

    for spec in API_ROUTE_SPECS:
        register_route(spec)

    return app


app = create_app()
