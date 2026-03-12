from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from charity_status.enrichments import EnrichmentService, ProviderRegistry
from charity_status.enrichments.providers import MockProvider
from charity_status.query import VerificationInput, verify_nonprofit


@dataclass
class InMemoryQueryRepository:
    record: dict[str, Any]

    def lookup_nonprofit(self, ein: str, subsection: str | None = None) -> tuple[str, dict[str, Any] | None]:
        del subsection
        return "local-ref", self.record if self.record.get("ein") == ein else None

    def lookup_form990_enrichment(self, ein: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        del ein
        return None, None, None, None

    def list_form990_filings(self, ein: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        del ein, limit
        return "local-ref", []

    def lookup_peer_benchmark(self, group: dict[str, Any]) -> dict[str, Any]:
        del group
        return {"count": 0, "metrics": {}}


def main() -> None:
    repository = InMemoryQueryRepository(
        record={
            "ein": "123456789",
            "name": "Local Reference Nonprofit",
            "state": "IL",
            "status": "1",
            "deductibility": "1",
            "subsection": "03",
            "ntee_cd": "P20",
            "tax_period": "202501",
            "filing_req_cd": "1",
            "asset_amt": "",
            "income_amt": "",
            "revenue_amt": "",
        }
    )
    enrichment_service = EnrichmentService(registry=ProviderRegistry(providers=[MockProvider(enabled=True)]))
    status, payload = verify_nonprofit(
        repository,
        VerificationInput(ein="123456789", provided_name="Local Reference Nonprofit"),
        enrichment_service=enrichment_service,
    )
    print(f"status={status}")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
