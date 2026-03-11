from __future__ import annotations

import re


class EINValidationError(ValueError):
    pass


_NON_DIGIT = re.compile(r"\D+")
_ALLOWED_PATTERN = re.compile(r"^[\d\-\s]+$")


def normalize_ein(raw_ein: str | None) -> str:
    if raw_ein is None:
        raise EINValidationError("EIN is required")

    stripped = raw_ein.strip()
    if not stripped:
        raise EINValidationError("EIN is required")

    if not _ALLOWED_PATTERN.match(stripped):
        raise EINValidationError("EIN contains invalid characters")

    digits = _NON_DIGIT.sub("", stripped)

    if len(digits) != 9:
        raise EINValidationError("EIN must be exactly 9 digits")

    return digits


def format_ein(normalized_ein: str) -> str:
    if len(normalized_ein) != 9 or not normalized_ein.isdigit():
        raise EINValidationError("Cannot format invalid EIN")
    return f"{normalized_ein[:2]}-{normalized_ein[2:]}"
