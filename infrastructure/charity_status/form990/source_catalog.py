from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

YEAR_PATTERN = re.compile(r"(20[0-9]{2})")

SOURCE_KIND_CSV_INDEX = "csv_index"
SOURCE_KIND_ZIP_ARCHIVE = "zip_archive"


@dataclass(frozen=True)
class Form990SourceArtifact:
    source_year: str
    source_kind: str
    source_url: str
    source_filename: str
    source_archive_key: str
    discovered_at: str
    source_signature: str
    page_url: str
    source_etag: str | None = None
    source_last_modified: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "year": self.source_year,
                "archive_name": self.source_archive_key,
                "source_archive": self.source_archive_key,
                "index_url": self.source_url if self.source_kind == SOURCE_KIND_CSV_INDEX else None,
                "zip_url": self.source_url if self.source_kind == SOURCE_KIND_ZIP_ARCHIVE else None,
                "source_page_url": self.page_url,
            }
        )
        return payload


IrsYearSource = Form990SourceArtifact


@dataclass(frozen=True)
class SourceCatalogDiff:
    new_sources: tuple[dict[str, Any], ...]
    removed_sources: tuple[dict[str, Any], ...]
    changed_sources: tuple[dict[str, Any], ...]
    unchanged_sources: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_sources": list(self.new_sources),
            "removed_sources": list(self.removed_sources),
            "changed_sources": list(self.changed_sources),
            "unchanged_sources": int(self.unchanged_sources),
        }


def sources_to_catalog(sources: list[Form990SourceArtifact]) -> list[dict[str, Any]]:
    return [item.to_dict() for item in sources]


def discovery_state_payload(sources: list[Form990SourceArtifact], now: datetime | None = None) -> dict[str, Any]:
    generated = (now or datetime.now(timezone.utc)).isoformat()
    return {
        "generated_at": generated,
        "count": len(sources),
        "sources": [item.to_dict() for item in sources],
    }


def diff_source_catalog(current: list[Form990SourceArtifact], previous: list[dict[str, Any]]) -> SourceCatalogDiff:
    current_by_key = {_source_identity(item.to_dict()): item.to_dict() for item in current}
    previous_by_key = {_source_identity(item): item for item in previous if isinstance(item, dict)}

    new_sources: list[dict[str, Any]] = []
    removed_sources: list[dict[str, Any]] = []
    changed_sources: list[dict[str, Any]] = []
    unchanged = 0

    for key, entry in current_by_key.items():
        previous_entry = previous_by_key.get(key)
        if previous_entry is None:
            new_sources.append(entry)
            continue
        if _state_tuple(entry) != _state_tuple(previous_entry):
            changed_sources.append({"before": previous_entry, "after": entry})
        else:
            unchanged += 1

    for key, entry in previous_by_key.items():
        if key not in current_by_key:
            removed_sources.append(entry)

    return SourceCatalogDiff(
        new_sources=tuple(sorted(new_sources, key=_entry_sort_key)),
        removed_sources=tuple(sorted(removed_sources, key=_entry_sort_key)),
        changed_sources=tuple(sorted(changed_sources, key=_changed_entry_sort_key)),
        unchanged_sources=unchanged,
    )


def discovery_state_changed(current: list[Form990SourceArtifact], previous: list[dict[str, Any]]) -> bool:
    diff = diff_source_catalog(current, previous)
    return bool(diff.new_sources or diff.removed_sources or diff.changed_sources)


def normalize_configured_sources(catalog: list[dict[str, Any]], now: datetime | None = None, default_page_url: str = "configured://source_catalog") -> list[Form990SourceArtifact]:
    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    artifacts: list[Form990SourceArtifact] = []
    for item in catalog:
        if not isinstance(item, dict):
            continue
        artifacts.extend(_normalize_configured_item(item, discovered_at=discovered_at, default_page_url=default_page_url))
    return sorted(artifacts, key=lambda source: (source.source_year, source.source_kind, source.source_archive_key, source.source_filename))


def source_years(sources: list[Form990SourceArtifact]) -> list[str]:
    return sorted({item.source_year for item in sources if item.source_year})


def select_sources_by_years(sources: list[Form990SourceArtifact], years: set[str]) -> list[Form990SourceArtifact]:
    if not years:
        return []
    return [item for item in sources if item.source_year in years]


def derive_source_year(value: str) -> str | None:
    match = YEAR_PATTERN.search(str(value))
    return match.group(1) if match else None


def derive_source_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or str(url)
    return path.rstrip("/").split("/")[-1]


def derive_source_archive_key(value: str) -> str:
    stem = str(value).strip()
    if not stem:
        return "unknown_source"
    filename = derive_source_filename(stem)
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]
    normalized = re.sub(r"[^a-z0-9]+", "_", filename.lower()).strip("_")
    return normalized or "unknown_source"


def infer_source_kind(url: str, explicit_kind: str | None = None) -> str | None:
    if explicit_kind in {SOURCE_KIND_CSV_INDEX, SOURCE_KIND_ZIP_ARCHIVE}:
        return explicit_kind
    lowered = str(url).lower()
    if lowered.endswith(".csv"):
        return SOURCE_KIND_CSV_INDEX
    if lowered.endswith(".zip"):
        return SOURCE_KIND_ZIP_ARCHIVE
    return None


