
import streamlit as st
import math
import pandas as pd

st.set_page_config(page_title="Visit Value Agent 4.0 (Pilot)", page_icon="🩺", layout="centered")

# --- Branding ---
st.markdown("<h1 style='text-align:center;margin-bottom:0'>Visit Value Agent 4.0 — Pilot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;margin-top:0'><em>Bramhall Consulting, LLC — predict. perform. prosper.</em></p>", unsafe_allow_html=True)
st.divider()

# Session state for stepper
if "step" not in st.session_state:
    st.session_state.step = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}

def next_step():
    st.session_state.step += 1

def reset():
    st.session_state.step = 1
    st.session_state.answers = {}

# --- Input Flow (one question at a time) ---
with st.expander("Instructions (summary)", expanded=False):
    st.write("Answer one question at a time. After inputs, you'll get two tables (Calculations and VVI/RF/LF scoring), a scenario classification, prescriptive actions, and a print‑ready executive summary.")

st.markdown("### Start VVI Assessment")

if st.session_state.step == 1:
    visits = st.number_input("How many total patient visits occurred during this time period?", min_value=1, step=1)
    if st.button("Next"):
        st.session_state.answers["visits"] = visits
        next_step()

elif st.session_state.step == 2:
    net_rev = st.number_input("What was the total amount of **net revenue collected** for these visits? ($)", min_value=0.0, step=100.0, format="%.2f")
    if st.button("Next"):
        st.session_state.answers["net_revenue"] = net_rev
        next_step()

elif st.session_state.step == 3:
    labor_cost = st.number_input("What was the **total labor cost** for this period? ($) (W2 + PRN + overtime + contract/locum)", min_value=0.0, step=100.0, format="%.2f")
    if st.button("Next"):
        st.session_state.answers["labor_cost"] = labor_cost
        next_step()

elif st.session_state.step == 4:
    period = st.selectbox("What time period does this represent?", ["Week", "Month", "Quarter", "Year"])
    if st.button("Next"):
        st.session_state.answers["period"] = period
        next_step()

elif st.session_state.step == 5:
    focus = st.selectbox("Optional: Focus area for this assessment", ["All areas", "Revenue improvement", "Staffing efficiency", "Patient flow", "Burnout", "None"])
    if st.button("Next"):
        st.session_state.answers["focus"] = focus
        next_step()

elif st.session_state.step == 6:
    r_target = st.number_input("Revenue target per visit (default $140)", min_value=1.0, value=140.0, step=1.0, format="%.2f")
    if st.button("Next"):
        st.session_state.answers["rev_target"] = r_target
        next_step()

elif st.session_state.step == 7:
    l_target = st.number_input("Labor target per visit (default $85)", min_value=1.0, value=85.0, step=1.0, format="%.2f")
    if st.button("Run Assessment"):
        st.session_state.answers["lab_target"] = l_target
        next_step()

# --- Helpers ---
def tier(score):
    if score >= 100:
        return "Excellent"
    if 95 <= score <= 99:
        return "Stable"
    if 90 <= score <= 94:
        return "At Risk"
    return "Critical"

def scenario_name(rf_tier, lf_tier):
    # 4x4 grid descriptions
    rev_map = {
        "Excellent": "High Revenue",
        "Stable": "Stable Revenue",
        "At Risk": "Low Revenue",
        "Critical": "Critical Revenue"
    }
    lab_map = {
        "Excellent": "Efficient Labor",
        "Stable": "Stable Labor",
        "At Risk": "At‑Risk Labor",
        "Critical": "Critical Labor"
    }
    return f"{rev_map[rf_tier]} / {lab_map[lf_tier]}"

def pos_should_be_top3(rpv_gap, visits, avg_copay=30.0, copay_eligibility=0.5, leakage_rate=0.25):
    # Very rough signal whether POS alone could close the gap
    lift = avg_copay * copay_eligibility * leakage_rate  # per visit
    return lift >= rpv_gap

def format_money(x):
    return f"${x:,.2f}"

