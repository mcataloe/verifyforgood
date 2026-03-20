from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable

TEOS_ZIP_FILENAME_TEMPLATE = r"^{year}_TEOS_XML_[0-9A-Z]+\.zip$"


@dataclass(frozen=True)
class TeosZipDiscoveryRecord:
    tax_year: str
    source_url: str
    source_filename: str
    zip_basename: str
    discovered_at: str
    page_url: str

    def to_dict(self) -> dict[str, str]:
        return {
            "tax_year": self.tax_year,
            "source_url": self.source_url,
            "source_filename": self.source_filename,
            "zip_basename": self.zip_basename,
            "discovered_at": self.discovered_at,
            "page_url": self.page_url,
        }


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)
                return


def fetch_teos_download_page_html(page_url: str, timeout_seconds: int = 60) -> str:
    request = urllib.request.Request(page_url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"TEOS download page fetch failed with status {response.status}")
        return response.read().decode("utf-8", errors="replace")


def parse_teos_zip_links(
    html: str,
    *,
    page_url: str,
    target_year: str,
    now: datetime | None = None,
) -> list[TeosZipDiscoveryRecord]:
    year = str(target_year).strip()
    if not re.fullmatch(r"20[0-9]{2}", year):
        raise ValueError("target_year must be a four-digit year")

    discovered_at = (now or datetime.now(timezone.utc)).isoformat()
    parser = _AnchorParser()
    parser.feed(html)

    filename_pattern = re.compile(TEOS_ZIP_FILENAME_TEMPLATE.format(year=re.escape(year)), re.IGNORECASE)
    records_by_basename: dict[str, TeosZipDiscoveryRecord] = {}
    for raw_href in parser.hrefs:
        absolute_url = urllib.parse.urljoin(page_url, str(raw_href).strip())
        filename = absolute_url.rstrip("/").split("/")[-1]
        if not filename_pattern.fullmatch(filename):
            continue
        zip_basename = filename.rsplit(".", 1)[0]
        records_by_basename.setdefault(
            zip_basename,
            TeosZipDiscoveryRecord(
                tax_year=year,
                source_url=absolute_url,
                source_filename=filename,
                zip_basename=zip_basename,
                discovered_at=discovered_at,
                page_url=page_url,
            ),
        )

    return sorted(records_by_basename.values(), key=lambda item: (item.tax_year, item.zip_basename, item.source_url))


def discover_teos_zip_links(
    page_url: str,
    *,
    target_year: str,
    timeout_seconds: int = 60,
    now: datetime | None = None,
    fetcher: Callable[[str, int], str] | None = None,
) -> list[TeosZipDiscoveryRecord]:
    html_fetcher = fetcher or fetch_teos_download_page_html
    html = html_fetcher(page_url, timeout_seconds)
    return parse_teos_zip_links(html, page_url=page_url, target_year=target_year, now=now)


__all__ = [
    "TeosZipDiscoveryRecord",
    "discover_teos_zip_links",
    "fetch_teos_download_page_html",
    "parse_teos_zip_links",
]
