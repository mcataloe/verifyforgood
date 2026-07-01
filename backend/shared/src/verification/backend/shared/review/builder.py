from __future__ import annotations

from typing import Any

REVIEW_CONTRACT_VERSION = "1.0"

_INCOMPLETE_CHECK_STATUSES = {"unknown", "not_found", "not_checked"}
_UNAVAILABLE_CHECK_STATUSES = {"source_unavailable"}
_STALE_CHECK_STATUSES = {"stale"}
_REVIEW_CHECK_STATUSES = {"potential_match", "review_required"}
_CONFLICT_CHECK_STATUSES = {"conflicting"}


def ensure_review(
    payload: dict[str, Any],
    *,
    customer_policy_id: str | None = None,
    policy_owner: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    if isinstance(payload.get("review"), dict) and payload["review"].get("contract_version") == REVIEW_CONTRACT_VERSION:
        return payload
    payload["review"] = build_review(
        payload,
        customer_policy_id=customer_policy_id,
        policy_owner=policy_owner,
    )
    return payload


def build_review(
    payload: dict[str, Any],
    *,
    customer_policy_id: str | None = None,
    policy_owner: str | None = None,
) -> dict[str, Any]:
    context = _ReviewContext(payload)
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    _add_irs_status_check(context, checks, issues)
    _add_tax_deductibility_check(context, checks, issues)
    _add_filing_checks(context, checks, issues)
    _add_name_match_check(context, checks, issues)
    _add_state_checks(context, checks, issues)
    _add_external_signal_checks(context, checks, issues)
    _add_integration_checks(context, checks, issues)

    evidence_review = {
        "status": _overall_status(checks, issues),
        "checks": checks,
        "source_coverage": _source_coverage(checks),
        "issues": issues,
    }
    requirements_evaluation = _build_requirements_evaluation(
        evidence_review,
        customer_policy_id=customer_policy_id or _text(context.customer_policy.get("policy_id")),
        policy_owner=policy_owner or _text(context.customer_policy.get("policy_owner")) or "customer",
        policy_version=_text(context.customer_policy.get("policy_version")) or "1.0",
        policy_effective_at=_text(context.customer_policy.get("policy_effective_at")),
    )
    return {
        "contract_version": REVIEW_CONTRACT_VERSION,
        "evidence_review": evidence_review,
        "requirements_evaluation": requirements_evaluation,
        "customer_decision": None,
    }


class _ReviewContext:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.organization = _dict(payload.get("organization"))
        self.verification = _dict(payload.get("verification")) or _dict(payload.get("overview"))
        self.filings = _dict(payload.get("filings"))
        self.latest_filing = _dict(self.filings.get("latest")) or _dict(payload.get("filing_summary"))
        self.name_verification = _dict(payload.get("name_verification"))
        self.enrichment = _dict(payload.get("enrichment"))
        self.state_compliance = _dict(payload.get("state_compliance")) or _dict(payload.get("compliance"))
        self.external_signals = _dict(payload.get("external_signals"))
        self.integration_evaluation = _dict(payload.get("integration_evaluation"))
        self.sources = [item for item in payload.get("sources") or [] if isinstance(item, dict)]
        self.customer_policy = _dict(payload.get("customer_policy"))

    def source_reference(self, source_name: str, *, fallback_valid_as_of: Any = None) -> list[dict[str, Any]]:
        normalized = source_name.lower()
        for source in self.sources:
            candidate = str(source.get("source_name") or source.get("integration_id") or "").lower()
            if candidate == normalized or normalized in candidate or candidate in normalized:
                return [
                    {
                        "source_name": source.get("source_name") or source_name,
                        "provider_name": source.get("provider_name"),
                        "retrieved_at": _nested(source, "freshness", "retrieved_at") or source.get("retrieved_at"),
                        "valid_as_of": source.get("valid_as_of") or fallback_valid_as_of,
                    }
                ]
        return [
            {
                "source_name": source_name,
                "provider_name": None,
                "retrieved_at": None,
                "valid_as_of": fallback_valid_as_of,
            }
        ]


def _add_irs_status_check(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    raw_status = _text(context.verification.get("irs_status"))
    status_normalized = raw_status.lower() if raw_status else ""
    if not raw_status:
        check_status = "unknown"
        issues.append(_issue("irs_status_unknown", "medium", "IRS status was not available in the source payload.", ["irs_status"]))
    elif status_normalized == "active":
        check_status = "confirmed"
    else:
        check_status = "not_confirmed"
        issues.append(
            _issue(
                "irs_status_not_active",
                "high",
                "IRS source status is not active; customer review is required before relying on this fact.",
                ["irs_status"],
            )
        )
    checks.append(
        _check(
            "irs_status",
            "federal_tax_status",
            "IRS exempt organization status",
            check_status,
            raw_status,
            context.source_reference("irs.eo_bmf"),
            authoritative_for_policy=True,
        )
    )


def _add_tax_deductibility_check(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    value = _boolish(context.verification.get("tax_deductible"))
    if value is True:
        check_status = "confirmed"
    elif value is False:
        check_status = "not_confirmed"
        issues.append(
            _issue(
                "deductibility_not_confirmed",
                "medium",
                "IRS deductibility was not confirmed by the available source fact.",
                ["irs_deductibility"],
            )
        )
    else:
        check_status = "unknown"
        issues.append(
            _issue(
                "deductibility_unknown",
                "low",
                "IRS deductibility indicator was not available.",
                ["irs_deductibility"],
            )
        )
    checks.append(
        _check(
            "irs_deductibility",
            "federal_tax_status",
            "IRS deductibility indicator",
            check_status,
            value,
            context.source_reference("irs.eo_bmf"),
            authoritative_for_policy=True,
        )
    )


def _add_filing_checks(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    recent = context.filings.get("recent_990_on_file")
    if recent is None:
        recent = context.verification.get("recent_990_on_file")
    tax_period = context.latest_filing.get("tax_period") or context.verification.get("tax_period")
    if recent is True:
        recency_status = "confirmed"
        freshness = "current"
    elif recent is False:
        recency_status = "stale"
        freshness = "stale"
        issues.append(
            _issue(
                "filing_evidence_stale",
                "medium",
                "Recent Form 990 evidence was not confirmed; this is not a legal filing-compliance determination.",
                ["filing_recency"],
            )
        )
    elif context.latest_filing:
        recency_status = "unknown"
        freshness = "unknown"
        issues.append(
            _issue(
                "filing_recency_unknown",
                "low",
                "Filing metadata exists, but recency could not be determined.",
                ["filing_recency"],
            )
        )
    else:
        recency_status = "not_found"
        freshness = "unknown"
        issues.append(
            _issue(
                "filing_evidence_missing",
                "medium",
                "No Form 990 filing evidence was present in the current payload.",
                ["filing_recency"],
            )
        )
    checks.append(
        _check(
            "filing_recency",
            "filing_evidence",
            "Recent Form 990 evidence indicator",
            recency_status,
            recent,
            context.source_reference("irs_form_990_xml", fallback_valid_as_of=tax_period),
            valid_as_of=tax_period,
            freshness_status=freshness,
            authoritative_for_policy=True,
            limitations=[
                "This indicator reports available filing data only; it is not a complete legal filing-obligation determination."
            ],
        )
    )

    parse_status = _text(context.latest_filing.get("parse_status"))
    if not context.latest_filing:
        check_status = "not_checked"
    elif not parse_status:
        check_status = "unknown"
    elif parse_status.lower() == "parsed":
        check_status = "confirmed"
    else:
        check_status = "review_required"
        issues.append(
            _issue(
                "filing_parse_review_required",
                "medium",
                "Latest filing parse status requires review before relying on parsed filing signals.",
                ["filing_parse_status"],
            )
        )
    checks.append(
        _check(
            "filing_parse_status",
            "filing_evidence",
            "Latest filing parse status",
            check_status,
            parse_status,
            context.source_reference("irs_form_990_xml", fallback_valid_as_of=tax_period),
            valid_as_of=tax_period,
            freshness_status="not_applicable" if check_status == "not_checked" else "unknown",
            authoritative_for_policy=False,
        )
    )


def _add_name_match_check(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    name_match = context.name_verification.get("name_match")
    if name_match is True:
        status = "confirmed"
    elif name_match is False:
        status = "review_required"
        issues.append(
            _issue(
                "name_match_review_required",
                "high",
                "Provided organization name does not confidently match the IRS organization name.",
                ["entity_name_match"],
            )
        )
    else:
        status = "not_checked"
    checks.append(
        _check(
            "entity_name_match",
            "entity_identity",
            "Provided name to source name match",
            status,
            name_match,
            context.source_reference("irs.eo_bmf"),
            match_confidence=context.name_verification.get("score"),
            authoritative_for_policy=name_match is not None,
        )
    )


def _add_state_checks(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    registration_status = _text(context.state_compliance.get("registration_status") or context.state_compliance.get("status"))
    jurisdiction = _text(context.state_compliance.get("registration_jurisdiction") or context.verification.get("state"))
    flags = context.state_compliance.get("compliance_flags") or context.state_compliance.get("flags") or []
    if isinstance(flags, dict):
        flags = list(flags.values())
    if not isinstance(flags, list):
        flags = [flags]
    normalized_registration = registration_status.lower() if registration_status else ""
    if registration_status:
        if normalized_registration in {"active", "good_standing", "matched", "pass"}:
            check_status = "confirmed"
        else:
            check_status = "conflicting" if str(context.verification.get("irs_status") or "").lower() == "active" else "review_required"
            issues.append(
                _issue(
                    "state_registration_review_required",
                    "high",
                    "A checked state source returned a registration status that requires customer review.",
                    ["state_registration_status"],
                )
            )
    elif _state_source_attempted(context):
        check_status = "source_unavailable"
        issues.append(
            _issue(
                "state_source_unavailable",
                "medium",
                "A state registry source was configured or attempted but did not provide registration evidence.",
                ["state_registration_status"],
            )
        )
    else:
        check_status = "not_checked"
    checks.append(
        _check(
            "state_registration_status",
            "state_registration",
            "Checked state registration status",
            check_status,
            registration_status,
            context.source_reference("state_registry"),
            valid_as_of=context.state_compliance.get("registration_expiration_date"),
            authoritative_for_policy=False,
            limitations=[
                "State evidence applies only to jurisdictions actually checked and does not establish nationwide registration compliance."
            ],
        )
    )

    if flags:
        flag_status = "review_required"
        issues.append(
            _issue(
                "state_flags_review_required",
                "medium",
                "A checked state source returned one or more flags for customer review.",
                ["state_compliance_flags"],
            )
        )
    elif registration_status:
        flag_status = "not_found"
    elif _state_source_attempted(context):
        flag_status = "source_unavailable"
    else:
        flag_status = "not_checked"
    checks.append(
        _check(
            "state_compliance_flags",
            "state_registration",
            "Checked state source flags",
            flag_status,
            flags,
            context.source_reference("state_registry"),
            authoritative_for_policy=False,
            limitations=[
                "No returned state flags means only that the checked source did not return flags in this payload."
            ],
        )
    )


def _add_external_signal_checks(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    sanctions = _dict(context.external_signals.get("sanctions"))
    sanctions_match = sanctions.get("sanctions_match")
    if sanctions_match is True:
        status = "potential_match"
        issues.append(
            _issue(
                "potential_sanctions_match_review_required",
                "high",
                "An external sanctions-style source returned a potential match; this is not a confirmed adverse finding.",
                ["sanctions_screening"],
            )
        )
    elif sanctions_match is False:
        status = "not_found"
    elif _source_named(context, "ofac") or _source_named(context, "sanctions"):
        status = "unknown"
    else:
        status = "not_checked"
    checks.append(
        _check(
            "sanctions_screening",
            "external_signal",
            "External sanctions-style screening signal",
            status,
            sanctions_match,
            context.source_reference(_text(sanctions.get("source")) or "sanctions"),
            authoritative_for_policy=False,
            limitations=[
                "Provider results are supplemental until separately validated; no-match is not a clearance."
            ],
        )
    )


def _add_integration_checks(
    context: _ReviewContext,
    checks: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    states = context.integration_evaluation.get("integrations") or []
    if not isinstance(states, list):
        states = []
    required_unmet = set(str(item) for item in context.integration_evaluation.get("required_unmet_integrations") or [])
    failure_integrations = set(str(item) for item in context.integration_evaluation.get("failure_integrations") or [])
    for state in states:
        if not isinstance(state, dict):
            continue
        integration_id = _text(state.get("integration_id"))
        if not integration_id:
            continue
        required = bool(state.get("required_for_eligibility") or integration_id in required_unmet)
        availability = _text(state.get("availability_status")) or "unknown"
        attempted = bool(state.get("attempted"))
        if integration_id in required_unmet or integration_id in failure_integrations or availability in {"failed", "missing_credentials", "unavailable"}:
            status = "source_unavailable"
            if required:
                issues.append(
                    _issue(
                        "required_source_unavailable",
                        "high",
                        "A customer-required source was unavailable or could not be evaluated.",
                        [f"integration:{integration_id}"],
                    )
                )
        elif not attempted:
            status = "not_checked"
        elif availability in {"matched", "available"}:
            status = "confirmed"
        elif availability == "no_match":
            status = "not_found"
        else:
            status = "unknown"
        checks.append(
            _check(
                f"integration:{integration_id}",
                "external_signal",
                f"{integration_id} source availability",
                status,
                availability,
                context.source_reference(integration_id),
                authoritative_for_policy=required,
                limitations=[
                    "External provider availability is not itself an authoritative pass/fail finding."
                ],
            )
        )


def _build_requirements_evaluation(
    evidence_review: dict[str, Any],
    *,
    customer_policy_id: str | None,
    policy_owner: str,
    policy_version: str,
    policy_effective_at: str | None,
) -> dict[str, Any] | None:
    if not customer_policy_id:
        return None

    checks = {item["check_id"]: item for item in evidence_review.get("checks", [])}
    requirements = [
        _requirement(
            checks,
            requirement_id="irs_status_active",
            description="Customer requires the IRS exempt organization status source fact to be active.",
            check_id="irs_status",
            met_when=lambda check: str(check.get("observed_value") or "").lower() == "active",
        ),
        _requirement(
            checks,
            requirement_id="tax_deductibility_confirmed",
            description="Customer requires the IRS deductibility indicator to be confirmed.",
            check_id="irs_deductibility",
            met_when=lambda check: check.get("observed_value") is True,
        ),
        _requirement(
            checks,
            requirement_id="recent_filing_indicator_available",
            description="Customer requires current available filing-recency evidence, without treating it as legal filing compliance.",
            check_id="filing_recency",
            met_when=lambda check: check.get("observed_value") is True and check.get("status") == "confirmed",
            stale_is_unresolved=True,
        ),
    ]
    result = _requirements_result(requirements, evidence_review.get("status"))
    return {
        "policy_id": customer_policy_id,
        "policy_version": policy_version,
        "policy_owner": policy_owner,
        "policy_effective_at": policy_effective_at,
        "adoption_status": "request_supplied",
        "result": result,
        "requirements": requirements,
    }


def _requirement(
    checks: dict[str, dict[str, Any]],
    *,
    requirement_id: str,
    description: str,
    check_id: str,
    met_when: Any,
    stale_is_unresolved: bool = False,
) -> dict[str, Any]:
    check = checks.get(check_id)
    if check is None:
        result = "unresolved"
        explanation = "The required evidence check is not present in this response."
    elif check.get("status") in _UNAVAILABLE_CHECK_STATUSES:
        result = "unresolved"
        explanation = "The required source was unavailable."
    elif check.get("status") in _INCOMPLETE_CHECK_STATUSES:
        result = "unresolved"
        explanation = "The required evidence is incomplete or unknown."
    elif stale_is_unresolved and check.get("status") in _STALE_CHECK_STATUSES:
        result = "unresolved"
        explanation = "The required evidence is stale and needs customer review."
    elif check.get("status") in _REVIEW_CHECK_STATUSES or check.get("status") in _CONFLICT_CHECK_STATUSES:
        result = "unresolved"
        explanation = "The required evidence needs customer review."
    elif met_when(check):
        result = "met"
        explanation = "The customer-authored requirement is supported by the referenced evidence check."
    else:
        result = "not_met"
        explanation = "The referenced evidence check does not support this customer-authored requirement."
    return {
        "requirement_id": requirement_id,
        "description": description,
        "result": result,
        "evidence_check_ids": [check_id],
        "explanation": explanation,
    }


def _requirements_result(requirements: list[dict[str, Any]], evidence_status: str | None) -> str:
    requirement_results = [item["result"] for item in requirements if item["result"] != "not_applicable"]
    if evidence_status == "source_unavailable" and any(result == "unresolved" for result in requirement_results):
        return "unable_to_evaluate"
    if any(result == "not_met" for result in requirement_results):
        return "requirements_not_met"
    if any(result == "unresolved" for result in requirement_results):
        return "unresolved"
    return "requirements_met"


def _overall_status(checks: list[dict[str, Any]], issues: list[dict[str, Any]]) -> str:
    issue_codes = {item.get("code") for item in issues}
    required_statuses = {
        item.get("status")
        for item in checks
        if item.get("authoritative_for_policy")
    }
    if any(status in _CONFLICT_CHECK_STATUSES for status in required_statuses) or "state_registration_review_required" in issue_codes:
        return "conflicting" if any(item.get("status") == "conflicting" for item in checks) else "review_required"
    if any(status in _REVIEW_CHECK_STATUSES for status in required_statuses) or any(
        code
        in {
            "potential_sanctions_match_review_required",
            "name_match_review_required",
            "state_flags_review_required",
            "filing_parse_review_required",
            "irs_status_not_active",
        }
        for code in issue_codes
    ):
        return "review_required"
    if any(status in _UNAVAILABLE_CHECK_STATUSES for status in required_statuses):
        return "source_unavailable"
    if any(status in _STALE_CHECK_STATUSES for status in required_statuses):
        return "stale"
    if any(status in _INCOMPLETE_CHECK_STATUSES for status in required_statuses):
        return "incomplete"
    return "complete"


def _source_coverage(checks: list[dict[str, Any]]) -> dict[str, list[str]]:
    required = [item["check_id"] for item in checks if item.get("authoritative_for_policy")]
    completed = [
        item["check_id"]
        for item in checks
        if item.get("authoritative_for_policy")
        and item.get("status") not in _UNAVAILABLE_CHECK_STATUSES | _INCOMPLETE_CHECK_STATUSES
    ]
    unavailable = [
        item["check_id"]
        for item in checks
        if item.get("authoritative_for_policy") and item.get("status") in _UNAVAILABLE_CHECK_STATUSES
    ]
    not_checked = [
        item["check_id"]
        for item in checks
        if item.get("authoritative_for_policy") and item.get("status") in _INCOMPLETE_CHECK_STATUSES
    ]
    return {
        "required": required,
        "completed": completed,
        "unavailable": unavailable,
        "not_checked": not_checked,
    }


def _check(
    check_id: str,
    category: str,
    label: str,
    status: str,
    observed_value: Any,
    source_references: list[dict[str, Any]],
    *,
    retrieved_at: str | None = None,
    valid_as_of: Any = None,
    freshness_status: str = "unknown",
    match_confidence: Any = None,
    limitations: list[str] | None = None,
    authoritative_for_policy: bool = False,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "category": category,
        "label": label,
        "status": status,
        "observed_value": observed_value,
        "source_references": source_references,
        "retrieved_at": retrieved_at or _first_source_value(source_references, "retrieved_at"),
        "valid_as_of": _text(valid_as_of) or _first_source_value(source_references, "valid_as_of"),
        "freshness_status": freshness_status,
        "match_confidence": match_confidence,
        "limitations": limitations or [],
        "authoritative_for_policy": authoritative_for_policy,
    }


def _issue(code: str, severity: str, message: str, related_check_ids: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "related_check_ids": related_check_ids,
    }


def _first_source_value(source_references: list[dict[str, Any]], key: str) -> str | None:
    for source in source_references:
        value = _text(source.get(key))
        if value:
            return value
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _nested(value: dict[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "deductible"}:
            return True
        if lowered in {"false", "0", "no", "n", "not_deductible"}:
            return False
    return None


def _source_named(context: _ReviewContext, needle: str) -> bool:
    needle = needle.lower()
    for source in context.sources:
        source_name = str(source.get("source_name") or source.get("integration_id") or "").lower()
        if needle in source_name:
            return True
    return False


def _state_source_attempted(context: _ReviewContext) -> bool:
    if _source_named(context, "state_registry") or _source_named(context, "state"):
        return True
    states = context.integration_evaluation.get("integrations") or []
    if isinstance(states, list):
        for state in states:
            if isinstance(state, dict) and "state_registry" in str(state.get("integration_id") or ""):
                return bool(state.get("attempted") or state.get("tenant_enabled") or state.get("required_for_eligibility"))
    return False
