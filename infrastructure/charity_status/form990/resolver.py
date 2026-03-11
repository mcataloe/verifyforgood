from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Callable

import xml.etree.ElementTree as ET

Selector = Callable[[ET.Element], str | None]


class FieldResolver:
    def __init__(self, selectors: list[Selector]):
        self._selectors = selectors

    def resolve(self, root: ET.Element) -> str | None:
        for selector in self._selectors:
            value = selector(root)
            if value is None:
                continue
            cleaned = value.strip()
            if cleaned:
                return cleaned
        return None


def text_xpath(path: str) -> Selector:
    def _extract(root: ET.Element) -> str | None:
        node = root.find(path)
        return node.text if node is not None else None

    return _extract


def bool_xpath(path: str) -> Selector:
    def _extract(root: ET.Element) -> str | None:
        node = root.find(path)
        if node is None or node.text is None:
            return None
        lowered = node.text.strip().lower()
        if lowered in {"true", "1", "y", "yes"}:
            return "true"
        if lowered in {"false", "0", "n", "no"}:
            return "false"
        return None

    return _extract


CANONICAL_FIELD_SELECTORS: dict[str, FieldResolver] = {
    "ein": FieldResolver([
        text_xpath(".//{*}Filer/{*}EIN"),
        text_xpath(".//{*}EIN"),
    ]),
    "tax_year": FieldResolver([
        text_xpath(".//{*}TaxYr"),
        text_xpath(".//{*}TaxYear"),
    ]),
    "tax_period_begin": FieldResolver([
        text_xpath(".//{*}TaxPeriodBeginDt"),
    ]),
    "tax_period_end": FieldResolver([
        text_xpath(".//{*}TaxPeriodEndDt"),
    ]),
    "filing_date": FieldResolver([
        text_xpath(".//{*}ReturnTs"),
        text_xpath(".//{*}TaxPeriodEndDt"),
    ]),
    "amended_return": FieldResolver([
        bool_xpath(".//{*}AmendedReturnInd"),
    ]),
    "return_type": FieldResolver([
        text_xpath(".//{*}ReturnTypeCd"),
    ]),
}


def resolve_field(root: ET.Element, field_name: str) -> str | None:
    resolver = CANONICAL_FIELD_SELECTORS[field_name]
    return resolver.resolve(root)


def resolve_text(root: ET.Element, paths: list[str]) -> str | None:
    resolver = FieldResolver([text_xpath(path) for path in paths])
    return resolver.resolve(root)


def resolve_bool(root: ET.Element, paths: list[str]) -> bool | None:
    resolver = FieldResolver([bool_xpath(path) for path in paths])
    value = resolver.resolve(root)
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def resolve_decimal(root: ET.Element, paths: list[str]) -> float | None:
    value = resolve_text(root, paths)
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("$", "")
    try:
        return float(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None
