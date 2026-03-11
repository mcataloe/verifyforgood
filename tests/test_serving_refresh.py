from __future__ import annotations

from typing import Any

from charity_status.serving.change_events import build_change_event
from charity_status.serving.compare import compare_materialized_items
from charity_status.serving.refresh import RefreshConfig, refresh_materialized_profiles
import pytest


def _payload(
    model_version: str = "1.0.0",
    score: int = 80,
    eligibility: str = "ELIGIBLE",
    decision_status: str = "approve",
    risk_flags: list[str] | None = None,
    stale_filing_days: int | None = None,
    registration_status: str | None = None,
    compliance_flags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "organization": {"ein": "12-3456789", "name": "Org"},
        "verification": {"irs_status": "active", "recent_990_on_file": True},
        "scores": {"overall": score},
        "score_explanation": {
            "model_version": model_version,
            "score_data_sources": ["eo_bmf"],
            "eligibility": eligibility,
            "factors": {"stale_filing_days": stale_filing_days},
        },
        "filing_summary": {"tax_year": "2024"},
        "enrichment": {"providers": [], "failures": []},
        "decision": {"status": decision_status, "risk_flags": risk_flags or []},
        "summary": {"decision_status": "approve"},
        "audit": {"model_version": model_version},
        "state_compliance": {"registration_status": registration_status, "compliance_flags": compliance_flags or []},
    }


class InMemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self.put_calls = 0

    def get_profile(self, ein: str) -> dict[str, Any] | None:
        return self._items.get(ein)

    def put_profile(self, item: dict[str, Any]) -> None:
        self.put_calls += 1
        self._items[item["ein"]] = item


def test_existing_item_unchanged_skip_write():
    store = InMemoryStore()
    config = RefreshConfig(environment="dev", mode="refresh_changed")

    def build(ein: str) -> dict[str, Any]:
        return _payload(model_version="2.0.0", score=91)

    refresh_materialized_profiles(config, ["123456789"], store, build)
    result = refresh_materialized_profiles(config, ["123456789"], store, build)

    assert result["written"] == 0
    assert result["skipped"] == 1
    assert result["reasons"]["unchanged"] == 1


def test_changed_hash_updates_write():
    store = InMemoryStore()
    config = RefreshConfig(environment="dev", mode="refresh_changed")

    refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload(score=75))
    result = refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload(score=95))

    assert result["written"] == 1
    assert result["updated"] == 1
    assert result["reasons"]["source_hash_changed"] == 1
    assert len(result["change_events"]) == 1


def test_changed_model_version_updates_write():
    store = InMemoryStore()
    config = RefreshConfig(environment="dev", mode="refresh_changed")

    refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload(model_version="1.0.0"))
    result = refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload(model_version="2.0.0"))

    assert result["written"] == 1
    assert result["updated"] == 1
    assert result["reasons"]["model_version_changed"] == 1


def test_missing_item_insert_write():
    store = InMemoryStore()
    config = RefreshConfig(environment="dev", mode="refresh_changed")
    result = refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload())

    assert result["written"] == 1
    assert result["inserted"] == 1
    assert result["reasons"]["missing_item"] == 1


def test_backfill_missing_mode_skips_existing():
    store = InMemoryStore()
    config = RefreshConfig(environment="dev", mode="backfill_missing")

    refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload())
    result = refresh_materialized_profiles(config, ["123456789"], store, lambda ein: _payload(score=99))

    assert result["written"] == 0
    assert result["skipped"] == 1
    assert result["reasons"]["backfill_existing"] == 1


def test_force_refresh_mode_writes_even_when_unchanged():
    store = InMemoryStore()
    refresh_materialized_profiles(
        RefreshConfig(environment="dev", mode="refresh_changed"),
        ["123456789"],
        store,
        lambda ein: _payload(),
    )
    result = refresh_materialized_profiles(
        RefreshConfig(environment="dev", mode="force_refresh"),
        ["123456789"],
        store,
        lambda ein: _payload(),
    )

    assert result["written"] == 1
    assert result["updated"] == 1
    assert result["reasons"]["force_refresh"] == 1


def test_nonprod_default_avoids_bulk_source_detection():
    store = InMemoryStore()
    result = refresh_materialized_profiles(
        RefreshConfig(environment="dev", mode="refresh_changed", source_detection_enabled=False),
        [],
        store,
        lambda ein: _payload(),
        source_detector=lambda: ["123456789", "987654321"],
    )

    assert result["selected"] == 0
    assert result["processed"] == 0
    assert store.put_calls == 0


def test_compare_changed_hash_and_model_paths():
    existing = {"source_hash": "abc", "model_version": "1.0.0"}
    assert compare_materialized_items(existing, {"source_hash": "xyz", "model_version": "1.0.0"}).reason == "source_hash_changed"
    assert compare_materialized_items(existing, {"source_hash": "abc", "model_version": "2.0.0"}).reason == "model_version_changed"


