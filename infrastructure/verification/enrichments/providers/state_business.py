from __future__ import annotations

import json
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from verification.enrichments.base import EnrichmentProvider, ProviderError
from verification.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from verification.sources import ProviderCapability, SourceCategory


class StateBusinessAdapter(ABC):
    @abstractmethod
    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        raise NotImplementedError


class StateBusinessApiAdapter(StateBusinessAdapter):
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
                    raise ProviderError(f"State business lookup failed with status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                return payload if isinstance(payload, dict) else None
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"State business lookup failed: {exc}") from exc


class StateBusinessProvider(EnrichmentProvider):
    def __init__(self, enabled: bool, adapter: StateBusinessAdapter | None = None) -> None:
        self._enabled = enabled
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "state_business"

    def is_enabled(self) -> bool:
        return self._enabled and self._adapter is not None

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.COMPLIANCE], source_ids=["state_business.entity_status"], us_only=True)]

    def lookup(self, ein: str, organization_name: str | None = None) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()
        fetched_at = now_utc_iso()
        try:
            raw = self._adapter.lookup(ein=ein, organization_name=organization_name)
        except Exception as exc:
            raise ProviderError(f"State business lookup failed: {exc}") from exc

        fields = self._normalize(raw or {})
        status = EnrichmentStatus.MATCHED if fields else EnrichmentStatus.NO_MATCH
        record_id = (raw or {}).get("record_id") if isinstance(raw, dict) else None
        return EnrichmentProviderResult(
            name=self.name,
            status=status,
            provider_record_id=str(record_id) if record_id is not None else None,
            fetched_at=fetched_at,
            fields=fields,
            source_payload=raw if isinstance(raw, dict) else None,
            source={"record_id": str(record_id) if record_id is not None else None, "fetched_at": fetched_at, "licensed": True, "notes": "State business entity status scaffold"},
            source_records=(
                [
                    self.build_normalized_source_record(
                        ein=ein,
                        source_id="state_business.entity_status",
                        category=SourceCategory.COMPLIANCE,
                        description="State business entity status source",
                        fetched_at=fetched_at,
                        fields=fields,
                        record_id=str(record_id) if record_id is not None else None,
                        expires_at=fields.get("entity_expiration_date"),
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
            "entity_status": payload.get("entity_status"),
            "entity_jurisdiction": payload.get("entity_jurisdiction"),
            "entity_expiration_date": payload.get("entity_expiration_date"),
            "good_standing": payload.get("good_standing"),
            "compliance_flags": payload.get("compliance_flags") or [],
        }

