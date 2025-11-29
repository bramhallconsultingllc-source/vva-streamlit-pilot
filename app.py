import os

# app.py — Visit Value Agent 4.0 (Pilot)
# Bramhall Consulting, LLC — predict. perform. prosper.

import io
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# --- AI (optional) ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # app still runs if OpenAI SDK isn't installed


# ----------------------------
# Page config & branded intro
# ----------------------------
st.set_page_config(
    page_title="Visit Value Agent 4.0 (Pilot)",
    page_icon="🩺",
    layout="centered"
)

LOGO_PATH = "Logo BC.png"  # update if your filename is different

st.markdown(intro_css, unsafe_allow_html=True)
st.markdown("<div class='intro-container'>", unsafe_allow_html=True)

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, use_column_width=False, output_format="PNG")
else:
    st.caption(f"(Logo file '{LOGO_PATH}' not found — update LOGO_PATH or add the image to the app root.)")

intro_html = """
<div class='intro-text'>
    <h2>Welcome to the Visit Value Index&trade; (VVI)</h2>
    <p>Where 5 simple inputs create:</p>
    <ul class='intro-bullets'>
        <li>A single standardized efficiency score</li>
        <li>Clear revenue and labor sub-factors</li>
        <li>A diagnosis and 16-scenario prescriptive matrix</li>
        <li>A 12-week turnaround strategy</li>
    </ul>
    <p style="margin-top:1rem;font-style:italic;color:#555;">
        Bramhall Consulting, LLC &mdash; predict. perform. prosper.
    </p>
</div>
"""
st.markdown(intro_html, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==============================
# Core helpers & configuration
# ==============================

TIER_ORDER = ["Critical", "At Risk", "Stable", "Excellent"]  # RF left→right, LF top→bottom


def tier_from_score(score: float) -> str:
    if score >= 100:
        return "Excellent"
    if 95 <= score <= 99:
        return "Stable"
    if 90 <= score <= 94:
        return "At Risk"
    return "Critical"


tier = tier_from_score  # alias, kept for backward compatibility

# ---- RF/LF Tier Bundles (from your 16-scenario matrix) ----

RF_ACTIONS = {
    "Excellent": [
        "Maintain revenue integrity through quarterly audits of charge capture and coding accuracy.",
        "Celebrate and share front-desk and provider best practices across all sites.",
        "Monitor chart closure timeliness as a reliability metric; maintain ≥95% within 24 hours.",
        "Conduct periodic registration and payer mapping spot checks to ensure data integrity.",
        "Continue reconciliation and charge validation as part of standard workflow discipline.",
        "Reinforce staff engagement through recognition and retention initiatives tied to performance.",
        "Use this site as a benchmark for peer-to-peer learning and throughput optimization.",
        "Review KPI trends quarterly to ensure continued alignment with growth and efficiency goals.",
    ],
    "Stable": [
        "Maintain monthly revenue-cycle reviews to ensure continued accuracy and throughput.",
        "Track chart closure performance as a standing metric (target ≥95% closed within 24 hours).",
        "Conduct periodic front-desk observations to reinforce AIDET and POS scripting consistency.",
        "Perform random charge-entry and coding audits to validate ongoing accuracy.",
        "Monitor registration and payer mapping via KPI dashboards and exception reporting.",
        "Benchmark AR aging against peers and address trends proactively.",
        "Continue reconciliation and charge validation as part of standard workflow discipline.",
    ],
    "At Risk": [
        "Conduct weekly huddles focused on revenue drivers and recurring error trends.",
        "Observe front-desk operations to ensure AIDET and POS scripting adherence.",
        "Monitor chart closures to ensure ≥90% are completed within 24 hours.",
        "Review charge entry and missing modifiers weekly to prevent leakage.",
        "Audit registration and payer mapping for ongoing accuracy.",
        "Perform weekly AR aging reviews to identify and correct top denial drivers.",
        "Continue daily reconciliation of deposits and charges, emphasizing prevention and accuracy.",
    ],
    "Critical": [
        "Conduct daily huddles focused on revenue drivers, front-end accuracy, and billing backlog reduction.",
        "Prevent closures through proactive staffing adjustments and contingency planning.",
        "Observe front-desk operations to ensure AIDET, POS scripting, and collection adherence.",
        "Perform an immediate scrub and cleanup of open coding and work queues; verify all charges are captured and corrected.",
        "Enforce chart closure ≤24 hours with real-time monitoring and accountability.",
        "Launch intensive revenue-cycle remediation: review charge entry, coding accuracy, and missing modifiers daily.",
        "Implement AR aging hygiene with detailed review, denial categorization, and clear ownership for resolution.",
        "Audit registration and payer mapping accuracy; correct plan mismatches and coverage gaps.",
        "Ensure appointment reminder calls are made; no patients turned away due to avoidable scheduling issues.",
        "Conduct daily reconciliation of deposits, charges, and collections to validate revenue capture integrity.",
    ],
}

LF_ACTIONS = {
    "Excellent": [
        "Maintain quarterly productivity audits and efficiency validation.",
        "Recognize and celebrate team performance to reinforce engagement and retention.",
        "Use this site as a model for throughput training and onboarding new leaders.",
        "Continue PCM-based staffing planning and validate forecast accuracy quarterly.",
        "Benchmark workflow efficiency metrics against top-quartile peers.",
        "Support innovation pilots or technology adoption to maintain leading performance.",
        "Maintain continuous feedback loops to sustain engagement and prevent burnout.",
    ],
    "Stable": [
        "Conduct monthly productivity review and benchmark performance against peers.",
        "Optimize shift templates for visit trends and seasonality using PCM logic.",
        "Encourage staff participation in process-improvement ideas and throughput innovations.",
        "Rotate cross-trained staff to maintain flexibility and engagement.",
        "Review time clock data for start/stop alignment and workflow consistency.",
        "Reinforce recognition and accountability for efficiency goals met.",
        "Begin succession and leadership readiness planning for key roles.",
    ],
    "At Risk": [
        "Conduct weekly schedule balancing based on rolling four-week visit trends.",
        "Cross-train staff to increase schedule flexibility and reduce coverage gaps.",
        "Monitor overtime weekly; address recurring high-volume days with float coverage.",
        "Conduct monthly stay interviews with high-performing staff to prevent turnover.",
        "Review clinic workflows for bottlenecks; streamline patient flow and documentation touchpoints.",
        "Evaluate provider-to-staff ratio; realign support where throughput lag occurs.",
        "Reinforce clear role assignments and task ownership during peak periods.",
    ],
    "Critical": [
        "Conduct daily schedule reviews to align staffing with visit volume and acuity.",
        "Implement overtime freeze except for approved coverage emergencies.",
        "Deploy float/PRN or cross-trained staff to cover high-risk shifts.",
        "Review turnover data; identify root causes and initiate stay interviews.",
        "Enforce real-time productivity monitoring; address idle-time and throughput delays.",
        "Implement shift handoff huddles to reduce inefficiencies and communication breakdowns.",
        "Conduct burnout assessments; provide rapid support or schedule relief.",
        "Streamline workflow by eliminating redundant tasks and reassigning non-clinical duties where possible.",
        "Initiate a 12-week staffing recovery plan with HR and Operations (PCM support).",
    ],
}

SCENARIO_DIAGNOSES = {
    ("Excellent", "Excellent"): "Both revenue and labor exceed benchmarks; optimal alignment — benchmark clinic.",
    ("Excellent", "Stable"): "Revenue strong; labor near benchmark with minor imbalance.",
    ("Excellent", "At Risk"): "High revenue with emerging labor strain — turnover, overtime, or burnout risk.",
    ("Excellent", "Critical"): "Revenue strong but labor inefficiency is driving significant cost escalation.",
    ("Stable", "Excellent"): "Lean staffing with steady revenue — opportunity to capture untapped throughput.",
    ("Stable", "Stable"): "Balanced, sustainable performance — risk of plateau without targeted improvement.",
    ("Stable", "At Risk"): "Revenue steady but labor costs creeping up — early inefficiency or drift.",
    ("Stable", "Critical"): "Revenue acceptable, but labor inefficiency is accelerating — margin compression risk.",
    ("At Risk", "Excellent"): "Strong labor efficiency but revenue leakage — under-coding, registration errors, or delayed billing.",
    ("At Risk", "Stable"): "Revenue softness with steady labor cost — front-end leakage likely.",
    ("At Risk", "At Risk"): "Dual drift — both revenue and labor slipping from optimal range.",
    ("At Risk", "Critical"): "Weak revenue with high labor inefficiency — accelerating margin loss.",
    ("Critical", "Excellent"): "Lean staffing but severe revenue leakage — systemic capture or billing failure.",
    ("Critical", "Stable"): "Revenue decline with average labor cost — profitability margin eroding.",
    ("Critical", "At Risk"): "Dual erosion — revenue and labor efficiency slipping together.",
    ("Critical", "Critical"): "Systemic distress — low revenue, high labor cost, and workforce instability.",
}

# Map (LF tier, RF tier) -> scenario number for 4×4 grid
SCENARIO_MAP = {
    ("Critical", "Critical"): 1, ("Critical", "At Risk"): 2, ("Critical", "Stable"): 3, ("Critical", "Excellent"): 4,
    ("At Risk", "Critical"): 5, ("At Risk", "At Risk"): 6, ("At Risk", "Stable"): 7, ("At Risk", "Excellent"): 8,
    ("Stable", "Critical"): 9, ("Stable", "At Risk"): 10, ("Stable", "Stable"): 11, ("Stable", "Excellent"): 12,
    ("Excellent", "Critical"): 13, ("Excellent", "At Risk"): 14, ("Excellent", "Stable"): 15, ("Excellent", "Excellent"): 16,
}


def scenario_name(rf_t: str, lf_t: str) -> str:
    rev_map = {
        "Excellent": "High Revenue",
        "Stable": "Stable Revenue",
        "At Risk": "Low Revenue",
        "Critical": "Critical Revenue",
    }
    lab_map = {
        "Excellent": "Efficient Labor",
        "Stable": "Stable Labor",
        "At Risk": "At-Risk Labor",
        "Critical": "Critical Labor",
    }
    return f"{rev_map.get(rf_t, rf_t)} / {lab_map.get(lf_t, lf_t)}"


def build_scenario_grid(active_rf_tier: str, active_lf_tier: str):
    rf_cols = TIER_ORDER
    lf_rows = TIER_ORDER
    data = []
    for lf in lf_rows:
        row = []
        for rf in rf_cols:
            row.append(SCENARIO_MAP[(lf, rf)])
        data.append(row)
    df = pd.DataFrame(
        data,
        index=[f"LF: {r}" for r in lf_rows],
        columns=[f"RF: {c}" for c in rf_cols],
    )

    def highlight_active(val, row_idx, col_idx):
        lf_here = lf_rows[row_idx]
        rf_here = rf_cols[col_idx]
        if (lf_here == active_lf_tier) and (rf_here == active_rf_tier):
            return "background-color: #fdd835; color: #000; font-weight: 700;"
        return ""

    styler = df.style.format(precision=0)
    for r in range(len(lf_rows)):
        for c in range(len(rf_cols)):
            styler = styler.set_properties(
                subset=(df.index[r], df.columns[c]),
                **{"text-align": "center", "font-weight": "500"},
            )
            styler = styler.apply(
                lambda s, r=r, c=c: [highlight_active(v, r, c) for v in s],
                axis=1,
                subset=(df.index[r], df.columns[c]),
            )
    styler = styler.set_table_styles(
        [{"selector": "th", "props": [("text-align", "center")]}]
    ).hide(axis="index", level=None)
    return df, styler


def format_money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def pos_should_be_top3(
    rpv_gap: float,
    avg_copay: float = 30.0,
    copay_eligibility: float = 0.5,
    leakage_rate: float = 0.25,
) -> bool:
    lift = avg_copay * copay_eligibility * leakage_rate
    return lift >= rpv_gap


def prescriptive_actions(rf_t: str, lf_t: str, rpv_gap: float):
    """
    Returns dict with diagnosis, top3, extended, huddle_script, daily_patch,
    using the official 16-scenario RF/LF matrix plus POS logic.
    """
    diagnosis = SCENARIO_DIAGNOSES.get((rf_t, lf_t), scenario_name(rf_t, lf_t))

    rf_list = RF_ACTIONS.get(rf_t, [])
    lf_list = LF_ACTIONS.get(lf_t, [])

    combined = rf_list + lf_list
    if not combined:
        combined = ["Sustain current performance and monitor for drift."]

    top3 = combined[:3]
    extended = combined[3:]

    # POS lever layered on top
    if rf_t in ("Critical", "At Risk", "Stable"):
        if pos_should_be_top3(rpv_gap):
            top3.append("Run a POS co-pay capture push (scripts, training, accountability).")
        else:
            extended.append("Quick POS audit (co-pay scripts, training, ClearPay accountability).")

    huddle_script = (
        "5-Minute Morning Huddle:\n"
        "• Today’s priorities: Top 3 levers above\n"
        "• Throughput focus: door-to-room < 10 min; room-to-provider < 15 min\n"
        "• Reliability: close charts same day; handoffs clear; escalate bottlenecks early"
    )
    daily_patch = (
        "Daily reminder: review Top 3 levers, confirm staffing vs demand, "
        "call out risks early, and recognize wins in real time."
    )

    extended.append("Daily 5-minute huddle: review Top 3 levers, VPDA drivers, and risks.")
    extended.append("Treat SWB% as context only; anchor decisions in VVI (NRPV/LCV, RF, and LF).")

    return {
        "diagnosis": diagnosis,
        "top3": top3[:3],
        "extended": extended,
        "huddle_script": huddle_script,
        "daily_patch": daily_patch,
    }


# ----------------------------
# Optional AI Insights helper
# ----------------------------

def ai_generate_insights(
    rf_score: float,
    lf_score: float,
    vvi_score: float,
    rpv: float,
    lpv: float,
    swb_pct: float,
    scenario_text: str,
    period: str,
):
    """
    Returns (ok, markdown_text). ok=False with a friendly reason if AI is not configured.
    AI only explains; it must NOT change or restate the numbers incorrectly.
    """
    if OpenAI is None:
        return False, "OpenAI SDK not installed. Add `openai` to requirements.txt to enable AI Insights."

    api_key = None
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return False, "Missing `OPENAI_API_KEY` in Streamlit Secrets. Add it to enable AI Insights."

    try:
        client = OpenAI(api_key=api_key)

        system_prompt = (
            "You are the Visit Value Agent (VVA). "
            "Use the provided scores as immutable ground truth. "
            "Do NOT invent numbers or contradict them. "
            "Be concise, actionable, and on-brand for Bramhall Consulting. "
            "Organize output as: Summary (2–3 bullets) • Why • What to do next (Top 3)."
        )

        user_payload = {
            "rf_score": rf_score,
            "lf_score": lf_score,
            "vvi_score": vvi_score,
            "rpv": rpv,
            "lpv": lpv,
            "swb_pct": swb_pct,
            "scenario": scenario_text,
            "period": period,
        }

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Use this JSON strictly as inputs (do not change numbers):\n"
                        f"{user_payload}\n\n"
                        "Write markdown with:\n"
                        "### Summary\n"
                        "• 2–3 tight bullets\n\n"
                        "### Why this is happening\n"
                        "Short explanation grounded in RF/LF/VVI and scenario.\n\n"
                        "### What to do next (Top 3)\n"
                        "Numbered list; crisp, manager-actionable."
                    ),
                },
            ],
        )
        text = resp.choices[0].message.content.strip()
        return True, text
    except Exception as e:
        return False, f"AI call failed: {e}"


