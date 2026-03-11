from __future__ import annotations

import xml.etree.ElementTree as ET


class ParsedXml:
    def __init__(self, root: ET.Element):
        self.root = root


class XmlParseError(RuntimeError):
    pass


def parse_xml(content: bytes) -> ParsedXml:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise XmlParseError(str(exc)) from exc
    return ParsedXml(root)
