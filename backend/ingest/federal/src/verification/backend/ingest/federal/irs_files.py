from __future__ import annotations

IRS_BASE_URL = "https://www.irs.gov/pub/irs-soi"
IRS_FILES = ["eo1.csv", "eo2.csv", "eo3.csv", "eo4.csv"]


def source_url_for(filename: str) -> str:
    return f"{IRS_BASE_URL}/{filename}"
