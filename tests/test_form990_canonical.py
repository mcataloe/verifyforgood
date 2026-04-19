from __future__ import annotations

from infrastructure.verification.form990.canonical import (
    canonicalize_xml_to_json,
    compute_normalized_xml_content_hash,
)


def test_canonicalize_xml_to_json_is_stable_and_namespace_free():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<ns0:Return xmlns:ns0="http://www.irs.gov/efile" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ns0:ReturnData>
    <ns0:IRS990>
      <ns0:OfficerGroup role="board">
        <ns0:PersonNm>Alice Smith</ns0:PersonNm>
      </ns0:OfficerGroup>
      <ns0:OfficerGroup role="board">
        <ns0:PersonNm>Bob Jones</ns0:PersonNm>
      </ns0:OfficerGroup>
    </ns0:IRS990>
  </ns0:ReturnData>
</ns0:Return>
"""

    first = canonicalize_xml_to_json(xml)
    second = canonicalize_xml_to_json(xml)

    assert first == second
    assert first == {
        "Return": {
            "ReturnData": {
                "IRS990": {
                    "OfficerGroup": [
                        {"PersonNm": "Alice Smith", "_attrs": {"role": "board"}},
                        {"PersonNm": "Bob Jones", "_attrs": {"role": "board"}},
                    ]
                }
            }
        }
    }


def test_compute_normalized_xml_content_hash_ignores_newline_and_trailing_space_differences():
    first = b"<Return>\r\n  <Value>123</Value>   \r\n</Return>\r\n"
    second = b"<Return>\n  <Value>123</Value>\n</Return>\n"

    assert compute_normalized_xml_content_hash(first) == compute_normalized_xml_content_hash(second)

