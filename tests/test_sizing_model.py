"""
CapitalFit — Unit Tests for Financial Sizing Model
Verifies formula parity with NBU_Monetization.xlsx
"""

import pytest
from core.sizing_model import FinancialSizingModel

def test_base_case_financials():
    model = FinancialSizingModel(
        total_eligible_accounts=550_000,
        rollout_coverage_pct=70.0,
        avg_headroom_per_account=61_727.0,
        gross_interest_apr_pct=12.0,
        cost_of_funds_pct=7.25,
        ecl_pct=0.50,
        year1_build_run_cost_cr=1.20,
    )
    res = model.calculate_metrics(conversion_rate_pct=0.86)
    
    # Verify values match PRD & Excel targets
    assert res["exposed_accounts"] == 385_000
    assert res["funded_accounts"] == 3_311
    assert abs(res["incremental_book_cr"] - 204.38) < 1.0  # Approx ~203.7-204.4 Cr
    assert res["gross_interest_cr"] > 24.0
    assert res["net_contribution_cr"] > 4.0
    assert res["contribution_roi"] >= 3.0
    assert res["clears_3x_roi_gate"] is True

def test_worst_case_fails_gate():
    model = FinancialSizingModel()
    res = model.calculate_metrics(conversion_rate_pct=0.50)
    assert res["contribution_roi"] < 3.0
    assert res["clears_3x_roi_gate"] is False

def test_best_case_exceeds_gate():
    model = FinancialSizingModel()
    res = model.calculate_metrics(conversion_rate_pct=1.50)
    assert res["contribution_roi"] > 6.0
    assert res["clears_3x_roi_gate"] is True