def test_change_event_unchanged_record_returns_none():
    before = {
        "scores": {"overall": 80},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    after = {
        "scores": {"overall": 80},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    assert build_change_event("123456789", before, after) is None


def test_change_event_score_only_change():
    before = {
        "scores": {"overall": 60},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    after = {
        "scores": {"overall": 75},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    event = build_change_event("123456789", before, after)
    assert event is not None
    assert "overall_score_threshold_crossed" in event["change_types"]


def test_change_event_decision_change():
    before = {
        "scores": {"overall": 72},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    after = {
        "scores": {"overall": 72},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "manual_review", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    event = build_change_event("123456789", before, after)
    assert event is not None
    assert "decision_status_changed" in event["change_types"]


def test_change_event_eligibility_change():
    before = {
        "scores": {"overall": 72},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    after = {
        "scores": {"overall": 40},
        "score_explanation": {"eligibility": "INELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "deny", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    event = build_change_event("123456789", before, after)
    assert event is not None
    assert "eligibility_changed" in event["change_types"]


def test_change_event_new_risk_and_compliance_flags():
    before = {
        "scores": {"overall": 72},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 100}},
        "decision": {"status": "approve", "risk_flags": []},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
    }
    after = {
        "scores": {"overall": 72},
        "score_explanation": {"eligibility": "ELIGIBLE", "factors": {"stale_filing_days": 500}},
        "decision": {"status": "approve_with_review", "risk_flags": ["state_compliance_flags_present"]},
        "verification": {"recent_990_on_file": True},
        "state_compliance": {"registration_status": "active", "compliance_flags": ["state_registration_expiring_soon"]},
    }
    event = build_change_event("123456789", before, after)
    assert event is not None
    assert "new_risk_flags" in event["change_types"]
    assert "new_compliance_flags" in event["change_types"]
    assert "filing_freshness_threshold_crossed" in event["change_types"]


def test_bootstrap_allowed_in_prod():
    store = InMemoryStore()

    def fetch_page(cursor: str | None, size: int) -> tuple[list[str], str | None]:
        assert size == 2
        if cursor is None:
            return ["123456789", "987654321"], "987654321"
        return [], None

    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all", batch_size=2),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=fetch_page,
    )

    assert result["status"] == "completed"
    assert result["total_seen"] == 2
    assert result["inserted"] == 2
    assert result["failed"] == 0


def test_bootstrap_blocked_by_default_in_nonprod():
    store = InMemoryStore()
    with pytest.raises(ValueError, match="only allowed"):
        refresh_materialized_profiles(
            RefreshConfig(environment="dev", mode="bootstrap_all"),
            [],
            store,
            lambda ein: _payload(),
            source_page_fetcher=lambda cursor, size: ([], None),
        )


def test_bootstrap_result_shape():
    store = InMemoryStore()
    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all"),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=lambda cursor, size: ([], None),
    )

    for key in [
        "status",
        "total_seen",
        "inserted",
        "updated",
        "skipped",
        "failed",
        "started_at",
        "completed_at",
        "duration_ms",
        "batch_count",
    ]:
        assert key in result


def test_bootstrap_batching_logic():
    store = InMemoryStore()
    pages = [
        (["100000001", "100000002"], "100000002"),
        (["100000003"], None),
    ]

    def fetch_page(cursor: str | None, size: int) -> tuple[list[str], str | None]:
        if not pages:
            return [], None
        return pages.pop(0)

    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all", batch_size=2),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=fetch_page,
    )
    assert result["batch_count"] == 2
    assert result["total_seen"] == 3


def test_bootstrap_skips_unchanged_items():
    store = InMemoryStore()

    def fetch_page(cursor: str | None, size: int) -> tuple[list[str], str | None]:
        if cursor is None:
            return ["123456789"], "123456789"
        return [], None

    refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all"),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=fetch_page,
    )
    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all"),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=fetch_page,
    )
    assert result["inserted"] == 0
    assert result["updated"] == 0
    assert result["skipped"] == 1


def test_bootstrap_handles_partial_failures_safely():
    store = InMemoryStore()

    def build(ein: str) -> dict[str, Any]:
        if ein == "987654321":
            raise RuntimeError("simulated build failure")
        return _payload()

    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all"),
        [],
        store,
        build,
        source_page_fetcher=lambda cursor, size: (["123456789", "987654321"], None) if cursor is None else ([], None),
    )

    assert result["failed"] == 1
    assert result["inserted"] == 1
    assert result["status"] == "completed_with_errors"
    assert len(result["errors"]) == 1


def test_bootstrap_can_checkpoint_with_max_batches():
    store = InMemoryStore()

    def fetch_page(cursor: str | None, size: int) -> tuple[list[str], str | None]:
        if cursor is None:
            return ["123456789"], "123456789"
        return ["987654321"], None

    result = refresh_materialized_profiles(
        RefreshConfig(environment="prod", mode="bootstrap_all", max_batches_per_run=1),
        [],
        store,
        lambda ein: _payload(),
        source_page_fetcher=fetch_page,
    )
    assert result["status"] == "partial"
    assert result["batch_count"] == 1
    assert result["next_cursor"] == "123456789"
