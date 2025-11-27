# app.py — Visit Value Agent 4.0 (Pilot)
# Bramhall Consulting, LLC — predict. perform. prosper.

import streamlit as st
import pandas as pd

# ----------------------------
# Page config & simple branding
# ----------------------------
st.set_page_config(page_title="Visit Value Agent 4.0 (Pilot)", page_icon="🩺", layout="centered")
st.markdown("<h1 style='text-align:center;margin-bottom:0'>Visit Value Agent 4.0 — Pilot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;margin-top:0'><em>Bramhall Consulting, LLC — predict. perform. prosper.</em></p>", unsafe_allow_html=True)
st.divider()

# ----------------------------
# Session state
# ----------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}

def next_step():
    st.session_state.step += 1

def reset():
    st.session_state.step = 1
    st.session_state.answers = {}

# ----------------------------
# Helpers
# ----------------------------
def format_money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

def tier(score: float) -> str:
    if score >= 100:
        return "Excellent"
    if 95 <= score <= 99:
        return "Stable"
    if 90 <= score <= 94:
        return "At Risk"
    return "Critical"

def scenario_name(rf_t: str, lf_t: str) -> str:
    rev_map = {"Excellent": "High Revenue", "Stable": "Stable Revenue", "At Risk": "Low Revenue", "Critical": "Critical Revenue"}
    lab_map = {"Excellent": "Efficient Labor", "Stable": "Stable Labor", "At Risk": "At-Risk Labor", "Critical": "Critical Labor"}
    return f"{rev_map[rf_t]} / {lab_map[lf_t]}"

def pos_should_be_top3(rpv_gap: float, avg_copay: float = 30.0, copay_eligibility: float = 0.5, leakage_rate: float = 0.25) -> bool:
    """Rough signal if POS capture alone could close the RPV gap."""
    lift = avg_copay * copay_eligibility * leakage_rate
    return lift >= rpv_gap

# ----------------------------
# Instructions
# ----------------------------
with st.expander("Instructions (summary)", expanded=False):
    st.write(
        "Answer one question at a time. When finished you’ll get: "
        "1) a Calculation Table (incl. SWB%), 2) a VVI/RF/LF scoring table, "
        "3) a scenario classification with prescriptive actions, and "
        "4) a print-ready Executive Summary with a download button."
    )

# ----------------------------
# Input Flow — one question at a time
# ----------------------------
st.markdown("### Start VVI Assessment")

# STEP 1 — Visits
if st.session_state.step == 1:
    visits = st.number_input(
        "How many total patient visits occurred during this time period?",
        min_value=1, step=1, key="visits_input",
    )
    st.button("Next", disabled=visits <= 0, on_click=lambda: (
        st.session_state.answers.update({"visits": int(visits)}), next_step()
    ))

# STEP 2 — Net Revenue
elif st.session_state.step == 2:
    net_rev = st.number_input(
        "What was the total amount of net revenue collected for these visits? ($)",
        min_value=0.01, step=100.0, format="%.2f", key="net_rev_input",
    )
    st.button("Next", disabled=net_rev <= 0, on_click=lambda: (
        st.session_state.answers.update({"net_revenue": float(net_rev)}), next_step()
    ))

# STEP 3 — Labor Cost
elif st.session_state.step == 3:
    labor_cost = st.number_input(
        "What was the total labor cost for this period? ($) (W2 + PRN + overtime + contract/locum)",
        min_value=0.01, step=100.0, format="%.2f", key="labor_cost_input",
    )
    st.button("Next", disabled=labor_cost <= 0, on_click=lambda: (
        st.session_state.answers.update({"labor_cost": float(labor_cost)}), next_step()
    ))

# STEP 4 — Period
elif st.session_state.step == 4:
    period = st.selectbox("What time period does this represent?", ["Week", "Month", "Quarter", "Year"], key="period_input")
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"period": period}), next_step()
    ))

# STEP 5 — Focus (optional)
elif st.session_state.step == 5:
    focus = st.selectbox(
        "Optional: Focus area for this assessment",
        ["All areas", "Revenue improvement", "Staffing efficiency", "Patient flow", "Burnout", "None"],
        key="focus_input",
    )
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"focus": focus}), next_step()
    ))

# STEP 6 — Revenue Target
elif st.session_state.step == 6:
    r_target = st.number_input(
        "Revenue target per visit (default $140)",
        min_value=1.0, value=140.0, step=1.0, format="%.2f", key="rev_target_input",
    )
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"rev_target": float(r_target)}), next_step()
    ))

# STEP 7 — Labor Target + Run
elif st.session_state.step == 7:
    l_target = st.number_input(
        "Labor target per visit (default $85)",
        min_value=1.0, value=85.0, step=1.0, format="%.2f", key="lab_target_input",
    )
    st.button("Run Assessment", on_click=lambda: (
        st.session_state.answers.update({"lab_target": float(l_target)}), next_step()
    ))

