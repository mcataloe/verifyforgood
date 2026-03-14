from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from charity_status.form990.source_catalog import (
    Form990SourceArtifact,
    build_source_artifact,
    derive_source_archive_key,
    derive_source_filename,
    derive_source_year,
    infer_source_kind,
)

STATIC_MANIFEST_PAGE_URL = "static_manifest://form990/Form990Links.txt"
URL_PATTERN = re.compile(r"https?://[^\s]+")

__all__ = [
    "STATIC_MANIFEST_PAGE_URL",
    "discover_static_form990_sources",
]


def discover_static_form990_sources(
    now: datetime | None = None,
    manifest_path: Path | None = None,
) -> list[Form990SourceArtifact]:
    path = manifest_path or _default_manifest_path()
    text = path.read_text(encoding="utf-8-sig")
    return _parse_manifest_text(text, now=now)


def _default_manifest_path() -> Path:
    path = Path(__file__).with_name("Form990Links.txt")
    if path.exists():
        return path
    raise FileNotFoundError(f"Form 990 static manifest not found at {path}")


def _parse_manifest_text(text: str, now: datetime | None = None) -> list[Form990SourceArtifact]:
    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    artifacts_by_identity: dict[tuple[str, str, str], Form990SourceArtifact] = {}

    for raw_url in URL_PATTERN.findall(text):
        source_url = raw_url.strip().rstrip(".,;)]}")
        if not source_url:
            continue
        source_kind = infer_source_kind(source_url)
        if not source_kind:
            continue
        source_filename = derive_source_filename(source_url)
        source_year = derive_source_year(f"{source_url} {source_filename}") or ""
        if not source_year:
            continue
        source_archive_key = derive_source_archive_key(source_filename)
        artifact = build_source_artifact(
            source_year=source_year,
            source_kind=source_kind,
            source_url=source_url,
            source_filename=source_filename,
            source_archive_key=source_archive_key,
            discovered_at=discovered_at,
            page_url=STATIC_MANIFEST_PAGE_URL,
        )
        identity = (artifact.source_year, artifact.source_kind, artifact.source_archive_key)
        artifacts_by_identity.setdefault(identity, artifact)

    return sorted(
        artifacts_by_identity.values(),
        key=lambda source: (source.source_year, source.source_kind, source.source_archive_key, source.source_filename),
    )
