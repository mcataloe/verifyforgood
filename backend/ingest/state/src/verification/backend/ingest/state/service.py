from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verification.backend.ingest.state.errors import StateRegistryLookupFailedError, UnsupportedStateRegistryError
from verification.backend.ingest.state.models import StateRegistryLookupRequest, StateRegistryRecord
from verification.backend.ingest.state.repository import StateRegistryRecordRepository
from verification.backend.ingest.state.registry import StateRegistryAdapterRegistry


@dataclass(frozen=True)
class StateRegistryLookupFailure:
    state_code: str
    error_code: str
    message: str
    source_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_code": self.state_code,
            "error_code": self.error_code,
            "message": self.message,
            "source_name": self.source_name,
        }


@dataclass(frozen=True)
class StateRegistryLookupOutcome:
    request: StateRegistryLookupRequest
    records: list[StateRegistryRecord]
    failures: list[StateRegistryLookupFailure]
    persisted_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "failures": [failure.to_dict() for failure in self.failures],
            "persisted_count": self.persisted_count,
        }


@dataclass(frozen=True)
class StateRegistryLookupService:
    adapter_registry: StateRegistryAdapterRegistry
    repository: StateRegistryRecordRepository | None = None

    def search(self, request: StateRegistryLookupRequest) -> list[StateRegistryRecord]:
        return self.lookup(request).records

    def lookup(self, request: StateRegistryLookupRequest) -> StateRegistryLookupOutcome:
        try:
            adapter = self.adapter_registry.resolve(request.state)
        except UnsupportedStateRegistryError as exc:
            return StateRegistryLookupOutcome(
                request=request,
                records=[],
                failures=[
                    StateRegistryLookupFailure(
                        state_code=request.state,
                        error_code="unsupported_state",
                        message=str(exc),
                    )
                ],
            )

        try:
            raw_records = adapter.search(request)
        except Exception as exc:
            return StateRegistryLookupOutcome(
                request=request,
                records=[],
                failures=[
                    StateRegistryLookupFailure(
                        state_code=request.state,
                        error_code="adapter_lookup_failed",
                        message=str(exc) or "State registry lookup failed",
                        source_name=adapter.source_name,
                    )
                ],
            )

        records: list[StateRegistryRecord] = []
        failures: list[StateRegistryLookupFailure] = []
        persisted_count = 0
        for raw_record in raw_records:
            try:
                parsed = adapter.parse_record(raw_record, request=request)
            except Exception as exc:
                failures.append(
                    StateRegistryLookupFailure(
                        state_code=request.state,
                        error_code="record_parse_failed",
                        message=str(exc) or "State registry record parse failed",
                        source_name=adapter.source_name,
                    )
                )
                continue
            if parsed is None:
                continue
            records.append(parsed)
            if self.repository is None:
                continue
            try:
                self.repository.save_record(request=request, record=parsed)
                persisted_count += 1
            except Exception as exc:
                failures.append(
                    StateRegistryLookupFailure(
                        state_code=request.state,
                        error_code="persistence_failed",
                        message=str(exc) or "State registry persistence failed",
                        source_name=adapter.source_name,
                    )
                )
        return StateRegistryLookupOutcome(
            request=request,
            records=records,
            failures=failures,
            persisted_count=persisted_count,
        )

    def fetch_by_external_entity_id(
        self,
        *,
        state_code: str,
        external_entity_id: str,
        request: StateRegistryLookupRequest | None = None,
    ) -> StateRegistryRecord | None:
        try:
            adapter = self.adapter_registry.resolve(state_code)
        except UnsupportedStateRegistryError as exc:
            raise StateRegistryLookupFailedError(str(exc)) from exc
        try:
            raw_record = adapter.fetch_by_external_entity_id(external_entity_id)
        except Exception as exc:
            raise StateRegistryLookupFailedError(str(exc) or "State registry lookup failed") from exc
        if raw_record is None:
            return None
        try:
            record = adapter.parse_record(raw_record, request=request)
        except Exception as exc:
            raise StateRegistryLookupFailedError(str(exc) or "State registry record parse failed") from exc
        if record is None:
            return None
        if self.repository is not None and request is not None:
            try:
                self.repository.save_record(request=request, record=record)
            except Exception:
                pass
        return record

