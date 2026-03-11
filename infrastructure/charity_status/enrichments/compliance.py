from __future__ import annotations

from typing import Any


COMPLIANCE_KEYS = {
    "registration_status",
    "registration_jurisdiction",
    "registration_expiration_date",
    "solicitation_permitted",
    "compliance_flags",
}


def extract_state_compliance(enrichment: dict[str, Any] | None) -> dict[str, Any]:
    payload = enrichment or {}
    providers = payload.get("providers") or []

    matches: list[dict[str, Any]] = []
    all_flags: list[str] = []

    for provider in providers:
        fields = provider.get("fields") or {}
        if not isinstance(fields, dict):
            continue
        if not any(key in fields for key in COMPLIANCE_KEYS):
            continue
        flags = fields.get("compliance_flags")
        normalized_flags = [str(flag) for flag in flags] if isinstance(flags, list) else []
        all_flags.extend(normalized_flags)
        matches.append(
            {
                "provider": provider.get("name"),
                "registration_status": fields.get("registration_status"),
                "registration_jurisdiction": fields.get("registration_jurisdiction"),
                "registration_expiration_date": fields.get("registration_expiration_date"),
                "solicitation_permitted": fields.get("solicitation_permitted"),
                "compliance_flags": normalized_flags,
                "source": provider.get("source") or {},
            }
        )

    selected = sorted(matches, key=lambda item: str(item.get("provider") or ""))[0] if matches else {}
    unique_flags = sorted(set(all_flags))
    return {
        "registration_status": selected.get("registration_status"),
        "registration_jurisdiction": selected.get("registration_jurisdiction"),
        "registration_expiration_date": selected.get("registration_expiration_date"),
        "solicitation_permitted": selected.get("solicitation_permitted"),
        "compliance_flags": unique_flags,
        "source": {
            "provider": selected.get("provider"),
            "matched_provider_count": len(matches),
            "attribution": selected.get("source") or {},
        },
    }
