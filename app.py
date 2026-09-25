"""
CapitalFit — Internal Ops & Governance Console
Main Entry Point for Streamlit Application.
"""

import streamlit as st
import os
import sys

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.auth import AuthManager
from core.database import DatabaseStore
from core.audit_logger import AuditLogger
from core.system_state import SystemStateManager
from data.synthetic_generator import SyntheticDataGenerator

st.set_page_config(
    page_title="CapitalFit | Angel One NBU Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Auth Session
AuthManager.init_session_state()
user = AuthManager.get_current_user()

# Auto-seed synthetic data if database is empty
db_store = DatabaseStore()
audit_logger = AuditLogger(db_store)
funnel_summary = audit_logger.get_funnel_summary()

if funnel_summary["total_accounts"] == 0:
    with st.spinner("Initializing database & seeding synthetic MTF/LAS account portfolio..."):
        gen = SyntheticDataGenerator(db_store)
        gen.generate_seed_data(num_accounts=250)
        funnel_summary = audit_logger.get_funnel_summary()

# Check Kill Switch status
sys_state = SystemStateManager.get_state()
is_paused = sys_state.get("agent_paused", False)

# Sidebar Header & Role Switcher
with st.sidebar:
    st.markdown("## ⚡ **Angel One NBU**")
    st.markdown("### **CapitalFit Ops Console**")
    st.caption("Stage 1 — MTF / LAS Headroom Agent")
    st.divider()

    st.markdown("#### 👤 **SSO User Context**")
    st.write(f"**User:** {user['name']}")
    st.write(f"**Email:** {user['email']}")

    # Role selector for live role testing
    selected_role = st.selectbox(
        "Switch Active Role (RBAC):",
        ["Risk", "Compliance", "Product", "Ops"],
        index=["Risk", "Compliance", "Product", "Ops"].index(user["role"]),
    )
    if selected_role != user["role"]:
        AuthManager.set_user_role(selected_role)
        st.rerun()

    st.divider()
    if is_paused:
        st.error("🚨 **AGENT PAUSED BY RISK**")
    else:
        st.success("🟢 **AGENT SYSTEM ACTIVE**")

    if st.button("🔄 Re-Seed Synthetic Data", use_container_width=True):
        with st.spinner("Re-seeding database..."):
            gen = SyntheticDataGenerator(db_store)
            gen.generate_seed_data(num_accounts=250)
            st.success("Database re-seeded successfully!")
            st.rerun()

# Main Header
st.title("⚡ CapitalFit — Collateral Headroom Agent")
st.markdown(
    "**Angel One New Business Unit (NBU)** — Real-time collateral headroom discovery, "
    "deterministic decisioning, grounded LLM explanations, and compliance governance."
)

st.divider()

# System Metrics Summary
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Eligible Cohort", f"{funnel_summary['total_accounts']:,} Accounts")
with col2:
    st.metric("Decisions Evaluated", f"{funnel_summary['evaluated_decisions']:,}")
with col3:
    st.metric("Nudges Sent", f"{funnel_summary['nudges_sent']:,}")
with col4:
    st.metric("Consented / Funded", f"{funnel_summary['consents_accepted']:,}")
with col5:
    st.metric("Funded Conversion", f"{funnel_summary['conversion_pct']}%")

st.divider()

# Navigation & Architecture Guide
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("📌 System Architecture Overview")
    st.markdown("""
    1. **Data & Signal Layer**: Real-time ingestion of MTF ledger, stock holdings, haircuts, and current funded limits.
    2. **Deterministic Policy Engine**: Encodes minimum headroom thresholds (≥15% AND ≥₹25k), risk exclusions (margin calls, collections, opt-outs), 14-day cooldown, and salted A/B group assignment.
    3. **LLM Phrasing & Guardrail Layer**: LLM acts strictly as a phrasing layer on deterministic payloads, verified by an automated compliance checker with static template fallback.
    4. **Consent & Disclosure**: Key-Fact-Statement (KFS) disclaimers with immutable audit trail.
    5. **Ops Console**: Live monitoring, cohort explorer, instant decision replay (<2s), financial scenario simulator, and emergency kill switch.
    """)

with col_right:
    st.subheader("🧭 Console Navigation Guide")
    st.markdown("""
    - **📊 1_Dashboard**: Live funnel metrics, A/B lift charts, revenue tracking.
    - **🔍 2_Cohort_Explorer**: Searchable database of client holdings & eligibility.
    - **⏱️ 3_Decision_Replay**: Instant trace reconstruction for auditability.
    - **📈 4_Scenario_Simulator**: Interactive policy & financial ROI what-if simulator.
    - **🛡️ 5_Admin_Overrides**: Master Kill Switch and manual account exclusions.
    """)

st.info("💡 **Getting Started:** Use the sidebar menu to navigate between pages. Active role controls page access per `config/roles.yaml`.")
