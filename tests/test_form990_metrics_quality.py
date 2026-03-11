from datetime import date

from infrastructure.charity_status.form990.metrics import compute_derived_metrics
from infrastructure.charity_status.form990.quality import compute_filing_quality


def test_compute_derived_metrics_nominal_case():
    financials = {
        "total_revenue": 1000,
        "total_expenses": 800,
        "program_service_expenses": 600,
        "management_general_expenses": 100,
        "fundraising_expenses": 50,
        "contributions_revenue": 700,
        "total_assets_eoy": 500,
        "total_liabilities_eoy": 200,
    }

    metrics = compute_derived_metrics(financials)

    assert metrics["programExpenseRatio"] == 0.75
    assert metrics["adminExpenseRatio"] == 0.125
    assert metrics["fundraisingRatio"] == 0.0625
    assert metrics["liabilitiesToAssetsRatio"] == 0.4
    assert metrics["operatingMargin"] == 0.2
    assert metrics["fundraisingEfficiency"] == 14.0
    assert metrics["workingCapital"] == 300
    assert metrics["monthsOfRunway"] == 4.5


def test_compute_derived_metrics_null_safe():
    metrics = compute_derived_metrics({"total_revenue": None, "total_expenses": 0})

    assert metrics["programExpenseRatio"] is None
    assert metrics["operatingMargin"] is None
    assert metrics["monthsOfRunway"] is None


def test_compute_filing_quality_and_anomalies():
    filing = {
        "ein": "123",
        "tax_year": "2023",
        "filing_date": "2024-01-10",
        "return_type": "990",
        "total_revenue": 1000,
        "total_expenses": 800,
        "program_service_expenses": 0,
        "total_assets_eoy": 100,
        "total_liabilities_eoy": 200,
        "net_assets_eoy": -120,
        "amended_return": True,
        "narrative_sections_missing": ["mission_description_present"],
    }
    history = [
        {
            "total_revenue": 300,
            "total_expenses": 300,
            "total_liabilities_eoy": 50,
            "net_assets_eoy": -10,
            "amended_return": True,
        }
    ]

    quality = compute_filing_quality(filing, history=history, as_of=date(2024, 2, 1))

    assert quality["missingRequiredFieldsCount"] == 0
    assert quality["narrativeMissing"] is True
    assert quality["staleFilingDays"] == 22
    assert "large_revenue_swing" in quality["anomalyFlags"]
    assert "large_liabilities_jump" in quality["anomalyFlags"]
    assert "zero_program_expenses_with_nonzero_total" in quality["anomalyFlags"]
    assert "repeated_amended_return_pattern" in quality["anomalyFlags"]
    assert "negative_net_assets_pattern" in quality["anomalyFlags"]


def test_compute_filing_quality_partial_document():
    quality = compute_filing_quality({"ein": None}, history=[])

    assert quality["missingRequiredFieldsCount"] >= 1
    assert quality["anomalyFlags"] == []
