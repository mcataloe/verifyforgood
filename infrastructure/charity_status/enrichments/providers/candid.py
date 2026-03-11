from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from charity_status.enrichments.base import EnrichmentProvider, ProviderError
from charity_status.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso


class CandidProvider(EnrichmentProvider):
    def __init__(self, enabled: bool, api_key: str | None = None, endpoint: str | None = None, timeout_seconds: int = 5):
        self._enabled = enabled
        self._api_key = api_key
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "candid"

    def is_enabled(self) -> bool:
        return self._enabled and bool(self._api_key) and bool(self._endpoint)

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()

        payload = self._fetch_raw(ein, organization_name)
        normalized = self._normalize(payload)
        status = EnrichmentStatus.MATCHED if normalized else EnrichmentStatus.NO_MATCH
        record_id = payload.get("id") if isinstance(payload, dict) else None

        fetched_at = now_utc_iso()
        return EnrichmentProviderResult(
            name=self.name,
            status=status,
            provider_record_id=str(record_id) if record_id is not None else None,
            fetched_at=fetched_at,
            fields=normalized,
            source_payload=payload if isinstance(payload, dict) else None,
            source={
                "record_id": str(record_id) if record_id is not None else None,
                "fetched_at": fetched_at,
                "licensed": True,
                "notes": "Candid provider scaffold; fields depend on configured endpoint/schema",
            },
        )

    def _fetch_raw(self, ein: str, organization_name: str | None) -> dict[str, Any]:
        if not self._endpoint:
            raise ProviderError("Candid endpoint is not configured")

        query = f"?ein={urllib.parse.quote(ein)}"
        if organization_name:
            query += f"&name={urllib.parse.quote(organization_name)}"

        request = urllib.request.Request(
            f"{self._endpoint}{query}",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise ProviderError(f"Candid lookup failed with status {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Candid lookup failed: {exc}") from exc

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}

        return {
            "transparency_level": payload.get("transparency_level"),
            "profile_complete": payload.get("profile_complete"),
            "external_rating_label": payload.get("rating_label"),
            "rating_score": payload.get("rating_score"),
            "impact_metrics_available": payload.get("impact_metrics_available"),
            "leadership_data_present": payload.get("leadership_data_present"),
            "profile_link": payload.get("profile_url"),
        }
