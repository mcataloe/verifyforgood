from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select

from charity_status.normalization import map_deductibility, map_entity_type, map_irs_status, map_ntee_category
from charity_status.platform import QueryRuntimeConfig, build_athena_client, resolve_postgres_sqlalchemy_url
from charity_status.serving import DynamoProfileStore
from charity_status_platform.customer_accounts import (
    CustomerAccountsBase,
    build_customer_accounts_engine,
    build_customer_accounts_session_factory,
    customer_accounts_session_scope,
)
from charity_status_platform.nonprofits import (
    ComplianceCheckModel,
    ComplianceCheckRecord,
    NonprofitFilingModel,
    NonprofitFilingRecord,
    NonprofitModel,
    NonprofitRecord,
    NonprofitSourceModel,
    NonprofitSourceRecord,
    SqlAlchemyNonprofitRepository,
    build_nonprofit_id,
)

from .migration_validation import MigrationEntityValidation, build_entity_validation


@dataclass(frozen=True)
class NonprofitMigrationCounts:
    nonprofits: int = 0
    filings: int = 0
    sources: int = 0
    compliance_checks: int = 0


@dataclass(frozen=True)
class NonprofitMigrationReport:
    dry_run: bool
    processed_eins: int
    source_counts: NonprofitMigrationCounts
    target_counts: NonprofitMigrationCounts
    missing_lookup_records: int = 0
    invalid_eins: int = 0
    profile_items_seen: int = 0
    validation: dict[str, MigrationEntityValidation] = field(default_factory=dict)
    sample_missing_eins: tuple[str, ...] = ()
    sample_invalid_eins: tuple[str, ...] = ()


def run_nonprofit_migration(
    env: Mapping[str, str] | None = None,
    *,
    sqlalchemy_url: str | None = None,
    query_client: Any | None = None,
    profile_store: Any | None = None,
    profile_table_name: str | None = None,
    page_size: int = 100,
    max_eins: int | None = None,
    start_after_ein: str | None = None,
    dry_run: bool = False,
    include_profile_cache: bool = True,
    sample_limit: int = 20,
    secrets_client: Any | None = None,
) -> NonprofitMigrationReport:
    source = env or os.environ
    resolved_url = sqlalchemy_url or resolve_postgres_sqlalchemy_url(source, secrets_client=secrets_client)
    engine = build_customer_accounts_engine(resolved_url)
    CustomerAccountsBase.metadata.create_all(engine)
    session_factory = build_customer_accounts_session_factory(engine)
    repository = SqlAlchemyNonprofitRepository(session_factory)
    effective_query_client = query_client or build_athena_client(_query_runtime_config(source))
    effective_profile_store = profile_store or _build_profile_store(
        source,
        include_profile_cache=include_profile_cache,
        profile_table_name=profile_table_name,
    )

    expected_nonprofits: set[int] = set()
    expected_filings: set[str] = set()
    expected_sources: set[str] = set()
    expected_checks: set[str] = set()
    missing_lookup_records: list[str] = []
    invalid_eins: list[str] = []
    processed_eins = 0
    profile_items_seen = 0

    cursor = _normalize_ein(start_after_ein) if start_after_ein else None
    while max_eins is None or processed_eins < max_eins:
        remaining = page_size if max_eins is None else max(0, min(page_size, max_eins - processed_eins))
        if remaining <= 0:
            break
        eins = list(effective_query_client.list_nonprofit_eins_page(limit=remaining, start_after_ein=cursor))
        if not eins:
            break
        for ein in eins:
            if max_eins is not None and processed_eins >= max_eins:
                break
            normalized_ein = _normalize_ein(ein)
            if len(normalized_ein) != 9:
                invalid_eins.append(str(ein))
                continue
            processed_eins += 1
            cursor = normalized_ein

            _, nonprofit_row = effective_query_client.lookup_nonprofit(normalized_ein)
            if not nonprofit_row:
                missing_lookup_records.append(normalized_ein)
                continue

            nonprofit_record = _nonprofit_record_from_query(
                repository=repository,
                ein=normalized_ein,
                row=nonprofit_row,
            )
            expected_nonprofits.add(normalized_ein)
            if not dry_run:
                repository.upsert_nonprofit(nonprofit_record)

            _, filing_rows = effective_query_client.list_form990_filings(normalized_ein, limit=50)
            for filing_row in filing_rows:
                filing_record = _filing_record_from_query(nonprofit_record.nonprofit_id, normalized_ein, filing_row)
                expected_filings.add(filing_record.filing_id)
                if not dry_run:
                    repository.upsert_filing(filing_record)

            if effective_profile_store is not None:
                profile_item = effective_profile_store.get_profile(normalized_ein)
                if profile_item:
                    profile_items_seen += 1
                    for source_record in _source_records_from_profile(nonprofit_record.nonprofit_id, normalized_ein, profile_item):
                        expected_sources.add(source_record.nonprofit_source_id)
                        if not dry_run:
                            repository.upsert_source(source_record)
                    compliance_record = _compliance_record_from_profile(nonprofit_record.nonprofit_id, normalized_ein, profile_item)
                    if compliance_record is not None:
                        expected_checks.add(compliance_record.compliance_check_id)
                        if not dry_run:
                            repository.create_compliance_check(compliance_record)

    target_counts, validation = _validate_nonprofit_targets(
        session_factory=session_factory,
        expected_nonprofits=expected_nonprofits,
        expected_filings=expected_filings,
        expected_sources=expected_sources,
        expected_checks=expected_checks,
        sample_limit=sample_limit,
    )
    source_counts = NonprofitMigrationCounts(
        nonprofits=len(expected_nonprofits),
        filings=len(expected_filings),
        sources=len(expected_sources),
        compliance_checks=len(expected_checks),
    )
    return NonprofitMigrationReport(
        dry_run=dry_run,
        processed_eins=processed_eins,
        source_counts=source_counts,
        target_counts=target_counts,
        missing_lookup_records=len(missing_lookup_records),
        invalid_eins=len(invalid_eins),
        profile_items_seen=profile_items_seen,
        validation=validation,
        sample_missing_eins=tuple(missing_lookup_records[:sample_limit]),
        sample_invalid_eins=tuple(invalid_eins[:sample_limit]),
    )