def compute_source_signature(
    *,
    source_year: str,
    source_kind: str,
    source_url: str,
    source_filename: str,
    source_archive_key: str,
    page_url: str,
    source_etag: str | None,
    source_last_modified: str | None,
) -> str:
    parts = [
        source_year,
        source_kind,
        source_url,
        source_filename,
        source_archive_key,
        page_url,
        source_etag or "",
        source_last_modified or "",
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def build_source_artifact(
    *,
    source_year: str,
    source_kind: str,
    source_url: str,
    source_filename: str | None,
    source_archive_key: str | None,
    discovered_at: str,
    page_url: str,
    source_etag: str | None = None,
    source_last_modified: str | None = None,
    source_signature: str | None = None,
) -> Form990SourceArtifact:
    filename = (source_filename or derive_source_filename(source_url) or "").strip()
    archive_key = (source_archive_key or derive_source_archive_key(filename or source_url)).strip()
    signature = source_signature or compute_source_signature(
        source_year=source_year,
        source_kind=source_kind,
        source_url=source_url,
        source_filename=filename,
        source_archive_key=archive_key,
        page_url=page_url,
        source_etag=source_etag,
        source_last_modified=source_last_modified,
    )
    return Form990SourceArtifact(
        source_year=source_year,
        source_kind=source_kind,
        source_url=source_url,
        source_filename=filename,
        source_archive_key=archive_key,
        discovered_at=discovered_at,
        source_signature=signature,
        page_url=page_url,
        source_etag=source_etag,
        source_last_modified=source_last_modified,
    )


def _normalize_configured_item(item: dict[str, Any], discovered_at: str, default_page_url: str) -> list[Form990SourceArtifact]:
    page_url = str(item.get("page_url") or item.get("source_page_url") or default_page_url).strip() or default_page_url
    source_year = str(item.get("source_year") or item.get("year") or "").strip()
    archive_key = str(item.get("source_archive_key") or item.get("archive_name") or item.get("source_archive") or "").strip() or None
    filename = str(item.get("source_filename") or "").strip() or None
    source_etag = _as_optional_text(item.get("source_etag") or item.get("etag"))
    source_last_modified = _as_optional_text(item.get("source_last_modified") or item.get("last_modified"))
    explicit_signature = _as_optional_text(item.get("source_signature"))

    if str(item.get("source_url") or "").strip():
        url = str(item.get("source_url") or "").strip()
        kind = infer_source_kind(url, explicit_kind=_as_optional_text(item.get("source_kind")))
        if not kind:
            return []
        year = source_year or derive_source_year(f"{url} {filename or ''} {archive_key or ''}") or ""
        if not year:
            return []
        return [
            build_source_artifact(
                source_year=year,
                source_kind=kind,
                source_url=url,
                source_filename=filename,
                source_archive_key=archive_key,
                discovered_at=discovered_at,
                page_url=page_url,
                source_etag=source_etag,
                source_last_modified=source_last_modified,
                source_signature=explicit_signature,
            )
        ]

    artifacts: list[Form990SourceArtifact] = []
    for key, kind in (("index_url", SOURCE_KIND_CSV_INDEX), ("zip_url", SOURCE_KIND_ZIP_ARCHIVE)):
        url = str(item.get(key) or "").strip()
        if not url:
            continue
        year = source_year or derive_source_year(f"{url} {filename or ''} {archive_key or ''}") or ""
        if not year:
            continue
        artifacts.append(
            build_source_artifact(
                source_year=year,
                source_kind=kind,
                source_url=url,
                source_filename=filename,
                source_archive_key=archive_key,
                discovered_at=discovered_at,
                page_url=page_url,
                source_etag=source_etag,
                source_last_modified=source_last_modified,
                source_signature=explicit_signature,
            )
        )
    return artifacts


def _source_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("source_year") or entry.get("year") or "").strip(),
        str(entry.get("source_kind") or "").strip(),
        str(entry.get("source_archive_key") or entry.get("archive_name") or entry.get("source_archive") or "").strip(),
    )


def _state_tuple(entry: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(entry.get("source_url") or entry.get("index_url") or entry.get("zip_url") or "").strip(),
        str(entry.get("source_filename") or "").strip(),
        str(entry.get("page_url") or entry.get("source_page_url") or "").strip(),
        str(entry.get("source_signature") or "").strip(),
        str(entry.get("source_etag") or entry.get("etag") or "").strip(),
        str(entry.get("source_last_modified") or entry.get("last_modified") or "").strip(),
        str(entry.get("source_kind") or "").strip(),
    )


def _entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("source_year") or entry.get("year") or "").strip(),
        str(entry.get("source_kind") or "").strip(),
        str(entry.get("source_archive_key") or entry.get("archive_name") or entry.get("source_archive") or "").strip(),
        str(entry.get("source_filename") or "").strip(),
    )


def _changed_entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    after = entry.get("after") if isinstance(entry.get("after"), dict) else {}
    return _entry_sort_key(after)


def _as_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