# --- Results ---
if st.session_state.step >= 8:
    a = st.session_state.answers
    visits = float(a["visits"])
    net_rev = float(a["net_revenue"])
    labor = float(a["labor_cost"])
    period = a["period"]
    focus = a["focus"]
    rt = float(a["rev_target"])
    lt = float(a["lab_target"])

    # Core metrics
    rpv = net_rev / visits if visits else 0.0
    lpv = labor / visits if visits else 0.0
    swb_pct = (labor / net_rev) if net_rev else 0.0

    # Factors and scores (0-100 scale by ratio*100)
    rf_raw = (rpv / rt) if rt else 0.0
    lf_raw = (lt / lpv) if lpv else 0.0
    rf_score = round(rf_raw * 100, 2)
    lf_score = round(lf_raw * 100, 2)

    rf_t = tier(rf_score)
    lf_t = tier(lf_score)
    vvi_raw = (rpv / lpv) if lpv else 0.0
    scenario = scenario_name(rf_t, lf_t)

    st.success("Assessment complete. See results below.")

    # Calculation Table
    calc_df = pd.DataFrame({
        "Metric": [
            "Total visits",
            "Net revenue collected",
            "Total labor cost",
            "Revenue per visit (RPV)",
            "Labor cost per visit (LPV)",
            "Revenue benchmark target",
            "Labor benchmark target",
            "Labor cost as % of revenue (SWB%)",
            "Revenue score",
            "Labor score",
            "VVI Interpretation"
        ],
        "Value": [
            f"{int(visits):,}",
            format_money(net_rev),
            format_money(labor),
            format_money(rpv),
            format_money(lpv),
            format_money(rt),
            format_money(lt),
            f"{swb_pct*100:.1f}%",
            f"{rf_score} ({rf_t})",
            f"{lf_score} ({lf_t})",
            scenario
        ]
    })
    st.subheader("Calculation Table")
    st.dataframe(calc_df, use_container_width=True, hide_index=True)

    # VVI / RF / LF Scoring Table
    score_df = pd.DataFrame({
        "Index": ["Revenue Factor (RF)", "Labor Factor (LF)", "Visit Value Index (VVI)"],
        "Formula": ["RPV ÷ Revenue Target", "Labor Target ÷ LPV", "RPV ÷ LPV"],
        "Raw Value": [f"{rf_raw:.2f}", f"{lf_raw:.2f}", f"{vvi_raw:.2f}"],
        "Weighted Score (0–100)": [f"{rf_score:.2f}", f"{lf_score:.2f}", "Derived from RF/LF"],
        "Tier": [rf_t, lf_t, lf_t if rf_t==lf_t else "Mixed"]
    })
    st.subheader("VVI / RF / LF Scoring Table")
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    st.subheader("Scenario")
    st.write(f"**{scenario}** — period: **{period}**. Focus: **{focus}**.")

    # Prescriptive Actions
    st.subheader("Prescriptive Actions")
    rpv_gap = max(0.0, rt - rpv)
    top3 = []
    extended = []

    # Revenue-oriented actions
    if rf_t in ["At Risk", "Critical", "Stable"] and rpv_gap > 0:
        top3 += [
            "Increase revenue density: prioritize higher-acuity visit types and coding accuracy.",
            "Tighten documentation quality (provider education + quick audits).",
            "Add capacity at peak hours to capture higher-value demand."
        ]

    # Labor-oriented actions
    if lf_t in ["At Risk", "Critical"]:
        top3 += [
            "Align staffing to demand curve (template & throughput fixes).",
            "Reduce avoidable OT / premium coverage with better scheduling discipline.",
            "Speed chart closure / cycle-time to improve throughput without overscheduling."
        ]

    # If neither bucket placed items, provide sustaining actions
    if not top3:
        top3 = [
            "Sustain current revenue integrity (quarterly audits).",
            "Sustain labor efficiency with periodic productivity checks.",
            "Share best practices across clinics; maintain cycle-time discipline."
        ]

    # POS patch logic (extended unless data shows massive copay leakage potential)
    if rf_t in ["At Risk", "Critical", "Stable"]:
        if pos_should_be_top3(rpv_gap, visits):
            top3.append("Run POS co‑pay capture push (scripts, training, accountability).")
        else:
            extended.append("Quick POS audit (co‑pay scripts, accountability, ClearPay).")

    # Daily 5-minute huddle (always extended unless comms is root cause)
    extended.append("Daily 5‑minute morning huddle: review Top 3 levers, VPDA drivers, risks.")

    # Always include SWB% context note per patch
    extended.append("Treat SWB% as context only; anchor decisions in VVI (RPV/LPV, RF/LF).")

    st.write("**Top 3 (Immediate):**")
    for i, item in enumerate(top3[:3], 1):
        st.write(f"{i}. {item}")
    st.write("**Extended Actions:**")
    for item in extended:
        st.write(f"• {item}")

# Print-ready executive summary
st.subheader("Print-Ready Executive Summary")

summary = f"""Visit Value Agent 4.0 — Executive Summary

Period: {period}
Focus: {focus}

VVI Scenario: {scenario}
Revenue Factor (RF): {rf_score:.2f} ({rf_t})
Labor Factor (LF): {lf_score:.2f} ({lf_t})
RPV: {format_money(rpv)}  |  LPV: {format_money(lpv)}  |  SWB%: {swb_pct*100:.1f}%

Top 3 Actions:
1) {top3[0] if len(top3)>0 else '-'}
2) {top3[1] if len(top3)>1 else '-'}
3) {top3[2] if len(top3)>2 else '-'}

Extended Actions:
- {extended[0] if len(extended)>0 else '-'}
- {extended[1] if len(extended)>1 else '-'}
- {extended[2] if len(extended)>2 else '-'}

Legal: This operational analysis is for informational purposes only and does not constitute medical, clinical, legal, or compliance advice. VVA provides operational insights only.
"""

st.code(summary)

# Download button
st.download_button(
    "Download Executive Summary (.txt)",
    data=summary.encode("utf-8"),
    file_name="VVA_Executive_Summary.txt"
)

st.divider()

if st.button("Start a New Assessment"):
    reset()