def _query_runtime_config(source: Mapping[str, str]) -> QueryRuntimeConfig:
    return QueryRuntimeConfig(
        database=str(source.get("DATABASE", "irs_nonprofits") or "irs_nonprofits"),
        table=str(source.get("TABLE", "eo_bmf") or "eo_bmf"),
        workgroup=str(source.get("WORKGROUP", "") or "").strip() or None,
        form990_filings_table=str(source.get("FORM990_FILINGS_TABLE", "form990_metadata") or "form990_metadata"),
        form990_metrics_table=str(source.get("FORM990_METRICS_TABLE", "form990_metrics") or "form990_metrics"),
        form990_governance_table=str(source.get("FORM990_GOVERNANCE_TABLE", "form990_governance") or "form990_governance"),
        form990_quality_table=str(source.get("FORM990_QUALITY_TABLE", "form990_quality") or "form990_quality"),
    )


def _build_profile_store(
    source: Mapping[str, str],
    *,
    include_profile_cache: bool,
    profile_table_name: str | None,
) -> Any | None:
    if not include_profile_cache:
        return None
    resolved_name = str(profile_table_name or source.get("PROFILE_TABLE_NAME") or "").strip()
    if not resolved_name:
        return None
    return DynamoProfileStore(table_name=resolved_name)


def _nonprofit_record_from_query(
    *,
    repository: SqlAlchemyNonprofitRepository,
    ein: str,
    row: dict[str, Any],
) -> NonprofitRecord:
    now_iso = _utc_now_iso()
    existing = repository.get_nonprofit_by_ein(ein)
    name = _text(row.get("name")) or (existing.canonical_name if existing else None) or f"EIN {ein}"
    subsection = _text(row.get("subsection")) or (existing.subsection_code if existing else None)
    deductibility = _text(row.get("deductibility")) or (existing.deductibility_code if existing else None)
    status_value = _text(row.get("status"))
    irs_status = map_irs_status(status_value or (existing.irs_status if existing else None))
    return NonprofitRecord(
        nonprofit_id=build_nonprofit_id(ein),
        ein=ein,
        canonical_name=name,
        normalized_name=name.lower(),
        subsection_code=subsection,
        deductibility_code=deductibility,
        tax_deductible=map_deductibility(deductibility),
        entity_type=map_entity_type(subsection),
        irs_status=irs_status,
        revoked=irs_status == "inactive",
        country="US",
        state=_text(row.get("state")) or (existing.state if existing else None),
        ntee_category=map_ntee_category(_text(row.get("ntee_cd")) or (existing.ntee_category if existing else None)),
        canonical_source="irs_eo_bmf_athena",
        source_version=(existing.source_version if existing else None),
        last_seen_at=now_iso,
        created_at=existing.created_at if existing else now_iso,
        updated_at=now_iso,
    )


