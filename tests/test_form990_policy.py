from __future__ import annotations

from datetime import datetime, timezone

from infrastructure.verification.form990.policy import IngestPolicyConfig, select_target_years


def test_incremental_target_year_selection_default_window():
    years, meta = select_target_years(
        ["2022", "2023", "2024", "2025"],
        IngestPolicyConfig(mode="incremental", incremental_year_window=2, reconciliation_enabled=False),
        now=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    assert years == ["2024", "2025"]
    assert meta["effective_mode"] == "incremental"


def test_reconciliation_target_year_selection():
    years, meta = select_target_years(
        ["2022", "2023", "2024", "2025"],
        IngestPolicyConfig(
            mode="incremental",
            reconciliation_enabled=True,
            reconciliation_cadence_days=30,
            last_reconciliation_at="2025-01-01T00:00:00+00:00",
        ),
        now=datetime(2025, 3, 1, tzinfo=timezone.utc),
    )
    assert years == ["2022", "2023", "2024", "2025"]
    assert meta["effective_mode"] == "reconciliation"


def test_noop_behavior_with_no_discovered_years():
    years, meta = select_target_years(
        [],
        IngestPolicyConfig(mode="incremental"),
        now=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    assert years == []
    assert meta["fallback_used"] is True


def test_config_override_target_years():
    years, meta = select_target_years(
        ["2022", "2023", "2024", "2025"],
        IngestPolicyConfig(mode="incremental", target_years=("2023", "2025")),
        now=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    assert years == ["2023", "2025"]
    assert meta["effective_mode"] == "incremental"


def test_safe_fallback_when_expected_years_missing():
    years, meta = select_target_years(
        ["legacy_a", "legacy_b"],
        IngestPolicyConfig(mode="incremental", incremental_year_window=2, reconciliation_enabled=False),
        now=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    assert years == ["legacy_a", "legacy_b"]
    assert meta["fallback_used"] is True

