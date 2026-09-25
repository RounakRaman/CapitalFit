"""
CapitalFit — Synthetic Data Generator
Populates the database with realistic synthetic MTF/LAS client accounts, stock portfolios,
decision audit traces, and consent events for immediate local Streamlit testing and demo.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.database import DatabaseStore
from core.policy_rules import PolicyEngine
from core.llm_explanation import LLMExplanationEngine
from core.audit_logger import AuditLogger

SAMPLE_STOCKS = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "tier": "TIER_1_LARGE_CAP"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "tier": "TIER_1_LARGE_CAP"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "tier": "TIER_1_LARGE_CAP"},
    {"symbol": "INFY.NS", "name": "Infosys Ltd", "tier": "TIER_1_LARGE_CAP"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "tier": "TIER_2_MID_CAP"},
    {"symbol": "ZOMATO.NS", "name": "Zomato Ltd", "tier": "TIER_2_MID_CAP"},
    {"symbol": "YESBANK.NS", "name": "Yes Bank Ltd", "tier": "TIER_3_SMALL_CAP"},
    {"symbol": "SUZLON.NS", "name": "Suzlon Energy Ltd", "tier": "TIER_3_SMALL_CAP"},
]

FIRST_NAMES = ["Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Sneha", "Aditya", "Neha", "Rahul", "Pooja"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Mehta", "Gupta", "Reddy", "Joshi", "Nair", "Rao", "Kumar"]

class SyntheticDataGenerator:
    """
    Seeds database with synthetic accounts and runs initial evaluation batch.
    """

    def __init__(self, db_store: DatabaseStore = None):
        self.db_store = db_store or DatabaseStore()
        self.policy_engine = PolicyEngine()
        self.llm_engine = LLMExplanationEngine()
        self.audit_logger = AuditLogger(self.db_store)

    def generate_seed_data(self, num_accounts: int = 250, clear_existing: bool = True):
        """
        Populates synthetic database tables.
        """
        conn = self.db_store.get_connection()
        cursor = conn.cursor()

        if clear_existing:
            cursor.execute("DELETE FROM consent_events")
            cursor.execute("DELETE FROM decision_audit")
            cursor.execute("DELETE FROM holdings")
            cursor.execute("DELETE FROM accounts")
            conn.commit()

        random.seed(42)  # Deterministic seed for reproducible testing

        accounts_created = 0
        now = datetime.now()

        for i in range(1, num_accounts + 1):
            account_id = f"ANGEL_{100000 + i}"
            client_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            
            # Risk condition allocation (~15% total risk excluded)
            rand_flag = random.random()
            margin_call_active = 1 if rand_flag < 0.04 else 0
            in_collections = 1 if (0.04 <= rand_flag < 0.07) else 0
            risk_review_hold = 1 if (0.07 <= rand_flag < 0.10) else 0
            opted_out = 1 if (0.10 <= rand_flag < 0.13) else 0

            # Cooldown condition allocation (~10% with recent nudge)
            last_nudge_at = None
            if random.random() < 0.15:
                days_ago = random.randint(1, 20)
                last_nudge_at = (now - timedelta(days=days_ago)).isoformat()

            # Generate holdings
            num_holdings = random.randint(2, 6)
            holdings = []
            selected_stocks = random.sample(SAMPLE_STOCKS, num_holdings)
            total_mkt_val = 0.0
            
            for stk in selected_stocks:
                qty = random.randint(50, 1000)
                price = random.uniform(200.0, 3500.0)
                mkt_val = round(qty * price, 2)
                total_mkt_val += mkt_val
                holdings.append({
                    "symbol": stk["symbol"],
                    "tier": stk["tier"],
                    "quantity": qty,
                    "market_value": mkt_val,
                })

            eligible_limit = self.policy_engine.calculate_eligible_limit(holdings)
            
            # Funded ratio between 10% and 85% of eligible limit
            funding_ratio = random.uniform(0.10, 0.85)
            current_funded = round(eligible_limit * funding_ratio, 2)
            headroom = max(0.0, round(eligible_limit - current_funded, 2))

            ab_group = self.policy_engine.evaluate_ab_group(account_id)

            # Insert account
            cursor.execute(
                """
                INSERT INTO accounts (
                    account_id, client_name, kyc_status, current_funded, eligible_limit, headroom,
                    margin_call_active, in_collections, risk_review_hold, opted_out, last_nudge_at,
                    treatment_group, created_at
                ) VALUES (?, ?, 'VERIFIED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, client_name, current_funded, eligible_limit, headroom,
                    margin_call_active, in_collections, risk_review_hold, opted_out, last_nudge_at,
                    ab_group, now.isoformat()
                ),
            )

            # Insert holdings
            for h in holdings:
                cursor.execute(
                    """
                    INSERT INTO holdings (account_id, symbol, tier, quantity, market_value)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (account_id, h["symbol"], h["tier"], h["quantity"], h["market_value"]),
                )

            accounts_created += 1

        conn.commit()
        conn.close()

        # Run evaluation batch over seeded accounts
        self._run_initial_evaluation_batch()

    def _run_initial_evaluation_batch(self):
        """
        Evaluates all seeded accounts and creates decision audit & consent records.
        """
        conn = self.db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT account_id FROM accounts")
        account_ids = [r[0] for r in cursor.fetchall()]

        for acc_id in account_ids:
            cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (acc_id,))
            acc_data = dict(cursor.fetchone())

            cursor.execute("SELECT symbol, tier, quantity, market_value FROM holdings WHERE account_id = ?", (acc_id,))
            acc_data["holdings"] = [dict(h) for h in cursor.fetchall()]

            # Evaluate Policy
            policy_res = self.policy_engine.evaluate_account(acc_data)

            explanation_res = None
            if policy_res["is_policy_eligible"]:
                top_symbols = ", ".join([h["symbol"].split(".")[0] for h in acc_data["holdings"][:2]])
                explanation_res = self.llm_engine.generate_nudge(policy_res, holdings_summary=top_symbols)

            # Log decision
            dec_id = self.audit_logger.log_decision(
                account_id=acc_id,
                policy_result=policy_res,
                explanation_result=explanation_res,
                inputs_snapshot={"account_id": acc_id, "holdings_count": len(acc_data["holdings"])},
            )

            # Simulate client response for NUDGE items in treatment (~15% conversion)
            if policy_res["final_action"] == "NUDGE":
                rand_resp = random.random()
                if rand_resp < 0.18:  # Accepted
                    funded_amt = policy_res["proposed_nudge_amount"]
                    self.audit_logger.log_consent_event(
                        decision_id=dec_id,
                        account_id=acc_id,
                        client_action="ACCEPTED",
                        funded_amount=funded_amt,
                    )
                elif rand_resp < 0.35:  # Declined
                    self.audit_logger.log_consent_event(
                        decision_id=dec_id,
                        account_id=acc_id,
                        client_action="DECLINED",
                        funded_amount=0.0,
                    )

        conn.close()

if __name__ == "__main__":
    gen = SyntheticDataGenerator()
    gen.generate_seed_data(num_accounts=250)
    print("Synthetic data seeded successfully!")
