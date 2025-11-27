# app.py — Visit Value Agent 4.0 (Pilot)
# Bramhall Consulting, LLC — predict. perform. prosper.

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------
# Page config & branding
# ----------------------------
st.set_page_config(page_title="Visit Value Agent 4.0 (Pilot)", page_icon="🩺", layout="centered")
st.markdown("<h1 style='text-align:center;margin-bottom:0'>Visit Value Agent 4.0 — Pilot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;margin-top:0'><em>Bramhall Consulting, LLC — predict. perform. prosper.</em></p>", unsafe_allow_html=True)
st.divider()
# ==============================
# 16-SCENARIO GRID — HELPERS
# ==============================

TIER_ORDER = ["Critical", "At Risk", "Stable", "Excellent"]  # left-to-right (RF), top-to-bottom (LF)

def tier_from_score(score: float) -> str:
    """Convert 0–100 weighted score to tier using White Paper thresholds."""
    if score >= 100:
        return "Excellent"
    elif 95 <= score <= 99:
        return "Stable"
    elif 90 <= score <= 94:
        return "At Risk"
    else:
        return "Critical"

# Scenario numbering map (row = LF tier, col = RF tier)
# Rows (top→bottom): LF Critical=1..4, LF At Risk=5..8, LF Stable=9..12, LF Excellent=13..16
# Cols (left→right): RF Critical, At Risk, Stable, Excellent
# => This preserves your earlier example: LF Excellent + RF Critical = Scenario 13 (“Low Revenue / Efficient Labor”)
SCENARIO_MAP = {
    ("Critical", "Critical"): 1,   ("Critical", "At Risk"): 2,   ("Critical", "Stable"): 3,   ("Critical", "Excellent"): 4,
    ("At Risk", "Critical"): 5,    ("At Risk", "At Risk"): 6,    ("At Risk", "Stable"): 7,    ("At Risk", "Excellent"): 8,
    ("Stable", "Critical"): 9,     ("Stable", "At Risk"): 10,    ("Stable", "Stable"): 11,    ("Stable", "Excellent"): 12,
    ("Excellent", "Critical"): 13, ("Excellent", "At Risk"): 14, ("Excellent", "Stable"): 15, ("Excellent", "Excellent"): 16,
}

def scenario_label(rf_tier: str, lf_tier: str) -> str:
    """Short diagnosis line based on the quadrant combo."""
    rf_high = rf_tier in ("Excellent", "Stable")
    lf_high = lf_tier in ("Excellent", "Stable")
    if rf_high and lf_high:
        return "Both Revenue & Labor strong — sustain, standardize, and scale best practices."
    if rf_high and not lf_high:
        return "Strong Revenue / Soft Labor — throughput, staffing alignment, overtime controls."
    if not rf_high and lf_high:
        return "Low Revenue / Efficient Labor — revenue density, coding hygiene, visit mix."
    return "Low Revenue / Soft Labor — stabilize access, fix revenue fundamentals, protect labor."

def build_scenario_grid(active_rf_tier: str, active_lf_tier: str):
    """Return a styled 4×4 DataFrame with the active cell highlighted."""
    import pandas as pd

    # Construct a DataFrame of scenario numbers with LF rows and RF columns
    rf_cols = TIER_ORDER  # Critical, At Risk, Stable, Excellent
    lf_rows = TIER_ORDER  # Critical, At Risk, Stable, Excellent (top to bottom)

    data = []
    for lf in lf_rows:
        row = []
        for rf in rf_cols:
            row.append(SCENARIO_MAP[(lf, rf)])
        data.append(row)

    df = pd.DataFrame(data, index=[f"LF: {r}" for r in lf_rows], columns=[f"RF: {c}" for c in rf_cols])

    # highlight function
    def highlight_active(val, row_idx, col_idx):
        lf_here = lf_rows[row_idx]
        rf_here = rf_cols[col_idx]
        if (lf_here == active_lf_tier) and (rf_here == active_rf_tier):
            return "background-color: #fdd835; color: #000; font-weight: 700;"  # gold highlight
        return ""

    # Build a Styler to highlight the active cell
    styler = df.style.format(precision=0)
    for r in range(len(lf_rows)):
        for c in range(len(rf_cols)):
            styler = styler.set_properties(
                subset=(df.index[r], df.columns[c]),
                **{"text-align": "center", "font-weight": "500"}
            )
            styler = styler.apply(
                lambda s, r=r, c=c: [highlight_active(v, r, c) for v in s], axis=1, subset=(df.index[r], df.columns[c])
            )

    # general cosmetics
    styler = (styler
              .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
              .hide(axis="index", level=None)  # comment this line if you want LF labels visible in the left index
             )
    return df, styler

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
    # 0–100 scale interpretation used throughout the White Paper
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
    """Very rough signal: could POS alone close the RPV gap?"""
    lift = avg_copay * copay_eligibility * leakage_rate  # per visit
    return lift >= rpv_gap

