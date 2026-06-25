from __future__ import annotations

from typing import Any

from verification.backend.ingest.federal.form990.parser import ParsedXml
from verification.backend.ingest.federal.form990.resolver import resolve_text


NARRATIVE_SELECTORS = {
    "mission_description_present": [".//{*}MissionDesc", ".//{*}PrimaryExemptPurposeTxt"],
    "program_accomplishments_present": [".//{*}ProgramServiceAccomplishmentsTxt", ".//{*}ProgramServiceRevenueTxt"],
    "leadership_disclosed": [".//{*}OfficerDirectorTrusteeEmplCnt", ".//{*}VotingMembersGoverningBodyCnt"],
}


def extract_narrative_fields(parsed_xml: ParsedXml) -> dict[str, Any]:
    root = parsed_xml.root
    result: dict[str, Any] = {}
    missing_sections: list[str] = []

    for field, paths in NARRATIVE_SELECTORS.items():
        value = resolve_text(root, paths)
        present = value is not None
        result[field] = present
        if not present:
            missing_sections.append(field)

    result["narrative_sections_missing"] = missing_sections
    return result

