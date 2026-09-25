"""
CapitalFit — Unit Tests for Policy Rules Engine & Guardrails
"""

import pytest
from datetime import datetime, timedelta
from core.policy_rules import PolicyEngine, HAIR_CUT_MATRIX
from core.llm_explanation import LLMExplanationEngine

def test_haircut_calculation():
    engine = PolicyEngine()
    holdings = [
        {"symbol": "RELIANCE", "tier": "TIER_1_LARGE_CAP", "market_value": 100_000.0},  # 85k limit
        {"symbol": "ZOMATO", "tier": "TIER_2_MID_CAP", "market_value": 100_000.0},      # 70k limit
        {"symbol": "SUZLON", "tier": "TIER_3_SMALL_CAP", "market_value": 100_000.0},    # 50k limit
    ]
    eligible_limit = engine.calculate_eligible_limit(holdings)
    assert eligible_limit == (85_000.0 + 70_000.0 + 50_000.0)

def test_headroom_computation():
    engine = PolicyEngine()
    headroom = engine.compute_headroom(eligible_limit=205_000.0, current_funded=50_000.0)
    assert headroom == 155_000.0

def test_margin_call_exclusion():
    engine = PolicyEngine()
    account_data = {
        "account_id": "ANGEL_TEST_01",
        "current_funded": 10_000.0,
        "holdings": [{"symbol": "TCS", "tier": "TIER_1_LARGE_CAP", "market_value": 200_000.0}],
        "margin_call_active": True,
    }
    res = engine.evaluate_account(account_data)
    assert res["is_policy_eligible"] is False
    assert "EXCLUDED_MARGIN_CALL_ACTIVE" in res["rejection_reasons"]
    assert res["final_action"] == "SUPPRESS_POLICY"

def test_cooldown_exclusion():
    engine = PolicyEngine()
    recent_date = (datetime.now() - timedelta(days=5)).isoformat()
    account_data = {
        "account_id": "ANGEL_TEST_02",
        "current_funded": 10_000.0,
        "holdings": [{"symbol": "TCS", "tier": "TIER_1_LARGE_CAP", "market_value": 200_000.0}],
        "last_nudge_at": recent_date,
    }
    res = engine.evaluate_account(account_data)
    assert res["is_policy_eligible"] is False
    assert any("EXCLUDED_COOLDOWN_ACTIVE" in r for r in res["rejection_reasons"])

def test_ab_assignment_determinism():
    engine = PolicyEngine()
    group1 = engine.evaluate_ab_group("ANGEL_100005")
    group2 = engine.evaluate_ab_group("ANGEL_100005")
    assert group1 == group2

def test_guardrail_checker_and_fallback():
    llm = LLMExplanationEngine(apr_pct=12.0)
    
    # Text missing required APR and disclaimers
    invalid_text = "You can take a loan of ₹50,000 right now!"
    passed, errors = llm.run_guardrail_checker(invalid_text, expected_headroom=50000.0, expected_apr=12.0)
    assert passed is False
    assert len(errors) > 0

    # Policy output passing through fallback
    policy_out = {
        "account_id": "ANGEL_TEST_03",
        "proposed_nudge_amount": 50000.0,
        "eligible_limit": 100000.0,
        "current_funded": 50000.0,
    }
    nudge = llm.generate_nudge(policy_out, holdings_summary="RELIANCE")
    assert nudge["final_nudge_text"] != ""
    assert "₹50,000" in nudge["final_nudge_text"]
    assert "12.0%" in nudge["final_nudge_text"]
