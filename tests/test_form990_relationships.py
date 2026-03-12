from __future__ import annotations

from infrastructure.charity_status.form990.parser import parse_xml
from infrastructure.charity_status.form990.relationships import extract_relationship_edges


def _xml_with_people() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<Return xmlns="http://www.irs.gov/efile">
  <Filer>
    <USAddress>
      <StateAbbreviationCd>IL</StateAbbreviationCd>
    </USAddress>
  </Filer>
  <ReturnData>
    <IRS990>
      <OfficerDirectorTrusteeKeyEmployeeGrp>
        <PersonNm>Jane Officer</PersonNm>
        <TitleTxt>Chief Executive Officer</TitleTxt>
      </OfficerDirectorTrusteeKeyEmployeeGrp>
      <OfficerDirectorTrusteeKeyEmployeeGrp>
        <PersonNm>John Board</PersonNm>
        <TitleTxt>Board Member</TitleTxt>
      </OfficerDirectorTrusteeKeyEmployeeGrp>
      <OfficerDirectorTrusteeKeyEmployeeGrp>
        <PersonNm>John Board</PersonNm>
        <TitleTxt>Board Member</TitleTxt>
      </OfficerDirectorTrusteeKeyEmployeeGrp>
    </IRS990>
  </ReturnData>
</Return>"""


def test_relationship_officer_extraction():
    parsed = parse_xml(_xml_with_people())
    edges = extract_relationship_edges(parsed, {"ein": "123456789", "tax_year": "2023"})
    officer_edges = [e for e in edges if e["edge_type"] == "PERSON_TO_NONPROFIT_OFFICER"]
    assert len(officer_edges) == 1
    assert officer_edges[0]["target_id"] == "NONPROFIT#123456789"


def test_relationship_board_extraction():
    parsed = parse_xml(_xml_with_people())
    edges = extract_relationship_edges(parsed, {"ein": "123456789", "tax_year": "2023"})
    board_edges = [e for e in edges if e["edge_type"] == "PERSON_TO_NONPROFIT_BOARD"]
    assert len(board_edges) == 1
    assert board_edges[0]["role"] == "Board Member"


def test_relationship_missing_leadership_data():
    parsed = parse_xml(b"<Return xmlns='http://www.irs.gov/efile'><Filer><EIN>123456789</EIN></Filer></Return>")
    edges = extract_relationship_edges(parsed, {"ein": "123456789", "tax_year": "2023"})
    assert edges == []


def test_relationship_duplicate_edge_suppression():
    parsed = parse_xml(_xml_with_people())
    edges = extract_relationship_edges(parsed, {"ein": "123456789", "tax_year": "2023"})
    # officer + board + nonprofit->state
    assert len(edges) == 3
    assert len({(e["edge_type"], e["source_id"], e["target_id"], e.get("role")) for e in edges}) == 3
