from __future__ import annotations

import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from verification.backend.shared.enrichments.base import EnrichmentProvider, ProviderError
from verification.backend.shared.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from verification.backend.shared.sources import ProviderCapability, SourceCategory


class OFACAdapter(ABC):
    @abstractmethod
    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        raise NotImplementedError


class OFACApiAdapter(OFACAdapter):
    def __init__(self, endpoint: str, timeout_seconds: int = 5) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        query = f"?ein={urllib.parse.quote(ein)}"
        if organization_name:
            query += f"&name={urllib.parse.quote(organization_name)}"
        request = urllib.request.Request(f"{self._endpoint}{query}", headers={"Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise ProviderError(f"OFAC lookup failed with status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                return payload if isinstance(payload, dict) else None
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"OFAC lookup failed: {exc}") from exc


class OFACProvider(EnrichmentProvider):
    def __init__(self, enabled: bool, adapter: OFACAdapter | None = None) -> None:
        self._enabled = enabled
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "ofac"

    def is_enabled(self) -> bool:
        return self._enabled and self._adapter is not None

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.RISK], source_ids=["ofac.sanctions"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()
        fetched_at = now_utc_iso()
        try:
            raw = self._adapter.lookup(ein=ein, organization_name=organization_name)
        except Exception as exc:
            raise ProviderError(f"OFAC lookup failed: {exc}") from exc
        fields = self._normalize(raw or {})
        status = EnrichmentStatus.MATCHED if fields else EnrichmentStatus.NO_MATCH
        return EnrichmentProviderResult(
            name=self.name,
            status=status,
            provider_record_id=None,
            fetched_at=fetched_at,
            fields=fields,
            source_payload=raw if isinstance(raw, dict) else None,
            source={"record_id": None, "fetched_at": fetched_at, "licensed": True, "notes": "OFAC sanctions screening scaffold"},
            source_records=(
                [
                    self.build_normalized_source_record(
                        ein=ein,
                        source_id="ofac.sanctions",
                        category=SourceCategory.RISK,
                        description="OFAC sanctions screening source",
                        fetched_at=fetched_at,
                        fields=fields,
                    )
                ]
                if fields
                else []
            ),
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "sanctions_match": bool(payload.get("sanctions_match")),
            "sanctions_lists": payload.get("sanctions_lists") or [],
            "matched_name": payload.get("matched_name"),
            "match_confidence": payload.get("match_confidence"),
        }

