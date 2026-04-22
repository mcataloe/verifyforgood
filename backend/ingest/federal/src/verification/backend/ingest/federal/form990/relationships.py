from __future__ import annotations

import re
from typing import Any

from verification.backend.ingest.federal.form990.parser import ParsedXml


OFFICER_KEYWORDS = ("officer", "president", "chief", "ceo", "cfo", "treasurer", "secretary")
BOARD_KEYWORDS = ("board", "director", "trustee", "governor")


def extract_relationship_edges(parsed_xml: ParsedXml, filing_record: dict[str, Any]) -> list[dict[str, Any]]:
    ein = str(filing_record.get("ein") or "").strip()
    tax_year = filing_record.get("tax_year")
    if not ein:
        return []

    nonprofit_id = f"NONPROFIT#{ein}"
    edges: list[dict[str, Any]] = []
    dedupe_keys: set[tuple[str, str, str, str | None]] = set()

    state = _resolve_state(parsed_xml)
    if state:
        _append_edge(
            edges,
            dedupe_keys,
            {
                "edge_type": "NONPROFIT_TO_STATE",
                "source_id": nonprofit_id,
                "target_id": f"STATE#US-{state}",
                "ein": ein,
                "tax_year": tax_year,
                "role": None,
                "source": "form990_governance",
            },
        )

    for node in parsed_xml.root.findall(".//{*}OfficerDirectorTrusteeKeyEmployeeGrp"):
        name = _node_text(node, [".//{*}PersonNm", ".//{*}PersonFullName", ".//{*}BusinessNameLine1Txt"])
        if not name:
            continue
        title = _node_text(node, [".//{*}TitleTxt", ".//{*}PersonTitleTxt"]) or ""
        edge_type = _classify_person_edge_type(title)
        if not edge_type:
            continue

        person_id = _person_id(ein, name)
        _append_edge(
            edges,
            dedupe_keys,
            {
                "edge_type": edge_type,
                "source_id": person_id,
                "target_id": nonprofit_id,
                "ein": ein,
                "tax_year": tax_year,
                "role": title or None,
                "source": "form990_governance",
            },
        )

    return edges


def _resolve_state(parsed_xml: ParsedXml) -> str | None:
    for path in [".//{*}Filer/{*}USAddress/{*}StateAbbreviationCd", ".//{*}BusinessAddress/{*}StateAbbreviationCd"]:
        node = parsed_xml.root.find(path)
        if node is not None and node.text:
            state = node.text.strip().upper()
            if re.match(r"^[A-Z]{2}$", state):
                return state
    return None


def _classify_person_edge_type(title: str) -> str | None:
    normalized = title.lower()
    if any(keyword in normalized for keyword in BOARD_KEYWORDS):
        return "PERSON_TO_NONPROFIT_BOARD"
    if any(keyword in normalized for keyword in OFFICER_KEYWORDS):
        return "PERSON_TO_NONPROFIT_OFFICER"
    return None


def _person_id(ein: str, name: str) -> str:
    # Conservative normalization: keep identity scoped to EIN + normalized display name.
    normalized = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return f"PERSON#{ein}#{normalized or 'unknown'}"


def _node_text(node: Any, paths: list[str]) -> str | None:
    for path in paths:
        found = node.find(path)
        if found is not None and found.text:
            value = found.text.strip()
            if value:
                return value
    return None


def _append_edge(edges: list[dict[str, Any]], dedupe_keys: set[tuple[str, str, str, str | None]], edge: dict[str, Any]) -> None:
    key = (edge["edge_type"], edge["source_id"], edge["target_id"], edge.get("role"))
    if key in dedupe_keys:
        return
    dedupe_keys.add(key)
    edges.append(edge)

