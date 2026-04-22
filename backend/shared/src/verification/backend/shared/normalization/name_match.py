from __future__ import annotations

import re
from typing import Any

_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")
_MULTI_SPACE = re.compile(r"\s+")
_SUFFIX_NOISE = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "llc",
    "ltd",
    "limited",
}


def compare_names(provided_name: str | None, irs_name: str | None) -> dict[str, Any]:
    if not provided_name:
        return {
            "provided_name": None,
            "irs_name": irs_name,
            "name_match": None,
            "match_confidence": None,
        }

    if not irs_name:
        return {
            "provided_name": provided_name,
            "irs_name": irs_name,
            "name_match": False,
            "match_confidence": "none",
        }

    provided_clean = _normalize_for_match(provided_name)
    irs_clean = _normalize_for_match(irs_name)

    if provided_name.strip().lower() == irs_name.strip().lower():
        confidence = "exact"
        is_match = True
    elif provided_clean == irs_clean and provided_clean:
        confidence = "normalized"
        is_match = True
    elif _weak_similarity(provided_clean, irs_clean):
        confidence = "weak"
        is_match = False
    else:
        confidence = "none"
        is_match = False

    return {
        "provided_name": provided_name,
        "irs_name": irs_name,
        "name_match": is_match,
        "match_confidence": confidence,
    }


def _normalize_for_match(value: str) -> str:
    lowered = value.lower().strip()
    cleaned = _NON_ALNUM.sub(" ", lowered)
    tokens = [token for token in _MULTI_SPACE.sub(" ", cleaned).split(" ") if token and token not in _SUFFIX_NOISE]
    return " ".join(tokens)


def _weak_similarity(left: str, right: str) -> bool:
    if not left or not right:
        return False
    left_tokens = set(left.split(" "))
    right_tokens = set(right.split(" "))
    if len(left_tokens) < 2 or len(right_tokens) < 2:
        return False
    overlap = len(left_tokens.intersection(right_tokens))
    baseline = min(len(left_tokens), len(right_tokens))
    return (overlap / baseline) >= 0.7
