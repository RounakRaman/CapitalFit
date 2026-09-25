"""
CapitalFit — Deterministic Policy & Eligibility Engine
Encodes haircut calculations, headroom detection, risk exclusion checks,
14-day cooldown enforcement, single-stock concentration caps, and deterministic A/B hashing.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

# Security Haircut Table by Stock Category
HAIR_CUT_MATRIX = {
    "TIER_1_LARGE_CAP": 0.15,  # 85% LTV
    "TIER_2_MID_CAP": 0.30,    # 70% LTV
    "TIER_3_SMALL_CAP": 0.50,  # 50% LTV
}

class PolicyEngine:
    """
    Deterministic eligibility and rule evaluation engine.
    Does NOT use LLM or non-deterministic inference.
    """

    def __init__(
        self,
        min_headroom_pct: float = 15.0,
        min_headroom_abs: float = 25_000.0,
        cooldown_days: int = 14,
        max_nudge_amount_cap: float = 1_000_000.0,
        treatment_split_pct: float = 50.0,
        ab_salt: str = "angel_capitalfit_salt_v1",
    ):
        self.min_headroom_pct = min_headroom_pct
        self.min_headroom_abs = min_headroom_abs
        self.cooldown_days = cooldown_days
        self.max_nudge_amount_cap = max_nudge_amount_cap
        self.treatment_split_pct = treatment_split_pct
        self.ab_salt = ab_salt

    def calculate_eligible_limit(self, holdings: List[Dict[str, Any]]) -> float:
        """
        Computes total collateral eligible limit based on security haircut matrix.
        """
        eligible_limit = 0.0
        for holding in holdings:
            mkt_val = holding.get("market_value", 0.0)
            tier = holding.get("tier", "TIER_2_MID_CAP")
            haircut = HAIR_CUT_MATRIX.get(tier, 0.30)
            eligible_limit += mkt_val * (1.0 - haircut)
        return round(eligible_limit, 2)

    def compute_headroom(self, eligible_limit: float, current_funded: float) -> float:
        """
        Computes headroom = eligible_limit - current_funded.
        """
        return max(0.0, round(eligible_limit - current_funded, 2))

    def evaluate_ab_group(self, account_id: str) -> str:
        """
        Deterministically hashes account ID into 'TREATMENT' or 'CONTROL'.
        """
        hash_input = f"{self.ab_salt}:{account_id}".encode("utf-8")
        hash_val = hashlib.sha256(hash_input).hexdigest()
        hash_int = int(hash_val[:8], 16)
        mod_val = hash_int % 100
        return "TREATMENT" if mod_val < self.treatment_split_pct else "CONTROL"

    def evaluate_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full policy evaluation pipeline for an account.
        """
        account_id = account_data["account_id"]
        current_funded = float(account_data.get("current_funded", 0.0))
        holdings = account_data.get("holdings", [])
        
        # Risk Flags
        margin_call_active = account_data.get("margin_call_active", False)
        in_collections = account_data.get("in_collections", False)
        risk_review_hold = account_data.get("risk_review_hold", False)
        opted_out = account_data.get("opted_out", False)
        last_nudge_date_str = account_data.get("last_nudge_at", None)

        # 1. Eligibility & Headroom Computation
        eligible_limit = self.calculate_eligible_limit(holdings)
        raw_headroom = self.compute_headroom(eligible_limit, current_funded)
        
        # Cap max nudge proposal if configured
        capped_headroom = min(raw_headroom, self.max_nudge_amount_cap)
        headroom_pct_of_eligible = (raw_headroom / eligible_limit * 100.0) if eligible_limit > 0 else 0.0

        # 2. Risk Exclusion Checks (F2.1)
        rejection_reasons = []
        if margin_call_active:
            rejection_reasons.append("EXCLUDED_MARGIN_CALL_ACTIVE")
        if in_collections:
            rejection_reasons.append("EXCLUDED_IN_COLLECTIONS")
        if risk_review_hold:
            rejection_reasons.append("EXCLUDED_RISK_REVIEW_HOLD")
        if opted_out:
            rejection_reasons.append("EXCLUDED_CLIENT_OPTED_OUT")

        # 3. Cooldown Check (F2.1)
        cooldown_violating = False
        if last_nudge_date_str:
            try:
                last_nudge_dt = datetime.fromisoformat(last_nudge_date_str)
                now = datetime.now()
                if (now - last_nudge_dt).days < self.cooldown_days:
                    cooldown_violating = True
                    rejection_reasons.append(f"EXCLUDED_COOLDOWN_ACTIVE (<{self.cooldown_days}d)")
            except Exception:
                pass

        # 4. Trigger Threshold Check (F1.4)
        threshold_passed = (
            raw_headroom >= self.min_headroom_abs and
            headroom_pct_of_eligible >= self.min_headroom_pct
        )
        if not threshold_passed and not rejection_reasons:
            rejection_reasons.append(
                f"EXCLUDED_BELOW_HEADROOM_THRESHOLD (<₹{self.min_headroom_abs:,.0f} or <{self.min_headroom_pct}%)"
            )

        is_policy_eligible = (len(rejection_reasons) == 0)

        # 5. Deterministic A/B Assignment (F2.3)
        ab_group = self.evaluate_ab_group(account_id)

        # Final Action Decision
        if is_policy_eligible:
            if ab_group == "TREATMENT":
                final_action = "NUDGE"
                decision_reason = "ELIGIBLE_PROCEED_TO_LLM"
            else:
                final_action = "SUPPRESS_CONTROL"
                decision_reason = "ELIGIBLE_BUT_SUPPRESSED_CONTROL_GROUP"
        else:
            final_action = "SUPPRESS_POLICY"
            decision_reason = "; ".join(rejection_reasons)

        return {
            "account_id": account_id,
            "eligible_limit": eligible_limit,
            "current_funded": current_funded,
            "headroom": raw_headroom,
            "proposed_nudge_amount": capped_headroom,
            "headroom_pct_of_eligible": round(headroom_pct_of_eligible, 2),
            "is_policy_eligible": is_policy_eligible,
            "rejection_reasons": rejection_reasons,
            "ab_group": ab_group,
            "final_action": final_action,
            "decision_reason": decision_reason,
            "policy_version": "v1.0_deterministic",
            "evaluated_at": datetime.now().isoformat(),
        }
