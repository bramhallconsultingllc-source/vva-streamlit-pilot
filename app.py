import textwrap
import os
import base64
import io
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- AI (optional) ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # app still runs if OpenAI SDK isn't installed


# ----------------------------
# Helpers
# ----------------------------
def get_base64_image(path: str) -> str:
    """Return a base64-encoded string for the image at `path`."""
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


# ----------------------------
# Page config & branded intro
# ----------------------------
st.set_page_config(
    page_title="Visit Value Agent 4.0 (Pilot)",
    page_icon="🩺",
    layout="centered",
)

# CSS for intro section + supporting metrics
intro_css = """
<style>
.intro-container {
    text-align: center;
    margin-bottom: 1.5rem;
}

/* Logo: desktop default */
.intro-logo {
    max-width: 220px !important;
    width: 100% !important;
    height: auto !important;
    margin: 0 auto !important;
    display: block;
}

/* Mobile responsiveness — larger logo on phone screens */
@media (max-width: 600px) {
    .intro-logo {
        max-width: 200px !important;
        width: 200px !important;
        margin-top: 0.6rem !important;
    }
}

@media (max-width: 400px) {
    .intro-logo {
        max-width: 180px !important;
        width: 180px !important;
        margin-top: 0.6rem !important;
    }
}

/* Thin gold line that "draws" across */
.intro-line-wrapper {
    display: flex;
    justify-content: center;
    margin: 1.2rem 0 0.8rem;
}

.intro-line {
    width: 0;
    height: 1.5px;
    background: #b08c3e;
    animation: lineGrow 1.6s ease-out forwards;
}

/* Text fade-in after the line draws */
.intro-text {
    opacity: 0;
    transform: translateY(6px);
    animation: fadeInUp 1.4s ease-out forwards;
    animation-delay: 1.0s;
    text-align: center;
}

/* Supporting metrics lists */
.supporting-metrics ul {
    margin-top: 0.25rem;
    margin-bottom: 0.4rem;
    padding-left: 1.1rem;
}
.supporting-metrics li {
    margin-bottom: 0.12rem;
}

/* Animations */
@keyframes lineGrow {
    0%   { width: 0; }
    100% { width: 340px; }
}

@keyframes fadeInUp {
    0%   { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
}
</style>
"""
st.markdown(intro_css, unsafe_allow_html=True)

LOGO_PATH = "Logo BC.png"

st.markdown("<div class='intro-container'>", unsafe_allow_html=True)

# Logo
if os.path.exists(LOGO_PATH):
    img_data = get_base64_image(LOGO_PATH)
    st.markdown(
        f'<img src="data:image/png;base64,{img_data}" class="intro-logo" />',
        unsafe_allow_html=True,
    )
else:
    st.caption(
        f"(Logo file '{LOGO_PATH}' not found — update LOGO_PATH or add the image to the app root.)"
    )

