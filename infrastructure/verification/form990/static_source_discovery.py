from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from verification.form990.source_catalog import (
    Form990SourceArtifact,
    build_source_artifact,
    derive_source_archive_key,
    derive_source_filename,
    derive_source_year,
    infer_source_kind,
)

STATIC_MANIFEST_PAGE_URL = "static_manifest://form990/Form990Links.txt"
GENERATED_NEXT_YEAR_PAGE_URL = "generated://form990-next-year"
URL_PATTERN = re.compile(r"https?://[^\s]+")
INDEX_FILENAME_PATTERN = re.compile(r"^index_(20[0-9]{2})\.csv$")
TEOS_FILENAME_PATTERN = re.compile(r"^(20[0-9]{2})_TEOS_XML_[0-9A-Z]+\.zip$", re.IGNORECASE)

__all__ = [
    "GENERATED_NEXT_YEAR_PAGE_URL",
    "STATIC_MANIFEST_PAGE_URL",
    "discover_static_form990_sources",
]


def discover_static_form990_sources(
    now: datetime | None = None,
    manifest_path: Path | None = None,
    enable_next_year_generation: bool = True,
) -> list[Form990SourceArtifact]:
    path = manifest_path or _default_manifest_path()
    text = path.read_text(encoding="utf-8-sig")
    sources = _parse_manifest_text(text, now=now)
    if not enable_next_year_generation:
        return sources
    return _dedupe_and_sort_sources([*sources, *_generate_next_year_sources(sources, now=now)])


def _default_manifest_path() -> Path:
    path = Path(__file__).with_name("Form990Links.txt")
    if path.exists():
        return path
    raise FileNotFoundError(f"Form 990 static manifest not found at {path}")


def _parse_manifest_text(text: str, now: datetime | None = None) -> list[Form990SourceArtifact]:
    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    artifacts: list[Form990SourceArtifact] = []

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
        artifacts.append(artifact)

    if not artifacts:
        raise ValueError("Form 990 static manifest did not contain any parseable CSV or ZIP source URLs")

    return _dedupe_and_sort_sources(artifacts)


def _generate_next_year_sources(
    explicit_sources: list[Form990SourceArtifact],
    now: datetime | None = None,
) -> list[Form990SourceArtifact]:
    if not explicit_sources:
        return []

    highest_explicit_year = max(explicit_sources, key=lambda item: item.source_year).source_year
    template_sources = [
        source
        for source in explicit_sources
        if source.source_year == highest_explicit_year and _is_next_year_template_source(source)
    ]
    if not template_sources:
        return []

    next_year = str(int(highest_explicit_year) + 1)
    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    generated_page_url = f"{GENERATED_NEXT_YEAR_PAGE_URL}/{highest_explicit_year}-to-{next_year}"
    generated: list[Form990SourceArtifact] = []

    for source in template_sources:
        source_url = _replace_year_tokens(source.source_url, source.source_year, next_year)
        if not source_url or source_url == source.source_url:
            continue
        source_filename = derive_source_filename(source_url)
        generated.append(
            build_source_artifact(
                source_year=next_year,
                source_kind=source.source_kind,
                source_url=source_url,
                source_filename=source_filename,
                source_archive_key=derive_source_archive_key(source_filename),
                discovered_at=discovered_at,
                page_url=generated_page_url,
            )
        )

    return _dedupe_and_sort_sources(generated)


def _is_next_year_template_source(source: Form990SourceArtifact) -> bool:
    filename = str(source.source_filename or "").strip()
    if source.source_kind == "csv_index":
        return bool(INDEX_FILENAME_PATTERN.fullmatch(filename))
    if source.source_kind == "zip_archive":
        return bool(TEOS_FILENAME_PATTERN.fullmatch(filename))
    return False


def _replace_year_tokens(source_url: str, source_year: str, next_year: str) -> str:
    replacements = [
        (f"/{source_year}/", f"/{next_year}/"),
        (f"index_{source_year}.csv", f"index_{next_year}.csv"),
        (f"{source_year}_TEOS_XML_", f"{next_year}_TEOS_XML_"),
    ]
    updated = source_url
    for original, replacement in replacements:
        updated = updated.replace(original, replacement)
    return updated


def _dedupe_and_sort_sources(sources: list[Form990SourceArtifact]) -> list[Form990SourceArtifact]:
    artifacts_by_identity: dict[tuple[str, str, str], Form990SourceArtifact] = {}
    for artifact in sources:
        identity = (artifact.source_year, artifact.source_kind, artifact.source_archive_key)
        artifacts_by_identity.setdefault(identity, artifact)
    return sorted(
        artifacts_by_identity.values(),
        key=lambda source: (source.source_year, source.source_kind, source.source_archive_key, source.source_filename),
    )

