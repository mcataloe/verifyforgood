from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from verification.enrichments import EvaluationContext
from verification.query.search import search_nonprofit_summaries
from verification.query.source_views import (
    get_nonprofit_compliance_view,
    get_nonprofit_federal_awards_view,
    get_nonprofit_single_source_view,
    get_nonprofit_sources_view,
)
from .regulatory_filings import get_nonprofit_filings
from .verification_service import OrganizationVerificationInput as VerificationInput
from .verification_service import verify_nonprofit


@dataclass(frozen=True)
class TenantNonprofitContext:
    organization_id: str
    authenticated_subject: str
    authenticated_user_id: str | None
    auth_method: str
    credential_id: str | None
    metadata: dict[str, str] = field(default_factory=dict)


class NonprofitService:
    def __init__(self, *, client: Any, enrichment_service: Any, feature_flag_service: Any | None = None) -> None:
        self._client = client
        self._enrichment_service = enrichment_service
        self._feature_flag_service = feature_flag_service

    def lookup_nonprofit(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        verification_input: VerificationInput,
        evaluation_context: Any | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        effective_context = self._resolve_effective_evaluation_context(
            tenant_context=tenant_context,
            evaluation_context=evaluation_context,
        )
        return verify_nonprofit(
            self._client,
            verification_input,
            enrichment_service=self._enrichment_service,
            evaluation_context=effective_context,
        )

    def search_nonprofits(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        name_query: str,
        limit: int,
        state: str | None = None,
        subsection: str | None = None,
        active_only: bool = False,
        cursor: str | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        return search_nonprofit_summaries(
            client=self._client,
            name_query=name_query,
            limit=limit,
            state=state,
            subsection=subsection,
            active_only=active_only,
            cursor=cursor,
        )

    def get_filings(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        ein: str,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        return get_nonprofit_filings(self._client, ein)

    def get_sources(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        ein: str,
        subsection: str | None = None,
        evaluation_context: Any | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        effective_context = self._resolve_effective_evaluation_context(
            tenant_context=tenant_context,
            evaluation_context=evaluation_context,
        )
        return get_nonprofit_sources_view(
            self._client,
            self._enrichment_service,
            ein,
            subsection=subsection,
            evaluation_context=effective_context,
        )

    def get_source_detail(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        ein: str,
        source_name: str,
        subsection: str | None = None,
        evaluation_context: Any | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        effective_context = self._resolve_effective_evaluation_context(
            tenant_context=tenant_context,
            evaluation_context=evaluation_context,
        )
        return get_nonprofit_single_source_view(
            self._client,
            self._enrichment_service,
            ein,
            source_name=source_name,
            subsection=subsection,
            evaluation_context=effective_context,
        )

    def get_compliance(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        ein: str,
        subsection: str | None = None,
        evaluation_context: Any | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        effective_context = self._resolve_effective_evaluation_context(
            tenant_context=tenant_context,
            evaluation_context=evaluation_context,
        )
        return get_nonprofit_compliance_view(
            self._client,
            self._enrichment_service,
            ein,
            subsection=subsection,
            evaluation_context=effective_context,
        )

    def get_federal_awards(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        ein: str,
        subsection: str | None = None,
        evaluation_context: Any | None = None,
    ) -> tuple[int, dict[str, Any]]:
        self._require_tenant_context(tenant_context)
        effective_context = self._resolve_effective_evaluation_context(
            tenant_context=tenant_context,
            evaluation_context=evaluation_context,
        )
        return get_nonprofit_federal_awards_view(
            self._client,
            self._enrichment_service,
            ein,
            subsection=subsection,
            evaluation_context=effective_context,
        )

    @staticmethod
    def _require_tenant_context(tenant_context: TenantNonprofitContext) -> None:
        if not tenant_context.organization_id.strip():
            raise ValueError("organization_id is required for nonprofit queries")

    def _resolve_effective_evaluation_context(
        self,
        *,
        tenant_context: TenantNonprofitContext,
        evaluation_context: Any | None,
    ) -> EvaluationContext:
        context = evaluation_context if isinstance(evaluation_context, EvaluationContext) else EvaluationContext()
        if self._feature_flag_service is None:
            return context
        try:
            return self._feature_flag_service.apply_evaluation_context_overrides(
                organization_id=tenant_context.organization_id,
                context=context,
            )
        except Exception:  # noqa: BLE001
            return context


__all__ = [
    "NonprofitService",
    "TenantNonprofitContext",
]