# Animated line + welcome text
intro_html = """
<div class='intro-line-wrapper'>
    <div class='intro-line'></div>
</div>

<div class='intro-text'>
    <h2>Welcome to the Visit Value Index&trade; (VVI)</h2>
    <p style="margin-top:0.4rem;font-style:italic;color:#555;text-align:center;">
        predict. perform. prosper.
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


tier = tier_from_score  # alias

# Colors used for tier-based highlighting
TIER_COLORS = {
    "Excellent": "#d9f2d9",  # light green
    "Stable": "#fff7cc",     # light yellow
    "At Risk": "#ffe0b3",    # light orange
    "Critical": "#f8cccc",   # light red
}

# ---- RF/LF Tier Bundles ----
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
    Returns a dict with:
      - diagnosis
      - top3 (combined)
      - rev_actions (revenue-focused)
      - lab_actions (labor-focused)
      - system_actions (operating rhythm / governance)
      - extended (all actions flattened, used for PDF)
          "huddle_script": huddle_script,
}

# ----------------------------
# Rendering helpers
# ----------------------------
def render_action_bucket(title: str, items):
    """
    Renders a titled list of actions in a consistent style.
    """
    if not items:
        st.info(f"No actions available for {title.lower()}.")
        return

    st.markdown(
        f"<h4 style='margin-top:0.4rem; margin-bottom:0.4rem;'>{title}</h4>",
        unsafe_allow_html=True,
    )

    for i, item in enumerate(items, start=1):
        st.markdown(f"{i}. {item}")

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
    ...

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
if "runs" not in st.session_state:
    st.session_state.runs = []

if "assessment_ready" not in st.session_state:
    st.session_state.assessment_ready = False


def reset_assessment():
    """Clear assessment state and restart app."""
    st.session_state.assessment_ready = False
    # Keep portfolio, just reset the current run
    st.rerun()


# ----------------------------
# Input Form (all at once)
# ----------------------------
st.markdown("### Input")

with st.form("vvi_inputs"):
    # Required inputs
    st.markdown("**Required**")

    visits = st.number_input(
        "Number of Visits",
        min_value=1,
        step=1,
        value=500,
        key="visits_input",
    )

    net_rev = st.number_input(
        "Net Operating Revenue (NOR)",
        min_value=0.01,
        step=100.0,
        format="%.2f",
        value=100000.00,
        key="net_rev_input",
    )

    labor_cost = st.number_input(
        "Labor Expense – Salaries, Wages, Benefits (SWB)",
        min_value=0.01,
        step=100.0,
        format="%.2f",
        value=65000.00,
        key="labor_cost_input",
    )

    st.markdown("---")
    st.markdown(
        "**Optional**  \n"
        "<span style='font-size:0.8rem;color:#777;'>"
        "These optional inputs use industry-standard averages, "
        "but you can update them to better reflect your organization."
        "</span>",
        unsafe_allow_html=True,
    )

    r_target = st.number_input(
        "Budgeted NOR per Visit",
        min_value=1.0,
        value=140.0,
        step=1.0,
        format="%.2f",
        key="rev_target_input",
    )

    l_target = st.number_input(
        "Budgeted SWB per Visit",
        min_value=1.0,
        value=85.0,
        step=1.0,
        format="%.2f",
        key="lab_target_input",
    )

    submitted = st.form_submit_button("Run Assessment")

# ----------------------------
# Results
# ----------------------------
if submitted:
    st.session_state.assessment_ready = True

if st.session_state.assessment_ready:
    # Use current widget values for all downstream logic
    visits = float(st.session_state.visits_input)
    net_rev = float(st.session_state.net_rev_input)
    labor = float(st.session_state.labor_cost_input)
    rt = float(st.session_state.rev_target_input)
    lt = float(st.session_state.lab_target_input)
    period = "Custom"

    if visits <= 0 or net_rev <= 0 or labor <= 0:
        st.warning(
            "Please enter non-zero values for visits, net revenue, and labor cost."
        )
        st.stop()

    # Core metrics
    rpv = net_rev / visits  # Net Revenue per Visit (NRPV)
    lcv = labor / visits    # Labor Cost per Visit (LCV)
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

        st.markdown(
        """
<div style="
    background:#f5f5f5;
    border-left:4px solid #777;
    padding:0.9rem 1.1rem;
    border-radius:6px;
    font-size:0.95rem;
    color:#5a4a21;
    margin-top:1rem;
">
    <strong>Assessment complete.</strong> Your Executive Summary is ready below.
</div>
        """,
        unsafe_allow_html=True,
    )

        # ---------- Executive Summary heading ----------
    st.markdown(
        "<h2 style='text-align:center; margin-bottom:0.5rem;'>Executive Summary</h2>",
        unsafe_allow_html=True,
    )

    # ---------- Tier Legend (collapsible) ----------
    with st.expander("Scoring Tiers (0–100+)", expanded=False):
        st.markdown(
            """
<div style="
    margin-top:0.2rem;
    margin-bottom:0.4rem;
    padding:0.6rem 0.2rem;
    font-size:0.9rem;
    color:#333;
    line-height:1.6;
