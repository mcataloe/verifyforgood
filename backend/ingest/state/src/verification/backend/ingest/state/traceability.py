from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from verification.backend.ingest.state.models import RawPayloadRef
from verification.backend.ingest.state.normalization import stable_payload_hash


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_raw_payload_ref(
    *,
    payload: dict[str, Any],
    source_identifier: str,
    parser_version: str,
    retrieved_at: str | None = None,
    storage_locator: str | None = None,
) -> RawPayloadRef:
    return RawPayloadRef(
        source_identifier=source_identifier,
        retrieved_at=retrieved_at or now_utc_iso(),
        raw_hash=stable_payload_hash(payload),
        parser_version=parser_version,
        storage_locator=storage_locator,
    )

