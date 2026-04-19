from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser


@dataclass(frozen=True)
class PortalHtmlCell:
    text: str
    href: str | None = None


class _TableParser(HTMLParser):
    def __init__(self, *, table_id: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self._target_table_id = table_id
        self._table_depth = 0
        self._capturing = table_id is None
        self._current_row: list[PortalHtmlCell] = []
        self._rows: list[list[PortalHtmlCell]] = []
        self._in_cell = False
        self._cell_chunks: list[str] = []
        self._cell_href: str | None = None

    @property
    def rows(self) -> list[list[PortalHtmlCell]]:
        return self._rows

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs}
        if tag == "table":
            if self._capturing or attrs_dict.get("id") == self._target_table_id:
                self._capturing = True
                self._table_depth += 1
            return
        if not self._capturing:
            return
        if tag == "tr":
            self._current_row = []
            return
        if tag in {"td", "th"}:
            self._in_cell = True
            self._cell_chunks = []
            self._cell_href = None
            return
        if tag == "a" and self._in_cell:
            href = attrs_dict.get("href")
            if href:
                self._cell_href = href
            return
        if tag == "br" and self._in_cell:
            self._cell_chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if not self._capturing:
            return
        if tag == "table":
            self._table_depth -= 1
            if self._table_depth <= 0:
                self._capturing = False
            return
        if tag in {"td", "th"} and self._in_cell:
            text = clean_portal_text("".join(self._cell_chunks))
            self._current_row.append(PortalHtmlCell(text=text, href=self._cell_href))
            self._in_cell = False
            self._cell_chunks = []
            self._cell_href = None
            return
        if tag == "tr" and self._current_row:
            self._rows.append(list(self._current_row))
            self._current_row = []

    def handle_data(self, data: str) -> None:
        if self._capturing and self._in_cell:
            self._cell_chunks.append(data)


def extract_table_records(html: str, *, table_id: str | None = None) -> list[dict[str, PortalHtmlCell]]:
    parser = _TableParser(table_id=table_id)
    parser.feed(html or "")
    rows = [row for row in parser.rows if any(cell.text for cell in row)]
    if not rows:
        return []
    headers = [cell.text for cell in rows[0]]
    records: list[dict[str, PortalHtmlCell]] = []
    for row in rows[1:]:
        padded = list(row) + [PortalHtmlCell(text="")] * max(0, len(headers) - len(row))
        records.append(
            {
                headers[index]: padded[index]
                for index in range(min(len(headers), len(padded)))
                if headers[index]
            }
        )
    return records


def extract_hidden_inputs(html: str) -> dict[str, str]:
    class _HiddenInputParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.items: dict[str, str] = {}

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "input":
                return
            attrs_dict = {key.lower(): value for key, value in attrs}
            if attrs_dict.get("type") != "hidden":
                return
            name = attrs_dict.get("name")
            if not name:
                return
            self.items[name] = attrs_dict.get("value") or ""

    parser = _HiddenInputParser()
    parser.feed(html or "")
    return parser.items


def clean_portal_text(value: str | None) -> str:
    return " ".join(unescape(str(value or "")).replace("\xa0", " ").split())
