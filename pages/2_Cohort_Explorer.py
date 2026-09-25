"""
CapitalFit Ops Console — Page 2: Cohort Explorer
Searchable and filterable client accounts database with computed headroom and policy status.
"""

import streamlit as st
import pandas as pd
import json
from core.auth import AuthManager
from core.database import DatabaseStore
from core.audit_logger import AuditLogger

st.set_page_config(page_title="Cohort Explorer | CapitalFit", page_icon="🔍", layout="wide")

# Check RBAC access
if not AuthManager.check_page_access("2_Cohort_Explorer.py"):
    st.error("🚫 Access Denied: Your current role does not have permission to view this page.")
    st.stop()

db_store = DatabaseStore()
audit_logger = AuditLogger(db_store)

st.title("🔍 Cohort Explorer & Headroom Inspector")
st.caption("Inspect client MTF holdings, computed headroom, risk flags, and decision outcomes.")

st.divider()

# Filter Controls
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    search_query = st.text_input("Search Account ID / Name:", placeholder="e.g. ANGEL_100005")

with col_f2:
    filter_ab = st.selectbox("A/B Group:", ["ALL", "TREATMENT", "CONTROL"])

with col_f3:
    filter_status = st.selectbox("Policy Outcome:", ["ALL", "NUDGE", "SUPPRESS_CONTROL", "SUPPRESS_POLICY"])

with col_f4:
    min_headroom_filter = st.number_input("Min Headroom (₹):", value=0, step=10000)

# Fetch Data from Database
conn = db_store.get_connection()
cursor = conn.cursor()

query = """
    SELECT a.account_id, a.client_name, a.current_funded, a.eligible_limit, a.headroom,
           a.treatment_group, a.margin_call_active, a.in_collections, a.risk_review_hold, a.opted_out,
           d.decision_id, d.policy_outcome, d.llm_output_text
    FROM accounts a
    LEFT JOIN decision_audit d ON a.account_id = d.account_id
"""
params = []
conditions = []

if search_query:
    conditions.append("(a.account_id LIKE ? OR a.client_name LIKE ?)")
    params.extend([f"%{search_query}%", f"%{search_query}%"])

if filter_ab != "ALL":
    conditions.append("a.treatment_group = ?")
    params.append(filter_ab)

if filter_status != "ALL":
    conditions.append("d.policy_outcome = ?")
    params.append(filter_status)

if min_headroom_filter > 0:
    conditions.append("a.headroom >= ?")
    params.append(min_headroom_filter)

if conditions:
    query += " WHERE " + " AND ".join(conditions)

query += " ORDER BY a.headroom DESC LIMIT 200"

cursor.execute(query, params)
rows = cursor.fetchall()
conn.close()

# Convert to DataFrame
df = pd.DataFrame([dict(r) for r in rows])

if df.empty:
    st.info("No accounts matching the selected filter criteria.")
else:
    st.markdown(f"Displaying **{len(df)}** accounts (capped at 200 matches):")
    
    # Format DataFrame for display
    display_df = df.copy()
    display_df["current_funded"] = display_df["current_funded"].apply(lambda x: f"₹{x:,.0f}")
    display_df["eligible_limit"] = display_df["eligible_limit"].apply(lambda x: f"₹{x:,.0f}")
    display_df["headroom"] = display_df["headroom"].apply(lambda x: f"₹{x:,.0f}")

    st.dataframe(
        display_df[[
            "account_id", "client_name", "eligible_limit", "current_funded",
            "headroom", "treatment_group", "policy_outcome", "decision_id"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Detail Account Inspector
    st.subheader("📋 Account Detail & Holdings Inspector")
    selected_account_id = st.selectbox("Select Account ID to Inspect:", df["account_id"].tolist())

    if selected_account_id:
        conn = db_store.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (selected_account_id,))
        acc_rec = dict(cursor.fetchone())

        cursor.execute("SELECT symbol, tier, quantity, market_value FROM holdings WHERE account_id = ?", (selected_account_id,))
        holdings_rows = [dict(h) for h in cursor.fetchall()]

        cursor.execute("SELECT * FROM decision_audit WHERE account_id = ?", (selected_account_id,))
        audit_rec = cursor.fetchone()
        audit_dict = dict(audit_rec) if audit_rec else {}

        conn.close()

        col_d1, col_d2 = st.columns([1, 1])

        with col_d1:
            st.markdown(f"#### Account Info: `{acc_rec['account_id']}`")
            st.write(f"**Client Name:** {acc_rec['client_name']}")
            st.write(f"**KYC Status:** {acc_rec['kyc_status']}")
            st.write(f"**Eligible Collateral Limit:** ₹{acc_rec['eligible_limit']:,.2f}")
            st.write(f"**Current Funded Loan:** ₹{acc_rec['current_funded']:,.2f}")
            st.write(f"**Available Headroom:** ₹{acc_rec['headroom']:,.2f}")
            st.write(f"**A/B Group:** `{acc_rec['treatment_group']}`")

            st.markdown("**Risk Flags Status:**")
            st.write(f"- Margin Call Active: {'🚨 YES' if acc_rec['margin_call_active'] else '✅ NO'}")
            st.write(f"- In Collections: {'🚨 YES' if acc_rec['in_collections'] else '✅ NO'}")
            st.write(f"- Risk Review Hold: {'⚠️ YES' if acc_rec['risk_review_hold'] else '✅ NO'}")
            st.write(f"- Client Opted Out: {'🚫 YES' if acc_rec['opted_out'] else '✅ NO'}")

        with col_d2:
            st.markdown("#### Pledged Portfolio Holdings")
            hdf = pd.DataFrame(holdings_rows)
            if not hdf.empty:
                hdf["market_value"] = hdf["market_value"].apply(lambda x: f"₹{x:,.2f}")
                st.dataframe(hdf, use_container_width=True, hide_index=True)

            st.markdown("#### Nudge Card Outcome")
            if audit_dict:
                st.write(f"**Decision ID:** `{audit_dict.get('decision_id')}`")
                st.write(f"**Action:** `{audit_dict.get('policy_outcome')}`")
                if audit_dict.get("llm_output_text"):
                    st.info(f"💬 **Nudge Text Shown:** \"{audit_dict.get('llm_output_text')}\"")
            else:
                st.write("No decision audit record found.")
