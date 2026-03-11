from __future__ import annotations

import json
import os

from charity_status.api import error_response, json_response
from charity_status.form990 import Form990IngestService

BUCKET = os.environ.get("BUCKET")
RAW_PREFIX = os.environ.get("FORM990_RAW_PREFIX", "form990/raw/")
METADATA_PREFIX = os.environ.get("FORM990_METADATA_PREFIX", "form990/normalized/metadata/")
MANIFEST_PREFIX = os.environ.get("FORM990_MANIFEST_PREFIX", "form990/normalized/manifests/")


def handler(event, context):
    if not BUCKET:
        return error_response(500, "BUCKET environment variable is required")

    payload = event.get("records") if isinstance(event, dict) else None
    download_raw = bool(event.get("download_raw")) if isinstance(event, dict) else False

    if payload is None and isinstance(event, dict) and event.get("body"):
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            return error_response(400, "Request body must be valid JSON")
        payload = body.get("records") if isinstance(body, dict) else None
        download_raw = bool(body.get("download_raw")) if isinstance(body, dict) else download_raw

    if payload is None:
        payload = []

    if not isinstance(payload, list):
        return error_response(400, "records must be an array")

    service = Form990IngestService(
        bucket=BUCKET,
        raw_prefix=RAW_PREFIX,
        metadata_prefix=METADATA_PREFIX,
        manifest_prefix=MANIFEST_PREFIX,
    )
    result = service.ingest_index_payload(payload=payload, download_raw=download_raw)
    return json_response(200, result)