def _filing_record_from_query(nonprofit_id: int, ein: str, row: dict[str, Any]) -> NonprofitFilingRecord:
    tax_year = _to_int(row.get("tax_year"))
    form_type = _text(row.get("return_type")) or "990"
    filing_date = _text(row.get("filing_date"))
    filing_id = _stable_id("fil", ein, str(tax_year or ""), form_type, filing_date or "")
    now_iso = _utc_now_iso()
    return NonprofitFilingRecord(
        filing_id=filing_id,
        nonprofit_id=nonprofit_id,
        tax_year=tax_year,
        tax_period=None,
        form_type=form_type,
        filing_date=filing_date,
        amended=_to_bool(row.get("amended_return")) or False,
        parse_status=_text(row.get("parse_status")),
        source_name="athena.form990",
        source_record_id=f"{ein}:{tax_year or ''}:{form_type}:{filing_date or ''}",
        raw_payload=dict(row),
        created_at=now_iso,
        updated_at=now_iso,
    )


def _source_records_from_profile(nonprofit_id: int, ein: str, profile_item: dict[str, Any]) -> list[NonprofitSourceRecord]:
    now_iso = _text(profile_item.get("materialized_at")) or _utc_now_iso()
    providers = ((profile_item.get("enrichment") or {}).get("providers") or [])
    records: list[NonprofitSourceRecord] = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_name = _text(provider.get("name")) or "unknown_provider"
        source = provider.get("source") or {}
        if not isinstance(source, dict):
            source = {}
        retrieved_at = _text(source.get("fetched_at")) or now_iso
        record_id = _text(source.get("record_id"))
        source_id = _text(source.get("source_name")) or provider_name
        source_record = NonprofitSourceRecord(
            nonprofit_source_id=_stable_id("src", ein, source_id, record_id or "", retrieved_at),
            nonprofit_id=nonprofit_id,
            source_id=source_id,
            provider_name=provider_name,
            category="enrichment",
            record_id=record_id,
            retrieved_at=retrieved_at,
            valid_as_of=retrieved_at,
            status=_text(provider.get("status")),
            driver=_text(provider.get("driver")),
            integration_id=_text(provider.get("integration_id")) or provider_name,
            tenant_enabled=_to_optional_bool(provider.get("tenant_enabled")),
            required_for_eligibility=_to_optional_bool(provider.get("required_for_eligibility")),
            evaluation_effect=_text(provider.get("evaluation_effect")),
            explanation_code=_text(provider.get("explanation_code")),
            explanation=_text(provider.get("explanation")),
            licensed=_to_optional_bool(source.get("licensed")),
            notes=_text(source.get("notes")),
            normalized_data=provider.get("fields") if isinstance(provider.get("fields"), dict) else provider.get("normalized_data"),
            raw_payload=provider,
            created_at=now_iso,
            updated_at=now_iso,
        )
        records.append(source_record)
    return records


def _compliance_record_from_profile(
    nonprofit_id: int,
    ein: str,
    profile_item: dict[str, Any],
) -> ComplianceCheckRecord | None:
    state_compliance = profile_item.get("state_compliance") or {}
    policy_evaluation = profile_item.get("policy_evaluation") or {}
    decision = profile_item.get("decision") or {}
    summary = profile_item.get("summary") or {}
    evidence = profile_item.get("evidence") or {}
    final_recommendation = _text(profile_item.get("final_recommendation")) or _text(policy_evaluation.get("final_recommendation"))
    if not any((state_compliance, policy_evaluation, decision, summary, evidence, final_recommendation)):
        return None

    evaluated_at = _text(profile_item.get("materialized_at")) or _utc_now_iso()
    source_hash = _text(profile_item.get("source_hash")) or _stable_id("src_hash", ein, evaluated_at)
    compliance_flags = state_compliance.get("compliance_flags")
    reasons = policy_evaluation.get("matched_rules")
    status = (
        final_recommendation
        or _text(decision.get("status"))
        or _text(state_compliance.get("registration_status"))
        or "available"
    )
    return ComplianceCheckRecord(
        compliance_check_id=_stable_id("chk", ein, source_hash, evaluated_at),
        nonprofit_id=nonprofit_id,
        check_type="materialized_profile_snapshot",
        status=status,
        evaluated_at=evaluated_at,
        policy_version=_text(policy_evaluation.get("policy_id")),
        model_version=_text(profile_item.get("model_version")),
        source_hash=source_hash,
        environment=_text(profile_item.get("environment")),
        registration_status=_text(state_compliance.get("registration_status")),
        registration_jurisdiction=_text(state_compliance.get("registration_jurisdiction")),
        registration_expiration_date=_text(state_compliance.get("registration_expiration_date")),
        solicitation_permitted=_to_optional_bool(state_compliance.get("solicitation_permitted")),
        state_business_status=_text((profile_item.get("external_signals") or {}).get("state_business_status")),
        state_business_good_standing=_to_optional_bool((profile_item.get("external_signals") or {}).get("state_business_good_standing")),
        final_recommendation=final_recommendation,
        flags_json=compliance_flags if isinstance(compliance_flags, (list, dict)) else None,
        reasons_json=reasons if isinstance(reasons, (list, dict)) else None,
        evidence_json=evidence if isinstance(evidence, (list, dict)) else None,
        summary_json=summary if isinstance(summary, dict) else None,
        metadata_json={
            "policy_evaluation": policy_evaluation if isinstance(policy_evaluation, dict) else {},
            "decision": decision if isinstance(decision, dict) else {},
            "audit": profile_item.get("audit") if isinstance(profile_item.get("audit"), dict) else {},
            "source_data_versions": profile_item.get("source_data_versions") if isinstance(profile_item.get("source_data_versions"), dict) else {},
            "external_signals": profile_item.get("external_signals") if isinstance(profile_item.get("external_signals"), dict) else {},
        },
        created_at=evaluated_at,
    )