# ----------------------------
# Session state
# ----------------------------

if "step" not in st.session_state:
    st.session_state.step = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "runs" not in st.session_state:
    st.session_state.runs = []  # list of dicts (name + results)


def next_step():
    st.session_state.step += 1


def reset():
    st.session_state.step = 1
    st.session_state.answers = {}


# ----------------------------
# Instructions (summary)
# ----------------------------

with st.expander("Instructions (summary)", expanded=False):
    st.write(
        "Answer one question at a time. When finished you’ll get: "
        "1) a Calculation Table (incl. SWB%), 2) a VVI/RF/LF scoring table, "
        "3) a scenario classification with prescriptive actions, "
        "4) a KPI bar chart, and 5) a print-ready Executive Summary/PDF."
    )

# ----------------------------
# Input Flow
# ----------------------------

st.markdown("### Start VVI Assessment")

if st.session_state.step == 1:
    visits = st.number_input(
        "How many total patient visits occurred during this time period?",
        min_value=1,
        step=1,
        key="visits_input",
    )
    st.button(
        "Next",
        disabled=visits <= 0,
        on_click=lambda: (
            st.session_state.answers.update({"visits": int(visits)}),
            next_step(),
        ),
    )

elif st.session_state.step == 2:
    net_rev = st.number_input(
        "What was the total net revenue collected? ($)",
        min_value=0.01,
        step=100.0,
        format="%.2f",
        key="net_rev_input",
    )
    st.button(
        "Next",
        disabled=net_rev <= 0,
        on_click=lambda: (
            st.session_state.answers.update({"net_revenue": float(net_rev)}),
            next_step(),
        ),
    )

