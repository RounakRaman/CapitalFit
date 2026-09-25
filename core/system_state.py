"""
CapitalFit — System Master State & Kill Switch Manager
Provides global state control for pausing or resuming agent nudges in real time (FR-09 / F8.5).
"""

import json
import os
from typing import Dict, Any

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "system_state.json")

class SystemStateManager:
    """
    Manages global system flags like Master Kill Switch and global override rules.
    """

    @staticmethod
    def get_state() -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "agent_paused": False,
            "paused_by": None,
            "paused_at": None,
            "pause_reason": None,
            "manual_excluded_accounts": [],
        }

    @staticmethod
    def set_kill_switch(paused: bool, user_email: str = "risk@angelone.in", reason: str = ""):
        state = SystemStateManager.get_state()
        state["agent_paused"] = paused
        state["paused_by"] = user_email if paused else None
        state["paused_at"] = __import__("datetime").datetime.now().isoformat() if paused else None
        state["pause_reason"] = reason if paused else None

        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    @staticmethod
    def add_account_override(account_id: str, exclude: bool = True):
        state = SystemStateManager.get_state()
        excluded = set(state.get("manual_excluded_accounts", []))
        if exclude:
            excluded.add(account_id)
        else:
            excluded.discard(account_id)
        state["manual_excluded_accounts"] = list(excluded)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
