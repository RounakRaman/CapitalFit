"""
CapitalFit Ops Console — Page 4: Scenario Simulator
Interactive financial & policy what-if simulator reproducing NBU_Monetization.xlsx formulas (FR-11).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.auth import AuthManager
from core.sizing_model import FinancialSizingModel

st.set_page_config(page_title="Scenario Simulator | CapitalFit", page_icon="📈", layout="wide")

# Check RBAC access
if not AuthManager.check_page_access("4_Scenario_Simulator.py"):
    st.error("🚫 Access Denied: Your current role does not have permission to view this page.")
    st.stop()

st.title("📈 Policy & Financial Scenario Simulator")
st.caption("Simulate policy threshold changes, conversion rates, and cost parameters using NBU_Monetization.xlsx formulas (FR-11).")

st.divider()

# Sidebar / Top Parameters Control
st.subheader("⚙️ Simulation Model Parameters")

col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    total_eligible = st.number_input("Eligible Account Cohort:", value=550_000, step=10_000)
    rollout_pct = st.slider("Rollout Coverage %:", min_value=10.0, max_value=100.0, value=70.0, step=5.0)
    avg_headroom = st.number_input("Avg Headroom per Account (₹):", value=61_727, step=1_000)

with col_p2:
    conversion_pct = st.slider("Funded Conversion Rate %:", min_value=0.10, max_value=3.00, value=0.86, step=0.05)
    gross_apr = st.slider("Gross Interest APR %:", min_value=8.0, max_value=16.0, value=12.0, step=0.25)
    cost_of_funds = st.slider("Cost of Funds %:", min_value=5.0, max_value=10.0, value=7.25, step=0.25)

with col_p3:
    ecl_pct = st.slider("Expected Credit Loss (ECL) %:", min_value=0.10, max_value=2.00, value=0.50, step=0.10)
    build_cost_cr = st.number_input("Year-1 Build & Run Cost (₹ Cr):", value=1.20, step=0.10)

# Instantiate Financial Model
model = FinancialSizingModel(
    total_eligible_accounts=int(total_eligible),
    rollout_coverage_pct=rollout_pct,
    avg_headroom_per_account=float(avg_headroom),
    gross_interest_apr_pct=gross_apr,
    cost_of_funds_pct=cost_of_funds,
    ecl_pct=ecl_pct,
    year1_build_run_cost_cr=build_cost_cr,
)

metrics = model.calculate_metrics(conversion_pct)
scenarios = model.run_scenario_analysis()

st.divider()

# Simulation Output Metrics Cards
st.subheader("📊 Projected Financial Outcomes (Year 1)")

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("Incremental LAS Book", f"₹{metrics['incremental_book_cr']} Cr")
with m2:
    st.metric("Gross Interest", f"₹{metrics['gross_interest_cr']} Cr")
with m3:
    st.metric("Variable Costs (Funding+ECL)", f"₹{metrics['total_variable_cost_cr']} Cr")
with m4:
    st.metric("Net Contribution", f"₹{metrics['net_contribution_cr']} Cr", delta=f"{'Target Cleared' if metrics['net_contribution_cr'] >= 4.4 else 'Below Base Target'}")
with m5:
    roi_label = f"{metrics['contribution_roi']}x"
    st.metric("Contribution ROI", roi_label, delta=f"{'Gate Cleared (≥3.0x)' if metrics['clears_3x_roi_gate'] else 'Below Gate'}")

st.divider()

# Scenario Benchmark Comparison Table
st.subheader("📋 Scenario Comparison Table (vs NBU_Monetization.xlsx)")

sc_df = pd.DataFrame([
    {
        "Scenario Name": sc["name"],
        "Conversion %": f"{sc['conversion_rate_pct']}%",
        "Incremental Book (₹ Cr)": f"₹{sc['incremental_book_cr']}",
        "Gross Interest (₹ Cr)": f"₹{sc['gross_interest_cr']}",
        "Variable Costs (₹ Cr)": f"₹{sc['total_variable_cost_cr']}",
        "Net Contribution (₹ Cr)": f"₹{sc['net_contribution_cr']}",
        "Contribution ROI": f"{sc['contribution_roi']}x",
        "Clears 3.0x Gate?": "✅ YES" if sc["clears_3x_roi_gate"] else "❌ NO",
    }
    for sc in scenarios.values()
] + [
    {
        "Scenario Name": f"⚡ CUSTOM SIMULATION ({conversion_pct}%)",
        "Conversion %": f"{metrics['conversion_rate_pct']}%",
        "Incremental Book (₹ Cr)": f"₹{metrics['incremental_book_cr']}",
        "Gross Interest (₹ Cr)": f"₹{metrics['gross_interest_cr']}",
        "Variable Costs (₹ Cr)": f"₹{metrics['total_variable_cost_cr']}",
        "Net Contribution (₹ Cr)": f"₹{metrics['net_contribution_cr']}",
        "Contribution ROI": f"{metrics['contribution_roi']}x",
        "Clears 3.0x Gate?": "✅ YES" if metrics["clears_3x_roi_gate"] else "❌ NO",
    }
])

st.dataframe(sc_df, use_container_width=True, hide_index=True)

st.divider()

# Sensitivity Plot: Conversion Rate vs ROI & Net Contribution
st.subheader("📉 Conversion Rate Sensitivity & Scale Gate Plot")

curve_data = model.generate_sensitivity_curve(start_conv=0.2, end_conv=2.0, steps=25)
curve_df = pd.DataFrame(curve_data)

fig_sens = go.Figure()
# Net Contribution curve
fig_sens.add_trace(
    go.Scatter(x=curve_df["conversion_rate_pct"], y=curve_df["net_contribution_cr"], mode="lines+markers", name="Net Contribution (₹ Cr)", line=dict(color="#0F62FE", width=3))
)
# ROI curve
fig_sens.add_trace(
    go.Scatter(x=curve_df["conversion_rate_pct"], y=curve_df["contribution_roi"], mode="lines", name="Contribution ROI (x)", yaxis="y2", line=dict(color="#10B981", width=3, dash="dash"))
)

# 3.0x ROI Gate Line
fig_sens.add_hline(y=3.0, yref="y2", line_width=2, line_dash="dot", line_color="red", annotation_text="3.0x ROI Scale Gate (0.86% Conv)", annotation_position="top left")

fig_sens.update_layout(
    xaxis_title="Funded Conversion Rate (%)",
    yaxis=dict(title="Net Contribution (₹ Crores)"),
    yaxis2=dict(title="Contribution ROI (x)", overlaying="y", side="right"),
    margin=dict(l=20, r=20, t=30, b=20),
    height=400,
    legend=dict(orient="h", y=1.1),
)

st.plotly_chart(fig_sens, use_container_width=True)
