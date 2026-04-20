"""FastAPI application ownership for the backend API runtime."""

from __future__ import annotations

from verification_backend.shared.local_dev import load_backend_local_env
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .transport import API_ROUTE_SPECS, build_backend_request, runtime_response_to_http


# Keep direct ASGI imports (`uvicorn ...app:app`) aligned with the documented
# backend local env contract without overriding already-exported variables.
load_backend_local_env()

from . import runtime


async def _dispatch_runtime_request(request: Request, *, resource: str) -> Response:
    raw_body = await request.body()
    body = raw_body.decode("utf-8") if raw_body else None
    event = build_backend_request(request, resource=resource, body=body)
    return runtime_response_to_http(runtime.handle_api_event(event))


def create_app() -> FastAPI:
    app = FastAPI(title="Charity Status API", version="1.0.0")

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/ready")
    async def ready() -> JSONResponse:
        return JSONResponse({"status": "ready"})

    def register_route(resource_spec) -> None:
        async def endpoint(request: Request) -> Response:
            return await _dispatch_runtime_request(request, resource=resource_spec.resource)

        methods = sorted(set(resource_spec.methods) | {"OPTIONS"})
        endpoint_name = (
            f"compat_{'_'.join(methods).lower()}_"
            f"{resource_spec.resource.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        )
        app.add_api_route(resource_spec.path, endpoint, methods=methods, name=endpoint_name)

    for spec in API_ROUTE_SPECS:
        register_route(spec)

    return app


app = create_app()


__all__ = ["app", "create_app"]

