from __future__ import annotations

from typing import Any

from verification.core.models import AuthContext


class NoopAuthContextProvider:
    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        request_context = event.get("requestContext") or {}
        identity = request_context.get("identity") or {}
        source_ip = str(identity.get("sourceIp") or "")
        metadata = {"source_ip": source_ip} if source_ip else {}
        return AuthContext(metadata=metadata)


class NoopQuotaMeteringHook:
    def on_request(self, auth_context: AuthContext, route_key: str) -> None:
        del auth_context, route_key

    def on_response(self, auth_context: AuthContext, route_key: str, status_code: int) -> None:
        del auth_context, route_key, status_code

