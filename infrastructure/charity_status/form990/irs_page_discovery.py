from __future__ import annotations

"""Legacy compatibility discovery for explicit irs_page mode only."""

import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

from charity_status.form990.source_catalog import (
    IrsYearSource,
    SOURCE_KIND_CSV_INDEX,
    SOURCE_KIND_ZIP_ARCHIVE,
    build_source_artifact,
    derive_source_archive_key,
    derive_source_year,
    diff_source_catalog,
    discovery_state_changed,
    discovery_state_payload,
    sources_to_catalog,
)

__all__ = [
    "IrsYearSource",
    "discover_irs_form990_sources",
    "diff_source_catalog",
    "discovery_state_changed",
    "discovery_state_payload",
    "sources_to_catalog",
]


class _AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._in_anchor = False
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = ""
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value
                break
        self._in_anchor = True
        self._href = href
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a":
            return
        if self._in_anchor and self._href:
            text = " ".join(part.strip() for part in self._parts if part.strip()).strip()
            self.anchors.append((self._href, text))
        self._in_anchor = False
        self._href = None
        self._parts = []


def discover_irs_form990_sources(page_url: str, timeout_seconds: int = 60, now: datetime | None = None) -> list[IrsYearSource]:
    request = urllib.request.Request(page_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"discovery page download failed with status {response.status}")
        html = response.read().decode("utf-8", errors="replace")
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")

    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    parser = _AnchorParser()
    parser.feed(html)

    sources: list[IrsYearSource] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_href, text in parser.anchors:
        href = urllib.parse.urljoin(page_url, (raw_href or "").strip())
        if not href:
            continue
        normalized = href.lower()
        if not _looks_like_form990_source(href, text):
            continue
        kind = _source_kind_from_link(normalized, text)
        if not kind:
            continue
        year = derive_source_year(f"{href} {text}")
        if not year:
            continue
        filename = href.rstrip("/").split("/")[-1]
        archive_key = derive_source_archive_key(filename)
        identity = (year, kind, archive_key)
        if identity in seen:
            continue
        seen.add(identity)
        sources.append(
            build_source_artifact(
                source_year=year,
                source_kind=kind,
                source_url=href,
                source_filename=filename,
                source_archive_key=archive_key,
                discovered_at=discovered_at,
                page_url=page_url,
                source_etag=etag,
                source_last_modified=last_modified,
            )
        )
    return sorted(sources, key=lambda source: (source.source_year, source.source_kind, source.source_archive_key, source.source_filename))


def _looks_like_form990_source(href: str, text: str) -> bool:
    href_lower = href.lower()
    lowered = f"{href} {text}".lower()
    if not (href_lower.endswith(".zip") or href_lower.endswith(".csv")):
        return False
    if not derive_source_year(lowered):
        return False
    return "/990/" in lowered or "form 990" in lowered or "990 xml" in lowered or "epostcard" in lowered


def _source_kind_from_link(normalized_href: str, text: str) -> str | None:
    lowered = f"{normalized_href} {text}".lower()
    if normalized_href.endswith(".csv"):
        return SOURCE_KIND_CSV_INDEX
    if normalized_href.endswith(".zip") and ("xml" in lowered or "/990/" in lowered or "epostcard" in lowered):
        return SOURCE_KIND_ZIP_ARCHIVE
    return None
