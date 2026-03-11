from __future__ import annotations

from typing import Any

from charity_status.serving.compare import compare_materialized_items
from charity_status.serving.refresh import RefreshConfig, refresh_materialized_profiles


def _payload(model_version: str = "1.0.0", score: int = 80) -> dict[str, Any]:
    return {
        "organization": {"ein": "12-3456789", "name": "Org"},
        "verification": {"irs_status": "active"},
        "scores": {"overall": score},
        "score_explanation": {"model_version": model_version, "score_data_sources": ["eo_bmf"]},
        "filing_summary": {"tax_year": "2024"},
        "enrichment": {"providers": [], "failures": []},
        "decision": {"status": "approve"},
        "summary": {"decision_status": "approve"},
        "audit": {"model_version": model_version},
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
