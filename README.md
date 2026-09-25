# ⚡ CapitalFit — The Collateral Headroom Agent Console

### Angel One New Business Unit (NBU) — Stage 1 (LAS/MTF)

CapitalFit is an AI agent architecture and Streamlit governance console that identifies existing Angel One clients using less of their eligible Margin Trade Funding (MTF) / Loan Against Securities (LAS) limit than their portfolio already supports, explains the pre-approved opportunity in plain language, and routes them to a one-tap native top-up flow.

---

## 🚀 Key Features

1. **Deterministic Policy Core (`core/policy_rules.py`)**:
   - Computes eligible limits per security haircut (Tier 1 15%, Tier 2 30%, Tier 3 50%).
   - Headroom detector: triggers when `headroom >= 15%` AND `headroom >= ₹25,000`.
   - Encodes risk exclusions (margin calls, collections, opt-outs), 14-day rolling cooldowns, and salted A/B group assignment (`TREATMENT` vs `CONTROL`).

2. **LLM Phrasing & Guardrail Layer (`core/llm_explanation.py`)**:
   - Uses LLM strictly as a phrasing layer for deterministic decision payloads.
   - Deterministic rule-based Guardrail Checker verifying amount match, APR match, absence of high-pressure language, and required RBI DLG compliance text.
   - Automatic static template fallback on guardrail failure.

3. **Streamlit Governance Console (`app.py`, `pages/`)**:
   - **📊 1_Dashboard**: Live funnel metrics, Plotly treatment/control lift chart with 95% CI, revenue tracker vs `NBU_Monetization.xlsx` target.
   - **🔍 2_Cohort_Explorer**: Filterable account database and pledged stock holdings breakdown.
   - **⏱️ 3_Decision_Replay**: Instant trace reconstruction (<2s response time) for 100% regulatory auditability.
   - **📈 4_Scenario_Simulator**: Interactive policy & financial ROI what-if simulator matching Excel formulas.
   - **🛡️ 5_Admin_Overrides**: Master Kill Switch and account override manager for Risk & Credit Ops.

---

## 💻 Local Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Streamlit Console
```bash
streamlit run app.py
```

### 3. Run Automated Tests
```bash
pytest tests/
```

---

## 🐳 Docker Deployment

```bash
docker build -t capitalfit-console .
docker run -p 8501:8501 capitalfit-console
```

Or using Docker Compose:
```bash
docker-compose up -d
```

---

## 📦 Zip Packaging for GitHub Upload

Run the package script to create `capitalfit_release.zip`:
```bash
python create_zip.py
```