">
    <div style="margin-bottom:0.25rem;">
        <span style="font-size:1rem; margin-right:0.35rem;">🟢</span>
        <b>Excellent</b>: 100+ <span style="color:#555;">(Top performing)</span>
    </div>
    <div style="margin-bottom:0.25rem;">
        <span style="font-size:1rem; margin-right:0.35rem;">🟡</span>
        <b>Stable</b>: 95–99 <span style="color:#555;">(Healthy, within benchmark)</span>
    </div>
    <div style="margin-bottom:0.25rem;">
        <span style="font-size:1rem; margin-right:0.35rem;">🟠</span>
        <b>At Risk</b>: 90–94 <span style="color:#555;">(Performance drift emerging)</span>
    </div>
    <div>
        <span style="font-size:1rem; margin-right:0.35rem;">🔴</span>
        <b>Critical</b>: Below 90 <span style="color:#555;">(Immediate corrective focus)</span>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
    
    # ---------- Hero VVI card centered ----------
    left_spacer, hero_col, right_spacer = st.columns([1, 2, 1])
    vvi_bg = TIER_COLORS.get(vvi_t, "#f5f5f5")

    with hero_col:
        vvi_html = f"""
<div style="
    background:{vvi_bg};
    padding:1.3rem 1.5rem;
    border-radius:14px;
    border-top:5px solid #b08c3e;
    box-shadow:0 10px 24px rgba(0,0,0,0.10);
    text-align:center;
">
    <div style="font-size:0.7rem; letter-spacing:0.14em;
                text-transform:uppercase; color:#666;
                margin-bottom:0.4rem;">
        Visit Value Index (VVI)
    </div>
    <div style="font-size:2.3rem; font-weight:750; color:#222;">
        {vvi_score:.1f}
    </div>
    <div style="font-size:0.9rem; color:#444; margin-top:0.2rem;">
        Overall performance vs. benchmark
    </div>
    <div style="margin-top:0.6rem; font-size:0.86rem; color:#333;">
        Tier:
        <span style="
            display:inline-block;
            padding:0.15rem 0.55rem;
            border-radius:999px;
            background:rgba(0,0,0,0.04);
            font-weight:600;
            font-size:0.8rem;
        ">
            {vvi_t}
        </span>
    </div>
</div>
"""
        st.markdown(vvi_html, unsafe_allow_html=True)

    st.markdown("")  # small spacing under hero card

    # ---------- RF / LF horizontal mini-cards ----------
    c_rf, c_lf = st.columns(2)
    rf_bg = TIER_COLORS.get(rf_t, "#f5f5f5")
    lf_bg = TIER_COLORS.get(lf_t, "#f5f5f5")

    with c_rf:
        st.markdown(
            f"""
<div style="
    background:{rf_bg};
    padding:0.85rem 1.0rem;
    border-radius:10px;
    border-top:3px solid rgba(0,0,0,0.06);
    box-shadow:0 6px 16px rgba(0,0,0,0.06);
">
    <div style="font-size:0.7rem; letter-spacing:0.11em;
                text-transform:uppercase; color:#666;
                margin-bottom:0.15rem;">
        Revenue Factor (RF)
    </div>
    <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="font-size:1.4rem; font-weight:700; color:#222;">
            {rf_score:.0f}
        </div>
        <div style="
            font-size:0.78rem;
            padding:0.16rem 0.6rem;
            border-radius:999px;
            background:rgba(0,0,0,0.03);
            font-weight:600;
            color:#333;
        ">
            {rf_t}
        </div>
    </div>
    <div style="font-size:0.78rem; color:#555; margin-top:0.25rem;">
        Actual NRPV vs. benchmark NRPV
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with c_lf:
        st.markdown(
            f"""
<div style="
    background:{lf_bg};
    padding:0.85rem 1.0rem;
    border-radius:10px;
    border-top:3px solid rgba(0,0,0,0.06);
    box-shadow:0 6px 16px rgba(0,0,0,0.06);
">
    <div style="font-size:0.7rem; letter-spacing:0.11em;
                text-transform:uppercase; color:#666;
                margin-bottom:0.15rem;">
        Labor Factor (LF)
    </div>
    <div style="display:flex; align-items:center; justify-content:space-between;">
        <div style="font-size:1.4rem; font-weight:700; color:#222;">
            {lf_score:.0f}
        </div>
        <div style="
            font-size:0.78rem;
            padding:0.16rem 0.6rem;
            border-radius:999px;
            background:rgba(0,0,0,0.03);
            font-weight:600;
            color:#333;
        ">
            {lf_t}
        </div>
    </div>
    <div style="font-size:0.78rem; color:#555; margin-top:0.25rem;">
        Benchmark LCV vs. actual LCV
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
    
        # ---------- Scenario strip (below RF / LF) ----------
    st.markdown(
        f"""
<div style="
    margin-top:1.3rem;
    margin-bottom:1.6rem;
    padding:1.2rem 1.2rem;
    border-radius:12px;
    background:#f7f7f7;
    border-left:4px solid #e0e0e0;
    font-size:1.0rem;
    text-align:center;
">
    <div style="font-size:0.8rem; text-transform:uppercase;
                letter-spacing:0.14em; color:#555; margin-bottom:0.35rem;">
        Diagnostic Scenario
    </div>
    <div style="color:#222; font-size:1.05rem; line-height:1.5; font-weight:600;">
        {scenario_text}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ---------- Prescriptive Actions heading ----------
st.markdown(
    """
    <h3 style='margin-top:1.2rem; margin-bottom:0.6rem;'>
        Prescriptive Actions
    </h3>
    """,
    unsafe_allow_html=True,
)

# ---------- Tabs: one pane per theme ----------
tab_rev, tab_lab, tab_sys = st.tabs(
    ["Revenue Focus", "Labor & Throughput", "Operating Rhythm"]
)

with tab_rev:
    render_action_bucket("Revenue Actions", actions.get("rev_actions", []))

with tab_lab:
    render_action_bucket("Labor Actions", actions.get("lab_actions", []))

with tab_sys:
    render_action_bucket("Operating Rhythm", actions.get("system_actions", []))

    # ---------- Impact Simulator (optional what-if) ----------
    with st.expander("Optional: Simulate impact of improvement", expanded=False):
        st.caption(
            "Adjust Net Revenue per Visit (NRPV) and Labor Cost per Visit (LCV) "
            "by dollars or percent to see how VVI, RF, and LF could move if "
            "your prescriptive actions are successful. This does not change your "
            "core scores above; it is a what-if view."
        )
        ...

        mode = st.radio(
            "Adjust by:",
            ["Percent change", "Dollar change"],
            horizontal=True,
        )

        c_sim1, c_sim2 = st.columns(2)
        if mode == "Percent change":
            nrpv_delta_pct = c_sim1.number_input(
                "NRPV change (%)", value=5.0, step=1.0, format="%.1f"
            )
            lcv_delta_pct = c_sim2.number_input(
                "LCV change (%)", value=-5.0, step=1.0, format="%.1f"
            )

            sim_rpv = rpv * (1 + nrpv_delta_pct / 100.0)
            sim_lcv = lcv * (1 + lcv_delta_pct / 100.0)
        else:
            nrpv_delta_amt = c_sim1.number_input(
                "NRPV change ($)", value=5.0, step=1.0, format="%.2f"
            )
            lcv_delta_amt = c_sim2.number_input(
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
        x = np.arange(len(labels))
        bar_width = 0.35

        # Bars
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

        # Vertical target line at score 100
        ax_sim.axvline(100, linestyle="--", linewidth=1.2, alpha=0.7)

        ax_sim.set_yticks([i + bar_width / 2 for i in x])
        ax_sim.set_yticklabels(labels)
        ax_sim.set_xlabel("Score (0–100+)")
        ax_sim.legend()
        ax_sim.spines["right"].set_visible(False)
        ax_sim.spines["top"].set_visible(False)
        st.pyplot(fig_sim)

    # ---------- AI Insights (optional, in-page) ----------
    st.subheader("AI Insights (optional)")

    ai_choice = st.radio(
        "Use AI to generate a short executive narrative?",
        ["Off", "On"],
        index=0,
        horizontal=True,
        help="Uses your OpenAI key in Streamlit Secrets.",
    )

    if ai_choice == "Off":
        st.info(
            "AI is off. Turn it on above to generate a concise narrative for leaders. "
            "Your scores & actions above are still fully available without AI."
        )
    else:
        if st.button("Generate AI Insights"):
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

        # Header
        c.setFillColor(colors.black)
        c.rect(0, h - 60, w, 60, fill=1, stroke=0)
        c.setFillColorRGB(0.48, 0.39, 0.0)
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
        line("VVI:", f"{vvi_score:.2f} ({vvi_t})")
        line("RF / LF:", f"{rf_score:.2f}% ({rf_t})  |  {lf_score:.2f}% ({lf_t})")
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
            if y < 80:
                c.showPage()
                y = h - 80
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, "Extended Actions (cont.)")
                y -= 18
                c.setFont("Helvetica", 11)

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
                v = float(row["VVI"])
            except Exception:
                return [""] * len(row)
            if v >= 100:
                color = "#d9f2d9"
            elif v >= 95:
                color = "#fff7cc"
            elif v >= 90:
                color = "#ffe0b3"
            else:
                color = "#f8cccc"
            return [f"background-color: {color}"] * len(row)

        st.dataframe(
            comp.style.apply(color_by_vvi, axis=1),
            use_container_width=True,
            hide_index=True,
        )

        _, c_reset = st.columns([3, 1])
        with c_reset:
            if st.button("Reset portfolio"):
                st.session_state.runs = []
                st.success("Portfolio cleared.")

    st.divider()
    if st.button("Start a New Assessment"):
        reset_assessment()
