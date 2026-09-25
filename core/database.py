"""
CapitalFit — Database & Persistence Store
Provides SQLite storage for client holdings, decision audit logs, and consent events.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "..", "capitalfit_data.db")

class DatabaseStore:
    """
    Manages SQLite database connection, schema initialization, and transactional queries.
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = os.path.abspath(db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """
        Creates tables for accounts, holdings, decision audit logs, and consent events.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                client_name TEXT,
                kyc_status TEXT DEFAULT 'VERIFIED',
                current_funded REAL DEFAULT 0.0,
                eligible_limit REAL DEFAULT 0.0,
                headroom REAL DEFAULT 0.0,
                margin_call_active INTEGER DEFAULT 0,
                in_collections INTEGER DEFAULT 0,
                risk_review_hold INTEGER DEFAULT 0,
                opted_out INTEGER DEFAULT 0,
                last_nudge_at TEXT,
                treatment_group TEXT,
                created_at TEXT
            )
        """)

        # Holdings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                symbol TEXT,
                tier TEXT,
                quantity INTEGER,
                market_value REAL,
                FOREIGN KEY(account_id) REFERENCES accounts(account_id)
            )
        """)

        # Immutable Decision Audit Trail (F7.4 / Section 12)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_audit (
                decision_id TEXT PRIMARY KEY,
                timestamp TEXT,
                account_id TEXT,
                inputs_snapshot_json TEXT,
                policy_version TEXT,
                eligible_limit REAL,
                headroom REAL,
                proposed_nudge_amount REAL,
                policy_outcome TEXT,
                ab_group TEXT,
                llm_output_text TEXT,
                guardrail_passed INTEGER,
                delivery_mode TEXT,
                rejection_reasons TEXT,
                FOREIGN KEY(account_id) REFERENCES accounts(account_id)
            )
        """)

        # Consent & Disclosure Events (F5.2 / Section 12)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consent_events (
                consent_id TEXT PRIMARY KEY,
                decision_id TEXT,
                account_id TEXT,
                consent_timestamp TEXT,
                disclosure_version TEXT,
                client_action TEXT,
                funded_amount REAL,
                transaction_id TEXT,
                FOREIGN KEY(decision_id) REFERENCES decision_audit(decision_id),
                FOREIGN KEY(account_id) REFERENCES accounts(account_id)
            )
        """)

        conn.commit()
        conn.close()