elif st.session_state.step == 3:
    labor_cost = st.number_input(
        "Total labor cost ($) (W2 + PRN + OT + contract/locum)",
        min_value=0.01,
        step=100.0,
        format="%.2f",
        key="labor_cost_input",
    )
    st.button(
        "Next",
        disabled=labor_cost <= 0,
        on_click=lambda: (
            st.session_state.answers.update({"labor_cost": float(labor_cost)}),
            next_step(),
        ),
    )

elif st.session_state.step == 4:
    period = st.selectbox(
        "What time period does this represent?",
        ["Week", "Month", "Quarter", "Year"],
        key="period_input",
    )
    st.button(
        "Next",
        on_click=lambda: (
            st.session_state.answers.update({"period": period}),
            next_step(),
        ),
    )

elif st.session_state.step == 5:
    r_target = st.number_input(
        "Revenue target per visit (default $140)",
        min_value=1.0,
        value=140.0,
        step=1.0,
        format="%.2f",
        key="rev_target_input",
    )
    st.button(
        "Next",
        on_click=lambda: (
            st.session_state.answers.update({"rev_target": float(r_target)}),
            next_step(),
        ),
    )

elif st.session_state.step == 6:
    l_target = st.number_input(
        "Labor target per visit (default $85)",
        min_value=1.0,
        value=85.0,
        step=1.0,
        format="%.2f",
        key="lab_target_input",
    )
    st.button(
        "Run Assessment",
        on_click=lambda: (
            st.session_state.answers.update({"lab_target": float(l_target)}),
            next_step(),
        ),
    )

