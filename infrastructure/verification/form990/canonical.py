from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from verification.form990.parser import ParsedXml, parse_xml


CANONICAL_FORM990_PARSER_VERSION = "form990.xml_parser.v1"
CANONICAL_FORM990_CANONICALIZATION_VERSION = "form990.raw_filing_json.v1"
ATTRS_KEY = "_attrs"
VALUE_KEY = "_value"


def canonicalize_xml_to_json(content: bytes) -> dict[str, Any]:
    return canonicalize_parsed_xml(parse_xml(content))


def canonicalize_parsed_xml(parsed_xml: ParsedXml) -> dict[str, Any]:
    root = parsed_xml.root
    return {_strip_namespace(root.tag): _canonicalize_element(root)}


def compute_normalized_xml_content_hash(content: bytes) -> str:
    digest = hashlib.sha256()
    pending = b""
    first_chunk = True

    for chunk in _iter_chunks(content):
        if first_chunk:
            first_chunk = False
            if chunk.startswith(b"\xef\xbb\xbf"):
                chunk = chunk[3:]
        pending += chunk
        pending = pending.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        lines = pending.split(b"\n")
        pending = lines.pop()
        for line in lines:
            digest.update(line.rstrip(b" \t\r\n\f\v"))
            digest.update(b"\n")

    if pending:
        digest.update(pending.rstrip(b" \t\r\n\f\v"))

    return digest.hexdigest()


def hash_local_xml_file(path: str) -> str:
    return compute_normalized_xml_content_hash(Path(path).read_bytes())


def _iter_chunks(content: bytes, *, chunk_size: int = 64 * 1024):
    for index in range(0, len(content), chunk_size):
        yield content[index:index + chunk_size]


def _canonicalize_element(element: Any) -> Any:
    attrs = {
        _strip_namespace(key): value
        for key, value in sorted(element.attrib.items(), key=lambda item: _strip_namespace(item[0]))
        if str(value).strip()
    }
    children = list(element)
    text = _clean_text(element.text)

    if not children:
        if attrs and text is not None:
            return {
                ATTRS_KEY: attrs,
                VALUE_KEY: text,
            }
        if attrs:
            return {ATTRS_KEY: attrs}
        return text or ""

    grouped_children: dict[str, list[Any]] = {}
    for child in children:
        key = _strip_namespace(child.tag)
        grouped_children.setdefault(key, []).append(_canonicalize_element(child))

    payload: dict[str, Any] = {}
    if attrs:
        payload[ATTRS_KEY] = attrs
    if text is not None:
        payload[VALUE_KEY] = text
    for key in sorted(grouped_children):
        values = grouped_children[key]
        payload[key] = values[0] if len(values) == 1 else values
    return payload


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

