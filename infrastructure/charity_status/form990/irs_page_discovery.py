from __future__ import annotations

import hashlib
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

YEAR_PATTERN = re.compile(r"(20[0-9]{2})")


@dataclass(frozen=True)
class IrsYearSource:
    year: str
    archive_name: str
    zip_url: str | None
    index_url: str | None
    source_page_url: str
    discovered_at: str
    source_etag: str | None = None
    source_last_modified: str | None = None
    source_signature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    links_by_year = _collect_links_by_year(parser.anchors, base_url=page_url)

    sources: list[IrsYearSource] = []
    for year in sorted(links_by_year.keys()):
        entries = links_by_year[year]
        for archive_key in sorted(entries.keys()):
            urls = entries[archive_key]
            if not urls.get("zip_url") and not urls.get("index_url"):
                continue
            archive_name = f"irs-page-{year}-{archive_key}"
            signature = _signature_for(
                year=year,
                archive_name=archive_name,
                zip_url=urls.get("zip_url"),
                index_url=urls.get("index_url"),
                source_page_url=page_url,
                etag=etag,
                last_modified=last_modified,
            )
            sources.append(
                IrsYearSource(
                    year=year,
                    archive_name=archive_name,
                    zip_url=urls.get("zip_url"),
                    index_url=urls.get("index_url"),
                    source_page_url=page_url,
                    discovered_at=discovered_at,
                    source_etag=etag,
                    source_last_modified=last_modified,
                    source_signature=signature,
                )
            )
    return sources


def sources_to_catalog(sources: list[IrsYearSource]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for source in sources:
        catalog.append(
            {
                "year": source.year,
                "source_year": source.year,
                "archive_name": source.archive_name,
                "source_archive": source.archive_name,
                "index_url": source.index_url,
                "zip_url": source.zip_url,
                "source_page_url": source.source_page_url,
                "source_signature": source.source_signature,
                "source_etag": source.source_etag,
                "source_last_modified": source.source_last_modified,
                "discovered_at": source.discovered_at,
            }
        )
    return catalog


def discovery_state_payload(sources: list[IrsYearSource], now: datetime | None = None) -> dict[str, Any]:
    generated = (now or datetime.now(timezone.utc)).isoformat()
    return {
        "generated_at": generated,
        "count": len(sources),
        "sources": [item.to_dict() for item in sources],
    }


def discovery_state_changed(current: list[IrsYearSource], previous: list[dict[str, Any]]) -> bool:
    current_norm = sorted([_state_tuple(item.to_dict()) for item in current])
    previous_norm = sorted([_state_tuple(item) for item in previous if isinstance(item, dict)])
    return current_norm != previous_norm


def _collect_links_by_year(anchors: list[tuple[str, str]], base_url: str) -> dict[str, dict[str, dict[str, str]]]:
    by_year: dict[str, dict[str, dict[str, str]]] = {}
    for raw_href, text in anchors:
        href = urllib.parse.urljoin(base_url, (raw_href or "").strip())
        if not href:
            continue
        normalized = href.lower()
        if not (normalized.endswith(".zip") or normalized.endswith(".csv")):
            continue
        year = _extract_year(f"{href} {text}")
        if not year:
            continue
        archive_key = _archive_key_from_link(href, year)
        year_bucket = by_year.setdefault(year, {})
        bucket = year_bucket.setdefault(archive_key, {})
        if normalized.endswith(".zip") and "xml" in normalized:
            bucket["zip_url"] = href
        if normalized.endswith(".csv") and ("index" in normalized or "xml" in normalized):
            bucket["index_url"] = href
    return by_year


def _extract_year(value: str) -> str | None:
    match = YEAR_PATTERN.search(str(value))
    return match.group(1) if match else None


def _archive_key_from_link(href: str, year: str) -> str:
    base = href.rstrip("/").split("/")[-1].lower()
    stem = base.rsplit(".", 1)[0]
    normalized = stem.replace("download990xml_", "").replace("index_", "")
    if year in normalized:
        suffix = normalized.split(year, 1)[1].strip("_-")
        if suffix:
            return f"{year}_{suffix}".replace("-", "_")
    return normalized.replace("-", "_")


def _signature_for(year: str, archive_name: str, zip_url: str | None, index_url: str | None, source_page_url: str, etag: str | None, last_modified: str | None) -> str:
    parts = [year, archive_name, zip_url or "", index_url or "", source_page_url, etag or "", last_modified or ""]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


def _state_tuple(entry: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(entry.get("year") or "").strip(),
        str(entry.get("archive_name") or "").strip(),
        str(entry.get("zip_url") or "").strip(),
        str(entry.get("index_url") or "").strip(),
        str(entry.get("source_signature") or "").strip(),
    )