def _validate_nonprofit_targets(
    *,
    session_factory: Any,
    expected_nonprofits: set[int],
    expected_filings: set[str],
    expected_sources: set[str],
    expected_checks: set[str],
    sample_limit: int,
) -> tuple[NonprofitMigrationCounts, dict[str, MigrationEntityValidation]]:
    with customer_accounts_session_scope(session_factory) as session:
        present_nonprofits = set(session.scalars(select(NonprofitModel.ein).where(NonprofitModel.ein.in_(expected_nonprofits))).all()) if expected_nonprofits else set()
        present_filings = set(session.scalars(select(NonprofitFilingModel.filing_id).where(NonprofitFilingModel.filing_id.in_(expected_filings))).all()) if expected_filings else set()
        present_sources = set(session.scalars(select(NonprofitSourceModel.nonprofit_source_id).where(NonprofitSourceModel.nonprofit_source_id.in_(expected_sources))).all()) if expected_sources else set()
        present_checks = set(session.scalars(select(ComplianceCheckModel.compliance_check_id).where(ComplianceCheckModel.compliance_check_id.in_(expected_checks))).all()) if expected_checks else set()

    validation = {
        "nonprofits": build_entity_validation(expected_keys=expected_nonprofits, present_keys=present_nonprofits, sample_limit=sample_limit),
        "filings": build_entity_validation(expected_keys=expected_filings, present_keys=present_filings, sample_limit=sample_limit),
        "sources": build_entity_validation(expected_keys=expected_sources, present_keys=present_sources, sample_limit=sample_limit),
        "compliance_checks": build_entity_validation(expected_keys=expected_checks, present_keys=present_checks, sample_limit=sample_limit),
    }
    return (
        NonprofitMigrationCounts(
            nonprofits=validation["nonprofits"].present,
            filings=validation["filings"].present,
            sources=validation["sources"].present,
            compliance_checks=validation["compliance_checks"].present,
        ),
        validation,
    )


def _normalize_ein(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())[:9]


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_int(value: Any) -> int | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = _text(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"true", "1", "y", "yes"}:
        return True
    if lowered in {"false", "0", "n", "no"}:
        return False
    return None


def _to_optional_bool(value: Any) -> bool | None:
    return _to_bool(value)


def _text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill nonprofit PostgreSQL tables from Athena and the optional materialized profile cache.")
    parser.add_argument("--sqlalchemy-url", default=os.environ.get("PLATFORM_POSTGRES_URL", ""))
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-eins", type=int, default=None)
    parser.add_argument("--start-after-ein", default="")
    parser.add_argument("--profile-table-name", default=os.environ.get("PROFILE_TABLE_NAME", ""))
    parser.add_argument("--skip-profile-cache", action="store_true", help="Do not read the Dynamo materialized profile cache for sources/compliance snapshots.")
    parser.add_argument("--dry-run", action="store_true", help="Skip writes and only validate current PostgreSQL contents against the source datasets.")
    parser.add_argument("--sample-limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_nonprofit_migration(
        os.environ,
        sqlalchemy_url=(str(args.sqlalchemy_url).strip() or None),
        profile_table_name=(str(args.profile_table_name).strip() or None),
        page_size=max(1, int(args.page_size)),
        max_eins=(None if args.max_eins is None else max(1, int(args.max_eins))),
        start_after_ein=(str(args.start_after_ein).strip() or None),
        dry_run=bool(args.dry_run),
        include_profile_cache=not bool(args.skip_profile_cache),
        sample_limit=max(1, int(args.sample_limit)),
    )
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