# ----------------------------
# Results (only after inputs complete)
# ----------------------------
if st.session_state.step >= 8:
    a = st.session_state.answers
    visits = float(a.get("visits", 0))
    net_rev = float(a.get("net_revenue", 0.0))
    labor = float(a.get("labor_cost", 0.0))
    period = a.get("period", "-")
    focus = a.get("focus", "All areas")
    rt = float(a.get("rev_target", 140.0))
    lt = float(a.get("lab_target", 85.0))

    # Guard against invalid runs
    if visits <= 0 or net_rev <= 0 or labor <= 0:
        st.warning("Please enter non-zero values for visits, net revenue, and labor cost, then run the assessment again.")
        st.stop()

    # Core metrics
    rpv = (net_rev / visits) if visits else 0.0
    lpv = (labor / visits) if visits else 0.0
    swb_pct = (labor / net_rev) if net_rev else 0.0  # context only

    # RF / LF raw and weighted scores (0–100 standardization)
    rf_raw = (rpv / rt) if rt else 0.0
    lf_raw = (lt / lpv) if lpv else 0.0
    rf_score = round(rf_raw * 100, 2)
    lf_score = round(lf_raw * 100, 2)
    rf_t = tier(rf_score)
    lf_t = tier(lf_score)

    # VVI “feel” via RF/LF; scenario naming
    vvi_raw = (rpv / lpv) if lpv else 0.0
    scenario = scenario_name(rf_t, lf_t)

    st.success("Assessment complete. See results below.")

    # ----------------------------
    # Calculation Table (incl. SWB%)
    # ----------------------------
    calc_df = pd.DataFrame(
        {
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
                "VVI Interpretation",
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
                scenario,
            ],
        }
    )
    st.subheader("Calculation Table")
    st.dataframe(calc_df, use_container_width=True, hide_index=True)

    # ----------------------------
    # VVI / RF / LF Scoring Table
    # ----------------------------
    score_df = pd.DataFrame(
        {
            "Index": ["Revenue Factor (RF)", "Labor Factor (LF)", "Visit Value Index (VVI)"],
            "Formula": ["RPV ÷ Revenue Target", "Labor Target ÷ LPV", "RPV ÷ LPV"],
            "Raw Value": [f"{rf_raw:.2f}", f"{lf_raw:.2f}", f"{vvi_raw:.2f}"],
            "Weighted Score (0–100)": [f"{rf_score:.2f}", f"{lf_score:.2f}", "Derived from RF/LF"],
            "Tier": [rf_t, lf_t, lf_t if rf_t == lf_t else "Mixed"],
        }
    )
    st.subheader("VVI / RF / LF Scoring Table")
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    # ----------------------------
    # Scenario + Prescriptive Actions (incl. patches)
    # ----------------------------
    st.subheader("Scenario")
    st.write(f"**{scenario}** — period: **{period}**. Focus: **{focus}**.")

    rpv_gap = max(0.0, rt - rpv)
    top3: list[str] = []
    extended: list[str] = []

    # Revenue levers
    if rf_t in ["At Risk", "Critical", "Stable"] and rpv_gap > 0:
        top3 += [
            "Increase revenue density: prioritize higher-acuity visit types and coding accuracy.",
            "Tighten documentation quality (provider education + quick audits).",
            "Add capacity at peak hours to capture higher-value demand.",
        ]

    # Labor levers
    if lf_t in ["At Risk", "Critical"]:
        top3 += [
            "Align staffing to the demand curve (templates & throughput fixes).",
            "Reduce avoidable OT / premium coverage with scheduling discipline.",
            "Speed chart closure / cycle-time to improve throughput.",
        ]

    if not top3:
        top3 = [
            "Sustain revenue integrity (quarterly audits).",
            "Sustain labor efficiency (periodic productivity checks).",
            "Share best practices across sites; maintain cycle-time discipline.",
        ]

    # POS patch — only Top 3 if it can materially close the RPV gap
    if rf_t in ["At Risk", "Critical", "Stable"]:
        if pos_should_be_top3(rpv_gap):
            top3.append("Run POS co-pay capture push (scripts, training, accountability).")
        else:
            extended.append("Quick POS audit (co-pay scripts, training, ClearPay accountability).")

    # Daily huddle patch — always
    extended.append("Daily 5-minute morning huddle: review Top 3 levers, VPDA drivers, risks.")
    # SWB% patch — context only
    extended.append("Treat SWB% as context only; anchor decisions in VVI (RPV/LPV, RF/LF).")

    st.write("**Top 3 (Immediate):**")
    for i, item in enumerate(top3[:3], start=1):
        st.write(f"{i}. {item}")

    st.write("**Extended Actions:**")
    for item in extended:
        st.write(f"• {item}")

    # ----------------------------
    # Print-Ready Executive Summary (guarded)
    # ----------------------------
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

    # Download
    st.download_button(
        "Download Executive Summary (.txt)",
        data=summary.encode("utf-8"),
        file_name="VVA_Executive_Summary.txt",
    )

    st.divider()
    if st.button("Start a New Assessment"):
        reset()
