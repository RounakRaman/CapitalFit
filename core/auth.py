"""
CapitalFit — Authentication & Role-Based Access Control (RBAC)
Simulates SSO authentication and role authorization for the Streamlit Ops Console.
"""

import streamlit as st
import yaml
import os
from typing import List, Dict, Any

ROLES_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "roles.yaml")

def load_roles_config() -> Dict[str, Any]:
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE, "r") as f:
            return yaml.safe_load(f)
    # Default fallback mapping
    return {
        "roles": {
            "Ops": {"allowed_pages": ["1_Dashboard.py", "2_Cohort_Explorer.py"]},
            "Compliance": {"allowed_pages": ["1_Dashboard.py", "2_Cohort_Explorer.py", "3_Decision_Replay.py"]},
            "Product": {"allowed_pages": ["1_Dashboard.py", "2_Cohort_Explorer.py", "3_Decision_Replay.py", "4_Scenario_Simulator.py"]},
            "Risk": {"allowed_pages": ["1_Dashboard.py", "2_Cohort_Explorer.py", "3_Decision_Replay.py", "4_Scenario_Simulator.py", "5_Admin_Overrides.py"]},
        }
    }

class AuthManager:
    """
    Manages session state authentication and role checks.
    """

    @staticmethod
    def init_session_state():
        if "user" not in st.session_state:
            st.session_state["user"] = {
                "authenticated": True,
                "email": "rounak.raman@angelone.in",
                "name": "Rounak Raman (NBU Lead)",
                "role": "Risk",  # Default to Risk for full demo access
            }

    @staticmethod
    def get_current_user() -> Dict[str, Any]:
        AuthManager.init_session_state()
        return st.session_state["user"]

    @staticmethod
    def set_user_role(role_name: str):
        AuthManager.init_session_state()
        st.session_state["user"]["role"] = role_name

    @staticmethod
    def check_page_access(page_filename: str) -> bool:
        user = AuthManager.get_current_user()
        role = user.get("role", "Ops")
        config = load_roles_config()
        role_info = config.get("roles", {}).get(role, {})
        allowed = role_info.get("allowed_pages", [])
        return page_filename in allowed
