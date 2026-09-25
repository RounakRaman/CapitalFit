"""
CapitalFit Ops Console — Page 5: Admin Overrides & Master Kill Switch
Allows Risk/Credit Ops to pause the agent globally or override specific accounts (FR-09 / F8.5).
"""

import streamlit as st
import pandas as pd
import json
from core.auth import AuthManager
from core.system_state import SystemStateManager
from core.database import DatabaseStore

st.set_page_config(page_title="Admin Overrides | CapitalFit", page_icon="🛡️", layout="wide")

# Check RBAC access (Risk role required)
if not AuthManager.check_page_access("5_Admin_Overrides.py"):
    st.error("🚫 Access Denied: Admin Overrides & Kill Switch are restricted strictly to Risk & Credit Ops roles.")
    st.info("Switch your active role to 'Risk' in the sidebar to test this page.")
    st.stop()

user = AuthManager.get_current_user()
sys_state = SystemStateManager.get_state()
is_paused = sys_state.get("agent_paused", False)

st.title("🛡️ Risk Overrides & Master Kill Switch")
st.caption("Angel Fincap Risk Operations Control Panel (FR-09 / F8.5 / Section 14).")

st.divider()

# Section 1: Emergency Master Kill Switch (FR-09 / F8.5)
st.subheader("🚨 Emergency Master Kill Switch")
st.markdown(
    "Pausing the agent stops **all new nudge generation** immediately across the platform. "
    "In-flight consented loans continue processing under standard MTF rules."
)

col_ks1, col_ks2 = st.columns([1.5, 1])

with col_ks1:
    if is_paused:
        st.error(f"🚨 **STATUS: AGENT PAUSED**")
        st.write(f"**Paused By:** `{sys_state.get('paused_by')}`")
        st.write(f"**Paused At:** `{sys_state.get('paused_at')}`")
        st.write(f"**Reason:** \"{sys_state.get('pause_reason')}\"")

        if st.button("🟢 RESUME CAPITALFIT AGENT", type="primary", use_container_width=True):
            SystemStateManager.set_kill_switch(paused=False, user_email=user["email"])
            st.success("Agent resumed successfully!")
            st.rerun()
    else:
        st.success("🟢 **STATUS: AGENT ACTIVE & NUDGING**")
        pause_reason_input = st.text_input("Enter reason for emergency pause:", placeholder="e.g. Market volatility spike / Policy review")

        if st.button("🚨 PAUSE CAPITALFIT AGENT (KILL SWITCH)", type="primary", use_container_width=True):
            if not pause_reason_input:
                st.warning("Please enter a pause reason before activating the kill switch.")
            else:
                SystemStateManager.set_kill_switch(paused=True, user_email=user["email"], reason=pause_reason_input)
                st.error("Agent paused immediately!")
                st.rerun()

st.divider()

# Section 2: Account-Level Manual Exclusions & Overrides (F8.5)
st.subheader("👤 Account-Level Manual Override Manager")

col_ex1, col_ex2 = st.columns([1, 1])

with col_ex1:
    st.markdown("#### Exclude / Include Specific Account")
    target_account_id = st.text_input("Enter Account ID:", placeholder="e.g. ANGEL_100015")
    action_type = st.radio("Action:", ["Exclude from Nudging", "Remove Exclusion"])

    if st.button("Apply Account Override", use_container_width=True):
        if target_account_id:
            exclude_flag = (action_type == "Exclude from Nudging")
            SystemStateManager.add_account_override(target_account_id, exclude=exclude_flag)
            st.success(f"Updated override for `{target_account_id}` ({action_type}).")
            st.rerun()
        else:
            st.warning("Please enter an Account ID.")

with col_ex2:
    st.markdown("#### Currently Manually Excluded Accounts")
    curr_state = SystemStateManager.get_state()
    excluded_list = curr_state.get("manual_excluded_accounts", [])

    if excluded_list:
        st.write(pd.DataFrame({"Excluded Account ID": excluded_list}))
    else:
        st.info("No accounts manually excluded.")

st.divider()

# Section 3: Compliance Audit Log Export (F7.4 / FR-08)
st.subheader("📥 Regulatory Audit Trail Export")
st.markdown("Download raw, immutable decision and consent logs for compliance review.")

db_store = DatabaseStore()
conn = db_store.get_connection()
audit_df = pd.read_sql_query("SELECT * FROM decision_audit", conn)
consent_df = pd.read_sql_query("SELECT * FROM consent_events", conn)
conn.close()

c_exp1, c_exp2 = st.columns(2)
with c_exp1:
    st.download_button(
        "📥 Download Decision Audit CSV",
        data=audit_df.to_csv(index=False),
        file_name="capitalfit_decision_audit.csv",
        mime="text/csv",
        use_container_width=True,
    )
with c_exp2:
    st.download_button(
        "📥 Download Consent Events CSV",
        data=consent_df.to_csv(index=False),
        file_name="capitalfit_consent_events.csv",
        mime="text/csv",
        use_container_width=True,
    )
