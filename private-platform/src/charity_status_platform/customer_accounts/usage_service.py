from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from charity_status_platform.billing_usage import monthly_period_for

from .identity_models import UsageMetricType, UsageRecord
from .identity_repositories import OrganizationRepository, UsageRepository


class UsageTrackingError(ValueError):
    status_code = 400


@dataclass(frozen=True)
class UsageService:
    organizations: OrganizationRepository
    usage: UsageRepository

    def increment_metric(
        self,
        *,
        organization_id: str,
        metric_type: str,
        period_month: str | None = None,
        units: int = 1,
    ) -> UsageRecord:
        if self.organizations.get(organization_id) is None:
            raise UsageTrackingError("organization_id must reference an existing organization")
        normalized_metric = _validate_metric_type(metric_type)
        resolved_units = max(0, int(units))
        if resolved_units <= 0:
            existing = self.usage.get(organization_id, normalized_metric.value, _resolve_period_month(period_month))
            if existing is None:
                return self.usage.put(
                    UsageRecord(
                        organization_id=organization_id,
                        metric_type=normalized_metric,
                        period_month=_resolve_period_month(period_month),
                        request_count=0,
                        last_updated=_utc_now(),
                    )
                )
            return existing
        return self.usage.increment(
            organization_id,
            normalized_metric.value,
            _resolve_period_month(period_month),
            units=resolved_units,
            last_updated=_utc_now(),
        )

    def get_monthly_usage(self, *, organization_id: str, period_month: str | None = None) -> list[UsageRecord]:
        if self.organizations.get(organization_id) is None:
            raise UsageTrackingError("organization_id must reference an existing organization")
        return self.usage.list_for_period(organization_id, _resolve_period_month(period_month))

    def reset_metric(
        self,
        *,
        organization_id: str,
        metric_type: str,
        period_month: str | None = None,
    ) -> UsageRecord:
        if self.organizations.get(organization_id) is None:
            raise UsageTrackingError("organization_id must reference an existing organization")
        return self.usage.put(
            UsageRecord(
                organization_id=organization_id,
                metric_type=_validate_metric_type(metric_type),
                period_month=_resolve_period_month(period_month),
                request_count=0,
                last_updated=_utc_now(),
            )
        )


def usage_metrics_for_route(route_key: str) -> tuple[UsageMetricType, ...]:
    normalized = str(route_key or "").strip().upper()
    metrics: list[UsageMetricType] = [UsageMetricType.API_REQUESTS]
    if any(
        marker in normalized
        for marker in (
            "GET /V1/NONPROFIT/",
            "GET /V1/NONPROFITS/SEARCH",
            "GET /V1/NONPROFITS/{EIN}",
            "GET /V1/NONPROFIT/{EIN}/FILINGS",
            "/SOURCES",
            "/COMPLIANCE",
            "/FEDERAL-AWARDS",
        )
    ):
        metrics.append(UsageMetricType.NONPROFIT_LOOKUPS)
    if normalized in {"POST /V1/VERIFY", "POST /V1/VERIFY/BATCH", "POST /V1/NONPROFITS/VERIFY"}:
        metrics.append(UsageMetricType.ENRICHMENT_REQUESTS)
    return tuple(metrics)


def _validate_metric_type(metric_type: str) -> UsageMetricType:
    try:
        return UsageMetricType(str(metric_type or "").strip().lower())
    except Exception as exc:  # noqa: BLE001
        raise UsageTrackingError("metric_type must be one of: api_requests, nonprofit_lookups, enrichment_requests") from exc


def _resolve_period_month(period_month: str | None) -> str:
    candidate = str(period_month or "").strip()
    return candidate or monthly_period_for()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
