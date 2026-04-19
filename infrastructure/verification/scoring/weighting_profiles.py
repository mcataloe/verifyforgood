from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WeightingProfile:
    profile_id: str
    weights: dict[str, float]
    description: str


DEFAULT_WEIGHTING_PROFILE_ID = "default_v1"

WEIGHTING_PROFILES: dict[str, WeightingProfile] = {
    "default_v1": WeightingProfile(
        profile_id="default_v1",
        weights={
            "compliance": 0.25,
            "trust": 0.25,
            "financial_resilience": 0.25,
            "transparency": 0.25,
        },
        description="Balanced default weights across score dimensions.",
    ),
    "compliance_heavy_v1": WeightingProfile(
        profile_id="compliance_heavy_v1",
        weights={
            "compliance": 0.5,
            "trust": 0.2,
            "financial_resilience": 0.2,
            "transparency": 0.1,
        },
        description="Higher weight on compliance for risk-averse customer profiles.",
    ),
    "transparency_light_v1": WeightingProfile(
        profile_id="transparency_light_v1",
        weights={
            "compliance": 0.3,
            "trust": 0.3,
            "financial_resilience": 0.3,
            "transparency": 0.1,
        },
        description="Reduced transparency contribution for limited-disclosure scenarios.",
    ),
}


def resolve_weighting_profile(
    requested_profile_id: str | None,
    fallback_to_default: bool = True,
) -> tuple[WeightingProfile, dict[str, object]]:
    requested = (requested_profile_id or DEFAULT_WEIGHTING_PROFILE_ID).strip() or DEFAULT_WEIGHTING_PROFILE_ID
    profile = WEIGHTING_PROFILES.get(requested)
    if profile is not None:
        return profile, {
            "requested": requested_profile_id,
            "applied": profile.profile_id,
            "fallback_applied": False,
            "fallback_reason": None,
        }
    if not fallback_to_default:
        raise ValueError(f"Unknown weighting profile: {requested_profile_id}")
    default_profile = WEIGHTING_PROFILES[DEFAULT_WEIGHTING_PROFILE_ID]
    return default_profile, {
        "requested": requested_profile_id,
        "applied": default_profile.profile_id,
        "fallback_applied": True,
        "fallback_reason": "unknown_profile",
    }
