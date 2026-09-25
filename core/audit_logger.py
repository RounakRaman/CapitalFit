"""
CapitalFit — Audit Logging & Telemetry Layer
Handles append-only logging of decision traces and consent events,
and provides fast lookup methods for Decision Replay and live funnel telemetry.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.database import DatabaseStore

class AuditLogger:
    """
    Immutable decision trace logger and query service.
    """

    def __init__(self, db_store: Optional[DatabaseStore] = None):
        self.db_store = db_store or DatabaseStore()

    def log_decision(
        self,
        account_id: str,
        policy_result: Dict[str, Any],
        explanation_result: Optional[Dict[str, Any]] = None,
        inputs_snapshot: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Logs a decision trace immutably into the decision_audit table.
        """
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now().isoformat()

        llm_text = explanation_result["final_nudge_text"] if explanation_result else ""
        guardrail_passed = 1 if (explanation_result and explanation_result.get("guardrail_passed", False)) else 0
        delivery_mode = explanation_result["delivery_mode"] if explanation_result else "NONE"
        rejection_reasons_str = json.dumps(policy_result.get("rejection_reasons", []))

        conn = self.db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO decision_audit (
                decision_id, timestamp, account_id, inputs_snapshot_json,
                policy_version, eligible_limit, headroom, proposed_nudge_amount,
                policy_outcome, ab_group, llm_output_text, guardrail_passed,
                delivery_mode, rejection_reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                timestamp,
                account_id,
                json.dumps(inputs_snapshot or {}),
                policy_result.get("policy_version", "v1.0_deterministic"),
                policy_result.get("eligible_limit", 0.0),
                policy_result.get("headroom", 0.0),
                policy_result.get("proposed_nudge_amount", 0.0),
                policy_result.get("final_action", "SUPPRESS_POLICY"),
                policy_result.get("ab_group", "CONTROL"),
                llm_text,
                guardrail_passed,
                delivery_mode,
                rejection_reasons_str,
            ),
        )

        # Update last_nudge_at in accounts table if NUDGE was delivered
        if policy_result.get("final_action") == "NUDGE":
            cursor.execute(
                "UPDATE accounts SET last_nudge_at = ? WHERE account_id = ?",
                (timestamp, account_id),
            )

        conn.commit()
        conn.close()
        return decision_id

    def log_consent_event(
        self,
        decision_id: str,
        account_id: str,
        client_action: str,  # ACCEPTED | DECLINED | OPTED_OUT
        funded_amount: float = 0.0,
        disclosure_version: str = "v1.0_KFS_MTF",
    ) -> str:
        """
        Logs a client consent, decline, or opt-out event immutably.
        """
        consent_id = f"cns_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now().isoformat()
        transaction_id = f"tx_{uuid.uuid4().hex[:10]}" if client_action == "ACCEPTED" else None

        conn = self.db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO consent_events (
                consent_id, decision_id, account_id, consent_timestamp,
                disclosure_version, client_action, funded_amount, transaction_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                consent_id,
                decision_id,
                account_id,
                timestamp,
                disclosure_version,
                client_action,
                funded_amount,
                transaction_id,
            ),
        )

        if client_action == "OPTED_OUT":
            cursor.execute("UPDATE accounts SET opted_out = 1 WHERE account_id = ?", (account_id,))
        elif client_action == "ACCEPTED" and funded_amount > 0:
            cursor.execute(
                "UPDATE accounts SET current_funded = current_funded + ? WHERE account_id = ?",
                (funded_amount, account_id),
            )

        conn.commit()
        conn.close()
        return consent_id

    def get_decision_trace(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstructs the full decision trace for a given decision_id in <2s (F8.2 / FR-08).
        """
        conn = self.db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM decision_audit WHERE decision_id = ?", (decision_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        
        result = dict(row)
        result["inputs_snapshot"] = json.loads(result["inputs_snapshot_json"] or "{}")
        result["rejection_reasons"] = json.loads(result["rejection_reasons"] or "[]")
        return result

    def search_recent_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches recent decisions for Cohort Explorer & Decision Replay list views.
        """
        conn = self.db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM decision_audit ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            d["inputs_snapshot"] = json.loads(d["inputs_snapshot_json"] or "{}")
            d["rejection_reasons"] = json.loads(d["rejection_reasons"] or "[]")
            out.append(d)
        return out

    def get_funnel_summary(self) -> Dict[str, Any]:
        """
        Computes aggregate funnel metrics for the dashboard (F8.4 / Section 16).
        """
        conn = self.db_store.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM accounts")
        total_accounts = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decision_audit")
        evaluated_decisions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decision_audit WHERE policy_outcome = 'NUDGE'")
        nudges_sent = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM consent_events WHERE client_action = 'ACCEPTED'")
        consents_accepted = cursor.fetchone()[0]

        cursor.execute("SELECT COALESCE(SUM(funded_amount), 0.0) FROM consent_events WHERE client_action = 'ACCEPTED'")
        total_funded_volume = cursor.fetchone()[0]

        conn.close()

        conversion_pct = (consents_accepted / nudges_sent * 100.0) if nudges_sent > 0 else 0.0

        return {
            "total_accounts": total_accounts,
            "evaluated_decisions": evaluated_decisions,
            "nudges_sent": nudges_sent,
            "consents_accepted": consents_accepted,
            "conversion_pct": round(conversion_pct, 2),
            "total_funded_volume_inr": round(total_funded_volume, 2),
            "total_funded_volume_cr": round(total_funded_volume / 10_000_000.0, 2),
        }
