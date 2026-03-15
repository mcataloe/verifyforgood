from __future__ import annotations

from typing import Any, Protocol

from charity_status.core.models import AuthContext


class QueryRepository(Protocol):
    def lookup_nonprofit(self, ein: str, subsection: str | None = None) -> tuple[str, dict[str, Any] | None]:
        ...

    def lookup_form990_enrichment(self, ein: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        ...

    def list_form990_filings(self, ein: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        ...

    def lookup_peer_benchmark(self, group: dict[str, Any]) -> dict[str, Any]:
        ...

    def list_nonprofit_eins_page(self, limit: int, start_after_ein: str | None = None) -> list[str]:
        ...


class ProfileStoreAdapter(Protocol):
    def get_profile(self, ein: str) -> dict[str, Any] | None:
        ...

    def put_profile(self, item: dict[str, Any]) -> None:
        ...


class EnrichmentProviderGateway(Protocol):
    def enrich(self, ein: str, organization_name: str | None = None, evaluation_context: Any | None = None) -> Any:
        ...


class AuthContextProvider(Protocol):
    def extract_context(self, event: dict[str, Any]) -> AuthContext:
        ...


class QuotaMeteringHook(Protocol):
    def on_request(self, auth_context: AuthContext, route_key: str) -> None:
        ...

    def on_response(self, auth_context: AuthContext, route_key: str, status_code: int) -> None:
        ...