# ----------------------------
# Results
# ----------------------------

if st.session_state.step >= 7:
    a = st.session_state.answers
    visits = float(a.get("visits", 0))
    net_rev = float(a.get("net_revenue", 0.0))
    labor = float(a.get("labor_cost", 0.0))
    period = a.get("period", "-")
    rt = float(a.get("rev_target", 140.0))
    lt = float(a.get("lab_target", 85.0))

    if visits <= 0 or net_rev <= 0 or labor <= 0:
        st.warning(
            "Please enter non-zero values for visits, net revenue, and labor cost, then run again."
        )
        st.stop()

    # Core metrics
    rpv = net_rev / visits  # Net Revenue per Visit (NRPV)
    lcv = labor / visits  # Labor Cost per Visit (LCV)
    swb_pct = labor / net_rev

    # RF and LF
    rf_raw = (rpv / rt) if rt else 0.0
    lf_raw = (lt / lcv) if lcv else 0.0
    rf_score = round(rf_raw * 100, 2)
    lf_score = round(lf_raw * 100, 2)
    rf_t = tier(rf_score)
    lf_t = tier(lf_score)

    # VVI (raw) and normalized using benchmark ratio
    vvi_raw = (rpv / lcv) if lcv else 0.0
    vvi_target = (rt / lt) if (rt and lt) else 1.67
    vvi_score = round((vvi_raw / vvi_target) * 100, 2)
    vvi_t = tier(vvi_score)

    rpv_gap = max(0.0, rt - rpv)
    actions = prescriptive_actions(rf_t, lf_t, rpv_gap)
    scenario_text = actions["diagnosis"]

    st.success("Assessment complete. See results below.")

    # ---------- Impact Simulator ----------
    with st.expander("Optional: Simulate impact of improvement", expanded=False):
        st.caption(
            "Adjust Net Revenue per Visit (NRPV) and Labor Cost per Visit (LCV) "
            "by dollars or percent to see how VVI, RF, and LF could move if "
            "your prescriptive actions are successful. This does not change your "
            "core scores above; it is a what-if view."
        )

        mode = st.radio(
            "Adjust by:",
            ["Percent change", "Dollar change"],
            horizontal=True,
        )

        c1, c2 = st.columns(2)
        if mode == "Percent change":
            nrpv_delta_pct = c1.number_input(
                "NRPV change (%)", value=5.0, step=1.0, format="%.1f"
            )
            lcv_delta_pct = c2.number_input(
                "LCV change (%)", value=-5.0, step=1.0, format="%.1f"
            )

            sim_rpv = rpv * (1 + nrpv_delta_pct / 100.0)
            sim_lcv = lcv * (1 + lcv_delta_pct / 100.0)
        else:
            nrpv_delta_amt = c1.number_input(
                "NRPV change ($)", value=5.0, step=1.0, format="%.2f"
            )
            lcv_delta_amt = c2.number_input(
                "LCV change ($)", value=-5.0, step=1.0, format="%.2f"
            )

            sim_rpv = rpv + nrpv_delta_amt
            sim_lcv = lcv + lcv_delta_amt

        sim_rpv = max(sim_rpv, 0.01)
        sim_lcv = max(sim_lcv, 0.01)

        sim_rf_raw = sim_rpv / rt
        sim_lf_raw = lt / sim_lcv
        sim_vvi_raw = sim_rpv / sim_lcv
        sim_vvi_target = (rt / lt) if (rt and lt) else 1.67
        sim_rf_score = sim_rf_raw * 100
        sim_lf_score = sim_lf_raw * 100
        sim_vvi_score = (sim_vvi_raw / sim_vvi_target) * 100

        sim_df = pd.DataFrame(
            {
                "Index": ["Current", "Simulated"],
                "NRPV": [format_money(rpv), format_money(sim_rpv)],
                "LCV": [format_money(lcv), format_money(sim_lcv)],
                "VVI Score": [f"{vvi_score:.1f}", f"{sim_vvi_score:.1f}"],
                "RF Score": [f"{rf_score:.1f}", f"{sim_rf_score:.1f}"],
                "LF Score": [f"{lf_score:.1f}", f"{sim_lf_score:.1f}"],
            }
        )

        st.write("**Simulated impact (does not overwrite actual results):**")
        st.dataframe(sim_df, use_container_width=True, hide_index=True)

        fig_sim, ax_sim = plt.subplots(figsize=(6, 2.5))
        labels = ["VVI", "RF", "LF"]
        current_vals = [vvi_score, rf_score, lf_score]
        sim_vals = [sim_vvi_score, sim_rf_score, sim_lf_score]
        x = range(len(labels))
        bar_width = 0.35

        ax_sim.barh(
            [i + bar_width for i in x],
            current_vals,
            height=bar_width,
            label="Current",
        )
        ax_sim.barh(
            x,
            sim_vals,
            height=bar_width,
            label="Simulated",
        )

        ax_sim.set_yticks([i + bar_width / 2 for i in x])
        ax_sim.set_yticklabels(labels)
        ax_sim.set_xlabel("Score (0–100+)")
        ax_sim.legend()
        ax_sim.spines["right"].set_visible(False)
        ax_sim.spines["top"].set_visible(False)
        st.pyplot(fig_sim)

    # ---------- KPI bars ----------
    def render_kpi_bars(vvi_score: float, rf_score: float, lf_score: float):
        labels = ["VVI (normalized 0–100)", "Revenue Factor (RF)", "Labor Factor (LF)"]
        values = [vvi_score, rf_score, lf_score]
        x_max = max(120, max(values) + 15)

        fig, ax = plt.subplots(figsize=(8.5, 2.8))
        bands = [
            (0, 90, "#d9534f"),
            (90, 95, "#f0ad4e"),
            (95, 100, "#ffd666"),
            (100, x_max, "#5cb85c"),
        ]
        for s, e, c in bands:
            ax.axvspan(s, e, color=c, alpha=0.15, lw=0)
        bars = ax.barh(labels, values, color="#2e2e2e", height=0.55)
        for bar, v in zip(bars, values):
            ax.text(
                v + (x_max * 0.01),
                bar.get_y() + bar.get_height() / 2,
                f"{v:.2f}",
                va="center",
                ha="left",
                fontsize=10,
            )
        ax.set_xlim(0, x_max)
        ax.set_xlabel("Score")
        ax.set_ylabel("")
        ax.grid(False, axis="y")
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["left"].set_visible(False)
        st.subheader("Key Metrics & Scores")
        st.pyplot(fig)
        return fig

    kpi_fig = render_kpi_bars(vvi_score, rf_score, lf_score)

    # ---------- Calculation table ----------
    calc_df = pd.DataFrame(
        {
            "Metric": [
                "Total visits",
                "Net revenue collected",
                "Total labor cost",
                "Net Revenue per Visit (NRPV)",
                "Labor Cost per Visit (LCV)",
                "Revenue benchmark target (NRPV target)",
                "Labor benchmark target (LCV target)",
                "Labor cost as % of revenue (SWB%)",
                "Revenue score (RF)",
                "Labor score (LF)",
                "VVI (NRPV ÷ LCV)",
                "VVI score (normalized 0–100)",
                "Scenario",
            ],
            "Value": [
                f"{int(visits):,}",
                format_money(net_rev),
                format_money(labor),
                format_money(rpv),
                format_money(lcv),
                format_money(rt),
                format_money(lt),
                f"{swb_pct * 100:.1f}%",
                f"{rf_score} ({rf_t})",
                f"{lf_score} ({lf_t})",
                f"{vvi_raw:.3f}",
                f"{vvi_score} ({vvi_t})",
                scenario_text,
            ],
        }
    )
    st.subheader("Calculation Table")
    st.dataframe(calc_df, use_container_width=True, hide_index=True)

    # ---------- Scoring table (VVI emphasized) ----------
    score_df = pd.DataFrame(
        {
            "Index": [
                "Visit Value Index (VVI)",
                "Revenue Factor (RF)",
                "Labor Factor (LF)",
            ],
            "Formula": [
                "NRPV ÷ LCV (normalized vs. benchmark ratio)",
                "NRPV ÷ Target NRPV",
                "Target LCV ÷ LCV",
            ],
            "Raw Value": [
                f"{vvi_raw:.3f}",
                f"{rf_raw:.3f}",
                f"{lf_raw:.3f}",
            ],
            "Weighted Score (0–100)": [
                f"{vvi_score:.2f}",
                f"{rf_score:.2f}",
                f"{lf_score:.2f}",
            ],
            "Tier": [vvi_t, rf_t, lf_t],
        }
    )

    st.subheader("VVI / RF / LF Scoring Table")

    def highlight_vvi(row):
        if row.name == 0:
            return [
                "font-weight:700; background-color:#f7f2d3; "
                "border-top:1px solid #ccc; border-bottom:1px solid #ccc;"
            ] * len(row)
        return [""] * len(row)

    styler_score = (
        score_df.style.apply(highlight_vvi, axis=1).set_properties(**{"text-align": "left"})
    )
    st.dataframe(styler_score, use_container_width=True, hide_index=True)

    # ---------- Scenario Grid ----------
    st.subheader("📊 VVI 16-Scenario Grid")
    df_grid, styler_grid = build_scenario_grid(rf_t, lf_t)
    st.dataframe(styler_grid, use_container_width=True)

    # ---------- Prescriptive output ----------
    st.subheader("Scenario")
    st.write(f"**{actions['diagnosis']}** — period: **{period}**.")
    st.write("**Top 3 (Immediate):**")
    for i, item in enumerate(actions["top3"], start=1):
        st.write(f"{i}) {item}")

    st.write("**Extended Actions:**")
    for item in actions["extended"]:
        st.write(f"• {item}")

    with st.expander("Huddle Script (copy/paste)", expanded=False):
        st.code(actions["huddle_script"])

    with st.expander("Daily Reminder Patch", expanded=False):
        st.write(actions["daily_patch"])

    # ---------- AI Insights (optional) ----------
    with st.sidebar:
        use_ai = st.toggle(
            "Enable AI Insights (optional)",
            value=False,
            help="Uses your OpenAI key in Streamlit Secrets",
        )

    st.subheader("AI Insights (optional)")
    if not use_ai:
        st.info(
            "AI is off. Turn it on in the left sidebar to generate narrative insights. "
            "Your scores & actions above are still fully available."
        )
    else:
        if st.button("Generate AI Insights with AI"):
            ok, md = ai_generate_insights(
                rf_score=rf_score,
                lf_score=lf_score,
                vvi_score=vvi_score,
                rpv=rpv,
                lpv=lcv,
                swb_pct=swb_pct,
                scenario_text=scenario_text,
                period=period,
            )
            if ok:
                st.markdown(md)
            else:
                st.warning(md)

    # ---------- Print-ready PDF export ----------
    def make_pdf_buffer():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=LETTER)
        w, h = LETTER

        # Header (black & gold)
        c.setFillColor(colors.black)
        c.rect(0, h - 60, w, 60, fill=1, stroke=0)
        c.setFillColorRGB(0.48, 0.39, 0.0)  # gold-ish
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, h - 40, "Visit Value Agent 4.0 — Executive Summary")
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 10)
        c.drawRightString(
            w - 40, h - 40, "Bramhall Consulting, LLC — predict. perform. prosper."
        )

        y = h - 90

        def line(lbl, val):
            nonlocal y
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.black)
            c.drawString(40, y, lbl)
            c.setFont("Helvetica", 11)
            c.drawString(200, y, val)
            y -= 16

        line("Period:", period)
        line("Scenario:", actions["diagnosis"])
        line(
            "RF / LF:",
            f"{rf_score:.2f} ({rf_t})  |  {lf_score:.2f} ({lf_t})",
        )
        line(
            "NRPV / LCV / SWB%:",
            f"{format_money(rpv)}  |  {format_money(lcv)}  |  {swb_pct*100:.1f}%",
        )
        y -= 6

        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Top 3 Actions")
        y -= 14
        c.setFont("Helvetica", 11)
        for i, t3 in enumerate(actions["top3"], start=1):
            c.drawString(50, y, f"{i}) {t3}")
            y -= 14

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Extended Actions")
        y -= 14
        c.setFont("Helvetica", 11)
        for ex in actions["extended"]:
            c.drawString(50, y, f"• {ex}")
            y -= 14
            if y < 140:
                c.showPage()
                y = h - 80

        # Embed KPI chart
        img_buf = io.BytesIO()
        kpi_fig.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
        img_buf.seek(0)
        img = ImageReader(img_buf)
        c.drawImage(img, 40, 80, width=w - 80, height=180, preserveAspectRatio=True, mask="auto")

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.grey)
        c.drawRightString(
            w - 40,
            40,
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  •  VVA 4.0 (Pilot)",
        )
        c.save()
        buf.seek(0)
        return buf

    st.download_button(
        "Download Executive Summary (PDF)",
        data=make_pdf_buffer(),
        file_name="VVA_Executive_Summary.pdf",
        mime="application/pdf",
    )

    # ---------- Save run & compare ----------
    st.subheader("Save this run")
    default_name = f"Clinic {len(st.session_state.runs) + 1}"
    run_name = st.text_input("Name this clinic/run:", value=default_name)
    if st.button("Save to portfolio"):
        st.session_state.runs.append(
            {
                "name": run_name,
                "period": period,
                "RF": rf_score,
                "LF": lf_score,
                "VVI": vvi_score,
                "scenario": actions["diagnosis"],
            }
        )
        st.success(f"Saved: {run_name}")

    if st.session_state.runs:
        st.subheader("Portfolio (compare clinics)")
        comp = pd.DataFrame(st.session_state.runs)

        def color_by_vvi(row):
            try:
                vvi_val = float(row["VVI"])
            except Exception:
                return [""] * len(row)
            if vvi_val >= 100:
                color = "#d9f2d9"  # light green
            elif vvi_val >= 95:
                color = "#fff7cc"  # light yellow
            elif vvi_val >= 90:
                color = "#ffe0b3"  # light orange
            else:
                color = "#f8cccc"  # light red
            return [f"background-color: {color}"] * len(row)

        styler_comp = comp.style.apply(color_by_vvi, axis=1)
        st.dataframe(styler_comp, use_container_width=True, hide_index=True)

        c_port1, c_port2 = st.columns([3, 1])
        with c_port2:
            if st.button("Reset portfolio", help="Clear all saved clinics/runs."):
                st.session_state.runs = []
                st.success("Portfolio has been cleared.")

    st.divider()
    if st.button("Start a New Assessment"):
        reset()
