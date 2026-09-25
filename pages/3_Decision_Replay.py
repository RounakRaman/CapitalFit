"""
CapitalFit Ops Console — Page 3: Decision Replay
Full decision audit trace reconstruction for any account in <2s (FR-08 / F8.2).
"""

import streamlit as st
import json
import time
from core.auth import AuthManager
from core.database import DatabaseStore
from core.audit_logger import AuditLogger

st.set_page_config(page_title="Decision Replay | CapitalFit", page_icon="⏱️", layout="wide")

# Check RBAC access
if not AuthManager.check_page_access("3_Decision_Replay.py"):
    st.error("🚫 Access Denied: Your current role does not have permission to view this page.")
    st.stop()

db_store = DatabaseStore()
audit_logger = AuditLogger(db_store)

st.title("⏱️ Full Decision Replay & Audit Trace")
st.caption("Reconstruct exact input data, policy execution steps, LLM prompt, guardrail checks, and consent records (FR-08).")

st.divider()

# Search / Select Decision
recent_decisions = audit_logger.search_recent_decisions(limit=100)

if not recent_decisions:
    st.info("No decision records found. Seed data first on the main page.")
    st.stop()

decision_options = {
    f"{d['decision_id']} | Acc: {d['account_id']} | Action: {d['policy_outcome']} ({d['timestamp'][:19]})": d["decision_id"]
    for d in recent_decisions
}

selected_label = st.selectbox("Select Decision Record to Replay:", list(decision_options.keys()))
selected_decision_id = decision_options[selected_label]

start_time = time.time()
trace = audit_logger.get_decision_trace(selected_decision_id)
elapsed_ms = (time.time() - start_time) * 1000.0

if not trace:
    st.error("Decision trace not found.")
    st.stop()

st.success(f"⚡ Decision trace reconstructed in **{elapsed_ms:.1f} ms** (Acceptance Criteria: <2,000 ms).")

st.divider()

# Replay Execution Steps
st.subheader(f"📌 Decision Trace ID: `{trace['decision_id']}`")

step1, step2, step3, step4 = st.tabs([
    "1️⃣ Data Ingestion Snapshot",
    "2️⃣ Policy Rule Evaluation",
    "3️⃣ LLM Phrasing & Prompt",
    "4️⃣ Guardrail & Final Delivery"
])

with step1:
    st.markdown("### Step 1: Input Data & Signal Layer (F1.1-F1.4)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write(f"**Account ID:** `{trace['account_id']}`")
        st.write(f"**Timestamp:** `{trace['timestamp']}`")
    with c2:
        st.write(f"**Eligible Limit:** ₹{trace['eligible_limit']:,.2f}")
        st.write(f"**Current Funded Amount:** ₹{(trace['eligible_limit'] - trace['headroom']):,.2f}")
    with c3:
        st.write(f"**Calculated Headroom:** ₹{trace['headroom']:,.2f}")
        st.write(f"**Proposed Top-Up:** ₹{trace['proposed_nudge_amount']:,.2f}")

    st.json(trace["inputs_snapshot"])

with step2:
    st.markdown("### Step 2: Deterministic Policy & A/B Engine (F2.1-F2.3)")
    st.write(f"**Policy Version:** `{trace['policy_version']}`")
    st.write(f"**Evaluated Action:** `{trace['policy_outcome']}`")
    st.write(f"**Salted A/B Group:** `{trace['ab_group']}`")

    if trace["rejection_reasons"]:
        st.warning(f"**Rejection / Exclusion Flags:** {', '.join(trace['rejection_reasons'])}")
    else:
        st.success("✅ **Passed All Risk & Cooldown Rules**")

with step3:
    st.markdown("### Step 3: LLM Explanation Layer (F4.1)")
    st.write(f"**Delivery Mode:** `{trace['delivery_mode']}`")
    st.markdown("**Generated Nudge Card Text:**")
    if trace["llm_output_text"]:
        st.info(f"💬 \"{trace['llm_output_text']}\"")
    else:
        st.write("No text generated (nudge suppressed by policy/control group).")

with step4:
    st.markdown("### Step 4: Guardrail Checker & Audit Verification (F4.2 / FR-05)")
    st.write(f"**Guardrail Compliance Status:** {'✅ PASSED (100% Verified)' if trace['guardrail_passed'] else '⚠️ FALLBACK TRIGGERED'}")
    
    st.markdown("""
    - **Amount Matching Check:** Stated amount strictly equals input headroom.
    - **APR Check:** Stated interest rate equals policy APR (12.0%).
    - **Prohibited Coercive Words Check:** Zero high-pressure terms found.
    - **Regulatory Disclaimer Check:** RBI DLG / Angel One T&C disclaimer present.
    """)

    # Check for any consent event tied to this decision
    conn = db_store.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM consent_events WHERE decision_id = ?", (trace["decision_id"],))
    consent_rec = cursor.fetchone()
    conn.close()

    st.divider()
    st.markdown("### 📜 Timestamped Client Consent Record (F5.2)")
    if consent_rec:
        cd = dict(consent_rec)
        st.success(f"**Consent ID:** `{cd['consent_id']}` | **Action:** `{cd['client_action']}` | **Timestamp:** `{cd['consent_timestamp']}`")
        if cd["transaction_id"]:
            st.write(f"**Transaction ID:** `{cd['transaction_id']}` | **Funded Amount:** ₹{cd['funded_amount']:,.2f}")
    else:
        st.write("No client response recorded yet for this decision trace.")
