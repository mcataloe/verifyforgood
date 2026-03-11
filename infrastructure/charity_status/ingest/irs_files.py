from __future__ import annotations

import os

IRS_BASE_URL = "https://www.irs.gov/pub/irs-soi"
IRS_FILES = ["eo1.csv", "eo2.csv", "eo3.csv", "eo4.csv"]


def ingest_bucket() -> str:
    return os.environ["BUCKET"]


def ingest_prefix() -> str:
    return os.environ.get("PREFIX", "eo_bmf/").strip("/") + "/"


def s3_key_for(filename: str) -> str:
    return f"{ingest_prefix()}{filename}"


def source_url_for(filename: str) -> str:
    return f"{IRS_BASE_URL}/{filename}"