# ----------------------------
# Instructions (summary)
# ----------------------------
with st.expander("Instructions (summary)", expanded=False):
    st.write(
        "Answer one question at a time. When finished you’ll get: "
        "1) a Calculation Table (incl. SWB%), 2) a VVI/RF/LF scoring table, "
        "3) a scenario classification with prescriptive actions, "
        "4) a Shiny-style KPI bar chart, and 5) a print-ready Executive Summary."
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
    rpv = (net_rev / visits) if visits else 0.0                 # Revenue per Visit
    lpv = (labor / visits) if visits else 0.0                   # Labor per Visit
    swb_pct = (labor / net_rev) if net_rev else 0.0             # context only

    # White Paper factors:
    # RF_raw = RPV / Target_RPV
    # LF_raw = Target_LPV / LPV
    rf_raw = (rpv / rt) if rt else 0.0
    lf_raw = (lt / lpv) if lpv else 0.0

    # Scores on 0–100 scale
    rf_score = round(rf_raw * 100, 2)
    lf_score = round(lf_raw * 100, 2)
    rf_t = tier(rf_score)
    lf_t = tier(lf_score)

    # VVI: value per dollar of labor
    vvi_raw = (rpv / lpv) if lpv else 0.0  # not scaled

    # VVI normalized to 0–100 for charting:
    # This equals (VVI / VVI_target) * 100 where VVI_target = rt/lt,
    # which simplifies to 100 * RF_raw * LF_raw (strict White Paper alignment).
    vvi_score = round(100 * rf_raw * lf_raw, 2)
    vvi_t = tier(vvi_score)

    scenario = scenario_name(rf_t, lf_t)
    st.success("Assessment complete. See results below.")

    # ----------------------------
    # Shiny-style KPI bars (VVI score, RF, LF) with tier bands
    # ----------------------------
    def render_kpi_bars(vvi_score: float, rf_score: float, lf_score: float):
        labels = ["VVI (normalized 0–100)", "Revenue Factor", "Labor Factor"]
        values = [vvi_score, rf_score, lf_score]

        # dynamic x-axis so >100 doesn't clip
        x_max = max(120, max(values) + 15)

        fig, ax = plt.subplots(figsize=(8.5, 2.8))

        # Tier bands: Critical <90, At-Risk 90–94, Stable 95–99, Excellent ≥100
        bands = [
            (0,   90,  "#d9534f"),  # red
            (90,  95,  "#f0ad4e"),  # orange
            (95,  100, "#ffd666"),  # gold
            (100, x_max, "#5cb85c") # green
        ]
        for start, end, color in bands:
            ax.axvspan(start, end, color=color, alpha=0.15, lw=0)

        # Bars
        bars = ax.barh(labels, values, color="#2e2e2e", height=0.55)

        # Value labels at the end of the bars
        for bar, v in zip(bars, values):
            ax.text(v + (x_max * 0.01), bar.get_y() + bar.get_height()/2,
                    f"{v:.2f}", va="center", ha="left", fontsize=10)

        ax.set_xlim(0, x_max)
        ax.set_xlabel("Score", fontsize=10)
        ax.set_ylabel("")
        ax.grid(False, axis="y")
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["left"].set_visible(False)

        st.subheader("Key Metrics & Scores (Shiny-style)")
        st.pyplot(fig)

    render_kpi_bars(vvi_score, rf_score, lf_score)

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
                "Revenue score (RF)",
                "Labor score (LF)",
                "VVI (value per $ labor)",
                "VVI score (normalized 0–100)",
                "Scenario",
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
                f"{vvi_raw:.3f}",
                f"{vvi_score} ({vvi_t})",
                scenario,
            ],
        }
    )
    st.subheader("Calculation Table")
    st.dataframe(calc_df, use_container_width=True, hide_index=True)

    # ----------------------------
    # VVI / RF / LF Scoring Table (formulas shown)
    # ----------------------------
    score_df = pd.DataFrame(
        {
            "Index": ["Revenue Factor (RF)", "Labor Factor (LF)", "Visit Value Index (VVI)"],
            "Formula": [
                "RPV ÷ Target RPV",
                "Target LPV ÷ LPV",
                "RPV ÷ LPV  (normalized score = 100 × RF_raw × LF_raw)"
            ],
            "Raw Value": [f"{rf_raw:.3f}", f"{lf_raw:.3f}", f"{vvi_raw:.3f}"],
            "Weighted Score (0–100)": [f"{rf_score:.2f}", f"{lf_score:.2f}", f"{vvi_score:.2f}"],
            "Tier": [rf_t, lf_t, vvi_t],
        }
    )
    st.subheader("VVI / RF / LF Scoring Table")
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    # ----------------------------
    # Scenario + Prescriptive Actions (incl. POS & huddle patches)
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
    # Print-Ready Executive Summary
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

    st.download_button(
        "Download Executive Summary (.txt)",
        data=summary.encode("utf-8"),
        file_name="VVA_Executive_Summary.txt",
    )

    st.divider()
    if st.button("Start a New Assessment"):
        reset()
