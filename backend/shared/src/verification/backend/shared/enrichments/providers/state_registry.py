from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from verification.backend.shared.enrichments.base import EnrichmentProvider, ProviderError
from verification.backend.shared.enrichments.models import EnrichmentProviderResult, EnrichmentStatus, now_utc_iso
from verification.backend.ingest.state import StateRegistryLookupRequest, StateRegistryLookupService, StateRegistryRecord
from verification.backend.shared.sources import ProviderCapability, SourceCategory


class StateRegistryAdapter(ABC):
    @abstractmethod
    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        raise NotImplementedError


class StateRegistryApiAdapter(StateRegistryAdapter):
    def __init__(self, endpoint: str, timeout_seconds: int = 5) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    def lookup(self, ein: str, organization_name: str | None = None) -> dict[str, Any] | None:
        import json
        import urllib.parse
        import urllib.request

        query = f"?ein={urllib.parse.quote(ein)}"
        if organization_name:
            query += f"&name={urllib.parse.quote(organization_name)}"
        request = urllib.request.Request(f"{self._endpoint}{query}", headers={"Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status >= 400:
                    raise ProviderError(f"State registry lookup failed with status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
                return payload if isinstance(payload, dict) else None
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"State registry lookup failed: {exc}") from exc


class StateRegistryProvider(EnrichmentProvider):
    def __init__(
        self,
        enabled: bool,
        adapter: StateRegistryAdapter | None = None,
        lookup_service: StateRegistryLookupService | None = None,
    ) -> None:
        self._enabled = enabled
        self._adapter = adapter
        self._lookup_service = lookup_service

    @property
    def name(self) -> str:
        return "state_registry"

    def is_enabled(self) -> bool:
        return self._enabled and (self._adapter is not None or self._lookup_service is not None)

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(provider_name=self.name, categories=[SourceCategory.COMPLIANCE], source_ids=["state_registry.compliance"], us_only=True)]

    def lookup(
        self,
        ein: str,
        organization_name: str | None = None,
        jurisdiction_state: str | None = None,
    ) -> EnrichmentProviderResult:
        if not self.is_enabled():
            return self.disabled_result()

        fetched_at = now_utc_iso()
        try:
            if self._lookup_service is not None and organization_name and jurisdiction_state:
                return self._lookup_via_service(
                    ein=ein,
                    organization_name=organization_name,
                    jurisdiction_state=jurisdiction_state,
                    fetched_at=fetched_at,
                )
            raw = self._adapter.lookup(ein=ein, organization_name=organization_name) if self._adapter is not None else None
        except Exception as exc:
            raise ProviderError(f"State registry lookup failed: {exc}") from exc

        fields = self._normalize(raw or {})
        status = EnrichmentStatus.MATCHED if fields else EnrichmentStatus.NO_MATCH
        return EnrichmentProviderResult(
            name=self.name,
            status=status,
            provider_record_id=(raw or {}).get("record_id") if isinstance(raw, dict) else None,
            fetched_at=fetched_at,
            fields=fields,
            source_payload=raw if isinstance(raw, dict) else None,
            source={
                "record_id": (raw or {}).get("record_id") if isinstance(raw, dict) else None,
                "fetched_at": fetched_at,
                "licensed": True,
                "notes": "State registry provider scaffold via adapter pattern",
            },
            source_records=(
                [
                    self.build_normalized_source_record(
                        ein=ein,
                        source_id="state_registry.compliance",
                        category=SourceCategory.COMPLIANCE,
                        description="State registry compliance source",
                        fetched_at=fetched_at,
                        fields=fields,
                        record_id=(raw or {}).get("record_id") if isinstance(raw, dict) else None,
                        expires_at=fields.get("registration_expiration_date"),
                    )
                ]
                if fields
                else []
            ),
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )

    def _lookup_via_service(
        self,
        *,
        ein: str,
        organization_name: str,
        jurisdiction_state: str,
        fetched_at: str,
    ) -> EnrichmentProviderResult:
        request = StateRegistryLookupRequest(
            organization_name=organization_name,
            normalized_organization_name=organization_name,
            state=jurisdiction_state,
            ein=ein,
        )
        outcome = self._lookup_service.lookup(request)
        if outcome.records:
            record = outcome.records[0]
            return EnrichmentProviderResult(
                name=self.name,
                status=EnrichmentStatus.MATCHED,
                provider_record_id=record.external_entity_id,
                fetched_at=fetched_at,
                fields=self._normalize_state_registry_record(record),
                source_payload={
                    "record": record.to_dict(),
                    "lookup": outcome.to_dict(),
                },
                source={
                    "record_id": record.external_entity_id,
                    "fetched_at": fetched_at,
                    "licensed": True,
                    "notes": f"State registry adapter match via {record.source_name}",
                    "source_name": record.source_name,
                    "raw_payload_ref": record.raw_payload_ref.to_dict() if record.raw_payload_ref else None,
                },
                source_records=[
                    self.build_normalized_source_record(
                        ein=ein,
                        source_id="state_registry.compliance",
                        category=SourceCategory.COMPLIANCE,
                        description=f"State registry compliance source ({record.source_name})",
                        fetched_at=fetched_at,
                        fields=self._normalize_state_registry_record(record),
                        record_id=record.external_entity_id,
                    )
                ],
                capabilities=[capability.to_dict() for capability in self.capabilities()],
            )

        if outcome.failures:
            error = outcome.failures[0].message
            return EnrichmentProviderResult(
                name=self.name,
                status=EnrichmentStatus.FAILED,
                provider_record_id=None,
                fetched_at=fetched_at,
                fields={},
                source_payload={"lookup": outcome.to_dict()},
                source={
                    "record_id": None,
                    "fetched_at": fetched_at,
                    "licensed": True,
                    "notes": "State registry adapter lookup failed",
                },
                capabilities=[capability.to_dict() for capability in self.capabilities()],
                error=error,
            )

        return EnrichmentProviderResult(
            name=self.name,
            status=EnrichmentStatus.NO_MATCH,
            provider_record_id=None,
            fetched_at=fetched_at,
            fields={},
            source_payload={"lookup": outcome.to_dict()},
            source={
                "record_id": None,
                "fetched_at": fetched_at,
                "licensed": True,
                "notes": "State registry adapter lookup returned no matching record",
            },
            capabilities=[capability.to_dict() for capability in self.capabilities()],
        )

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "registration_status": payload.get("registration_status"),
            "registration_jurisdiction": payload.get("registration_jurisdiction"),
            "registration_expiration_date": payload.get("registration_expiration_date"),
            "solicitation_permitted": payload.get("solicitation_permitted"),
            "compliance_flags": payload.get("compliance_flags") or [],
        }

    @classmethod
    def _normalize_state_registry_record(cls, record: StateRegistryRecord) -> dict[str, Any]:
        status = record.status.value if record.status is not None else None
        compliance_flags = []
        if record.standing is not None and record.standing.value != "good_standing":
            compliance_flags.append(record.standing.value)
        if status in {"inactive", "dissolved", "revoked", "suspended"}:
            compliance_flags.append(status)
        return cls._normalize(
            {
                "registration_status": status,
                "registration_jurisdiction": record.state_code,
                "registration_expiration_date": record.last_filing_date,
                "solicitation_permitted": True if status == "active" else None,
                "compliance_flags": sorted(set(compliance_flags)),
            }
        )

