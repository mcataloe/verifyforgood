from __future__ import annotations

import re

from .contracts import ChatExecutionContext


_SAFE_REPLACEMENT = (
    "I can summarize the available evidence, provenance, and data gaps, but I cannot make an independent "
    "trust, approval, fraud, safety, compliance, eligibility, donation, procurement, or endorsement determination."
)


class VerifyForGoodChatOutputPolicy:
    """Deterministically prevents the model from becoming the customer's decision authority."""

    _PROHIBITED_PATTERNS = (
        re.compile(
            r"\b(?:this|the)\s+(?:nonprofit|organization|charity)\s+(?:is|is not|appears to be|should be considered)\s+"
            r"(?:trustworthy|untrustworthy|worthy|unworthy|approved|denied|fraudulent|safe|unsafe|"
            r"legally compliant|compliant|noncompliant|eligible|ineligible|recommended|not recommended)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:you|your organization|the customer)\s+should\s+(?:donate|give|fund|approve|deny|reject|"
            r"procure|contract with|avoid)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:i|we|verifyforgood)\s+(?:recommend|approve|endorse|certify)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:safe|unsafe)\s+(?:to donate|for donation|for procurement|to procure|to fund|to contract)\b",
            re.IGNORECASE,
        ),
    )

    def apply(self, content: str, context: ChatExecutionContext) -> str:
        del context
        normalized = str(content or "").strip()
        if any(pattern.search(normalized) for pattern in self._PROHIBITED_PATTERNS):
            return _SAFE_REPLACEMENT
        return normalized


__all__ = ["VerifyForGoodChatOutputPolicy"]
