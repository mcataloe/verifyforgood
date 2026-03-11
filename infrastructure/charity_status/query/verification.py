from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from charity_status.normalization import compare_names
from charity_status.query.nonprofit_lookup import map_nonprofit_record
from charity_status.scoring import calculate_v1_scores


@dataclass(frozen=True)
class VerificationInput:
    ein: str
    provided_name: str | None = None
    subsection: str | None = None


def verify_nonprofit(
    client: Any,
    verification_input: VerificationInput,
) -> tuple[int, dict[str, Any]]:
    query_execution_id, record = client.lookup_nonprofit(verification_input.ein, subsection=verification_input.subsection)

    if not record:
        return 404, {"message": "Nonprofit not found", "ein": verification_input.ein}

    mapped = map_nonprofit_record(verification_input.ein, record)
    name_check = compare_names(verification_input.provided_name, mapped.organization.get("name"))

    score_result = calculate_v1_scores(
        record=record,
        verification=mapped.verification,
        ein_valid=True,
        name_match=name_check.get("name_match"),
    )

    payload = mapped.to_dict()
    payload["scores"] = score_result.scores
    payload["score_explanation"] = score_result.explanation
    payload["name_verification"] = name_check
    payload["queryExecutionId"] = query_execution_id
    return 200, payload
