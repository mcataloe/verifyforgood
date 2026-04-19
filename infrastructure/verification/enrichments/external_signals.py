from __future__ import annotations

from typing import Any


def extract_external_signals(enrichment: dict[str, Any] | None) -> dict[str, Any]:
    providers = (enrichment or {}).get("providers") or []
    signals = {
        "state_business": {
            "entity_status": None,
            "good_standing": None,
            "compliance_flags": [],
            "source": None,
        },
        "federal_awards": {
            "award_count": None,
            "total_obligations_usd": None,
            "latest_award_date": None,
            "source": None,
        },
        "sanctions": {
            "sanctions_match": False,
            "sanctions_lists": [],
            "matched_name": None,
            "source": None,
        },
    }
    for provider in providers:
        name = str(provider.get("integration_id") or provider.get("name") or "")
        fields = provider.get("fields") or {}
        if name == "state_business" and fields:
            signals["state_business"] = {
                "entity_status": fields.get("entity_status"),
                "good_standing": fields.get("good_standing"),
                "compliance_flags": fields.get("compliance_flags") or [],
                "source": name,
            }
        elif name == "usaspending" and fields:
            signals["federal_awards"] = {
                "award_count": fields.get("award_count"),
                "total_obligations_usd": fields.get("total_obligations_usd"),
                "latest_award_date": fields.get("latest_award_date"),
                "source": name,
            }
        elif name == "ofac" and fields:
            signals["sanctions"] = {
                "sanctions_match": bool(fields.get("sanctions_match")),
                "sanctions_lists": fields.get("sanctions_lists") or [],
                "matched_name": fields.get("matched_name"),
                "source": name,
            }
    return signals
