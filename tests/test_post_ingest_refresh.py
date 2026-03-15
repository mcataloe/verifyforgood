from __future__ import annotations

from typing import Any

from charity_status.serving.post_ingest_refresh import PostIngestRefreshConfig, refresh_from_ingest_output
from infrastructure.charity_status.scoring import SCORING_MODEL_VERSION


class InMemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self.put_calls = 0

    def get_profile(self, ein: str) -> dict[str, Any] | None:
        return self._items.get(ein)

    def put_profile(self, item: dict[str, Any]) -> None:
        self.put_calls += 1
        self._items[item["ein"]] = item


def _payload(score: int = 80, decision_status: str = "approve", eligibility: str = "ELIGIBLE") -> dict[str, Any]:
    return {
        "organization": {"ein": "12-3456789", "name": "Org"},
        "verification": {"irs_status": "active", "recent_990_on_file": True},
        "scores": {"overall": score},
        "score_explanation": {"model_version": SCORING_MODEL_VERSION, "score_data_sources": ["eo_bmf"], "eligibility": eligibility, "factors": {"stale_filing_days": 100}},
        "filing_summary": {"tax_year": "2024"},
        "enrichment": {"providers": [], "failures": []},
        "decision": {"status": decision_status, "risk_flags": []},
        "summary": {"decision_status": decision_status},
        "audit": {"model_version": SCORING_MODEL_VERSION},
        "state_compliance": {"registration_status": "active", "compliance_flags": []},
        "external_signals": {},
        "policy_evaluation": {"policy_id": "default", "final_recommendation": decision_status},
        "final_recommendation": decision_status,
    }


def test_no_affected_eins():
    store = InMemoryStore()
    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": []},
        store=store,
        profile_builder=lambda ein: _payload(),
    )
    assert result["affected_ein_count"] == 0
    assert result["refreshed_count"] == 0
    assert result["failed_count"] == 0


def test_one_ein_changed_filing():
    store = InMemoryStore()
    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789"], "affected_filing_ids": {"123456789": ["obj-1"]}},
        store=store,
        profile_builder=lambda ein: _payload(score=91),
    )
    assert result["affected_ein_count"] == 1
    assert result["refreshed_count"] == 1
    assert result["results"][0]["source_filing_ids"] == ["obj-1"]


def test_multiple_eins_mixed_changed_unchanged():
    store = InMemoryStore()
    refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789", "987654321"]},
        store=store,
        profile_builder=lambda ein: _payload(score=80 if ein == "123456789" else 95),
    )

    def build(ein: str) -> dict[str, Any]:
        if ein == "123456789":
            return _payload(score=80)
        return _payload(score=99)

    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-2", "affected_eins": ["123456789", "987654321"]},
        store=store,
        profile_builder=build,
    )
    assert result["affected_ein_count"] == 2
    assert result["refreshed_count"] == 1
    assert result["unchanged_count"] == 1


def test_unchanged_profile_noop_materialization():
    store = InMemoryStore()
    refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789"]},
        store=store,
        profile_builder=lambda ein: _payload(score=80),
    )
    before = store.put_calls
    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789"]},
        store=store,
        profile_builder=lambda ein: _payload(score=80),
    )
    assert result["unchanged_count"] == 1
    assert store.put_calls == before


def test_failed_ein_refresh_continues_processing():
    store = InMemoryStore()

    def build(ein: str) -> dict[str, Any] | None:
        if ein == "987654321":
            raise RuntimeError("boom")
        return _payload(score=90)

    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789", "987654321"]},
        store=store,
        profile_builder=build,
    )
    assert result["refreshed_count"] == 1
    assert result["failed_count"] == 1
    assert len(result["results"]) == 2


def test_change_event_emission_on_material_change():
    store = InMemoryStore()
    refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-1", "affected_eins": ["123456789"]},
        store=store,
        profile_builder=lambda ein: _payload(score=70, decision_status="approve"),
    )
    result = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output={"run_id": "ing-2", "affected_eins": ["123456789"]},
        store=store,
        profile_builder=lambda ein: _payload(score=50, decision_status="manual_review", eligibility="INELIGIBLE"),
    )
    assert result["refreshed_count"] == 1
    assert len(result["change_events"]) == 1


def test_idempotent_rerun_behavior():
    store = InMemoryStore()
    ingest = {"run_id": "ing-1", "affected_eins": ["123456789"], "affected_filing_ids": {"123456789": ["obj-1"]}}
    first = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output=ingest,
        store=store,
        profile_builder=lambda ein: _payload(score=80),
    )
    second = refresh_from_ingest_output(
        config=PostIngestRefreshConfig(environment="dev"),
        ingest_output=ingest,
        store=store,
        profile_builder=lambda ein: _payload(score=80),
    )
    assert first["refreshed_count"] == 1
    assert second["refreshed_count"] == 0
    assert second["unchanged_count"] == 1
