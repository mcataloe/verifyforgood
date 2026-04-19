from infrastructure.verification.scoring.peer_stats import compute_peer_stats
from infrastructure.verification.scoring.peers import assign_peer_group, revenue_band


def test_revenue_band_assignment():
    assert revenue_band(100000) == "under_250k"
    assert revenue_band(300000) == "250k_to_1m"
    assert revenue_band(5_000_000) == "1m_to_10m"
    assert revenue_band(50_000_000) == "10m_to_100m"
    assert revenue_band(500_000_000) == "100m_plus"
    assert revenue_band(None) == "unknown"


def test_peer_group_assignment_with_fallbacks():
    group = assign_peer_group(ntee_code="P20", org_type="03", total_revenue=750000, state="il")
    assert group["ntee"] == "P"
    assert group["org_type"] == "03"
    assert group["revenue_band"] == "250k_to_1m"
    assert group["state"] == "IL"

    fallback = assign_peer_group(ntee_code=None, org_type=None, total_revenue=None, state=None)
    assert fallback["ntee"] == "unknown"
    assert fallback["org_type"] == "unknown"
    assert fallback["revenue_band"] == "unknown"


def test_compute_peer_stats_distribution():
    rows = [
        {"programExpenseRatio": 0.6, "operatingMargin": 0.01},
        {"programExpenseRatio": 0.7, "operatingMargin": 0.03},
        {"programExpenseRatio": 0.8, "operatingMargin": 0.05},
        {"programExpenseRatio": 0.9, "operatingMargin": 0.07},
    ]
    stats = compute_peer_stats(rows, ["programExpenseRatio", "operatingMargin"])

    assert stats["count"] == 4
    assert stats["metrics"]["programExpenseRatio"]["median"] == 0.75
    assert stats["metrics"]["programExpenseRatio"]["p25"] is not None
    assert stats["metrics"]["operatingMargin"]["min"] == 0.01

