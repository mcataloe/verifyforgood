from __future__ import annotations

from datetime import datetime, timezone

_STATUS_INACTIVE = {"2", "4", "8", "revoked", "terminated", "inactive"}
_STATUS_ACTIVE = {"1", "3", "5", "active"}

_DEDUCTIBILITY_TRUE = {"1", "2", "3", "4", "5", "yes", "y", "true"}
_DEDUCTIBILITY_FALSE = {"0", "n", "no", "false"}

_SUBSECTION_MAP = {
    "03": "Charitable Organization",
    "04": "Social Welfare Organization",
    "05": "Labor and Agricultural Organization",
    "06": "Business League",
    "07": "Social and Recreational Club",
    "08": "Fraternal Beneficiary Society",
    "09": "Voluntary Employees Beneficiary Association",
    "10": "Domestic Fraternal Society",
    "19": "Post or Organization of Past or Present Members of the Armed Forces",
}

_NTEE_CATEGORY_MAP = {
    "A": "Arts, Culture and Humanities",
    "B": "Education",
    "C": "Environment",
    "D": "Animal Related",
    "E": "Health Care",
    "F": "Mental Health and Crisis Intervention",
    "G": "Diseases, Disorders and Medical Disciplines",
    "H": "Medical Research",
    "I": "Crime and Legal",
    "J": "Employment",
    "K": "Food, Agriculture and Nutrition",
    "L": "Housing and Shelter",
    "M": "Public Safety",
    "N": "Recreation and Sports",
    "O": "Youth Development",
    "P": "Human Services",
    "Q": "International and Foreign Affairs",
    "R": "Civil Rights and Social Action",
    "S": "Community Improvement and Capacity Building",
    "T": "Philanthropy and Volunteerism",
    "U": "Science and Technology",
    "V": "Social Science",
    "W": "Public and Societal Benefit",
    "X": "Religion Related",
    "Y": "Mutual and Membership Benefit",
    "Z": "Unknown/Unclassified",
}


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def _normalize_code(value: object | None) -> str | None:
    cleaned = _clean(value)
    if not cleaned:
        return None

    normalized = cleaned.lower()
    if normalized.isdigit():
        return str(int(normalized))
    if normalized.endswith(".0") and normalized[:-2].isdigit():
        return str(int(normalized[:-2]))
    return normalized


def map_irs_status(value: object | None) -> str:
    normalized = _normalize_code(value)
    if not normalized:
        return "unknown"
    if normalized in _STATUS_ACTIVE:
        return "active"
    if normalized in _STATUS_INACTIVE:
        return "inactive"
    return "unknown"


def map_deductibility(value: object | None) -> bool | None:
    normalized = _normalize_code(value)
    if not normalized:
        return None
    if normalized in _DEDUCTIBILITY_TRUE:
        return True
    if normalized in _DEDUCTIBILITY_FALSE:
        return False
    return None


def map_entity_type(subsection: object | None) -> str | None:
    cleaned = _clean(subsection)
    if not cleaned:
        return None
    return _SUBSECTION_MAP.get(cleaned, cleaned)


def map_ntee_category(ntee_cd: object | None) -> str | None:
    cleaned = _clean(ntee_cd)
    if not cleaned:
        return None
    prefix = cleaned[0].upper()
    return _NTEE_CATEGORY_MAP.get(prefix, cleaned)


def recent_990_on_file(tax_period: object | None, years_back: int = 3) -> bool | None:
    cleaned = _clean(tax_period)
    if not cleaned:
        return None
    if len(cleaned) != 6 or not cleaned.isdigit():
        return None

    year = int(cleaned[:4])
    month = int(cleaned[4:6])
    if month < 1 or month > 12:
        return None

    now = datetime.now(timezone.utc)
    min_year = now.year - years_back
    return year >= min_year
