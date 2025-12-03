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

# ----------------------------
# Static Insight Packs (16 Scenarios)
# ----------------------------

# Map RF/LF tier pair → scenario key
SCENARIO_LOOKUP = {
    ("Excellent", "Excellent"): "scenario_01",
    ("Excellent", "Stable"): "scenario_02",
    ("Excellent", "At Risk"): "scenario_03",
    ("Excellent", "Critical"): "scenario_04",
    ("Stable", "Excellent"): "scenario_05",
    ("Stable", "Stable"): "scenario_06",
    ("Stable", "At Risk"): "scenario_07",
    ("Stable", "Critical"): "scenario_08",
    ("At Risk", "Excellent"): "scenario_09",
    ("At Risk", "Stable"): "scenario_10",
    ("At Risk", "At Risk"): "scenario_11",
    ("At Risk", "Critical"): "scenario_12",
    ("Critical", "Excellent"): "scenario_13",
    ("Critical", "Stable"): "scenario_14",
    ("Critical", "At Risk"): "scenario_15",
    ("Critical", "Critical"): "scenario_16",
}

INSIGHT_PACKS = {
    # You’ll paste the text for Scenarios 1–3 here from the doc
    "scenario_01": {
        "id": 1,
        "rf_tier": "Excellent",
        "lf_tier": "Excellent",
        "title": "Scenario 1 — RF: Excellent / LF: Excellent",
        "label": "High Revenue + Efficient Labor",
        "executive_narrative": "TODO: paste Scenario 1 Executive Narrative.",
        "root_causes": [
            "TODO: paste Scenario 1 root cause bullets.",
        ],
        "do_tomorrow": [
            "TODO: Scenario 1 Do Tomorrow bullet 1",
        ],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_02": {
        "id": 2,
        "rf_tier": "Excellent",
        "lf_tier": "Stable",
        "title": "Scenario 2 — RF: Excellent / LF: Stable",
        "label": "High Revenue + Stable Labor",
        "executive_narrative": "TODO: paste Scenario 2 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_03": {
        "id": 3,
        "rf_tier": "Excellent",
        "lf_tier": "At Risk",
        "title": "Scenario 3 — RF: Excellent / LF: At Risk",
        "label": "High Revenue + Emerging Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 3 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },

    # ✅ Fully wired example from your pack:
    "scenario_04": {
        "id": 4,
        "rf_tier": "Excellent",
        "lf_tier": "Critical",
        "title": "Scenario 4 — RF: Excellent / LF: Critical",
        "label": "High Revenue + Severe Labor Inefficiency",
        "executive_narrative": (
            "This is the most margin-damaging combination: strong revenue performance "
            "overshadowed by severe labor inefficiency. Labor costs are substantially "
            "outpacing targets, eroding profitability and masking operational instability. "
            "Immediate intervention is required to prevent deeper workforce issues such as "
            "turnover, burnout, or schedule failures."
        ),
        "root_causes": [
            "Staffing is misaligned with demand (overstaffing or poor scheduling).",
            "Significant role drift and scope confusion across shifts.",
            "Workflow breakdown causing throughput collapse.",
            "Excessive overtime or reliance on PRN/agency labor.",
            "High documentation lag causing downstream rework.",
            "Operational cadence not functioning (no huddles, inconsistent KPIs).",
            "Burnout leading to performance drops.",
        ],
        "do_tomorrow": [
            "Morning huddle (stability focus).",
            "Registration + POS script accuracy check.",
            "Enforce chart closure ≤24 hours.",
        ],
        "next_7_days": [
            "Repeat non-negotiable staples.",
            "Conduct daily schedule reviews to align staffing with volume.",
            "Freeze overtime except pre-approved clinical need.",
            "Deploy cross-trained float staff to stabilize critical shifts.",
            "Perform an MA and front-office role drift reset.",
            "Begin daily throughput monitoring.",
        ],
        "next_30_60_days": [
            "Redesign the staffing template entirely using actual visit patterns.",
            "Implement standardized handoff huddles between shifts.",
            "Revamp intake, rooming, and MA task structure for clarity.",
            "Conduct burnout assessments with targeted interventions.",
            "Reinforce documentation workflows to reduce rework time.",
        ],
        "next_60_90_days": [
            "Build a 12-week staffing recovery plan with HR + Operations.",
            "Eliminate redundant or non–value-added tasks permanently.",
            "Create a reliability governance cadence with weekly KPI review.",
            "Relaunch culture-building and recognition efforts to stabilize the team.",
        ],
        "risks": [
            "Staff turnover >10% quarterly.",
            "Sustained overtime usage.",
            "Provider dissatisfaction.",
            "Wait times continuing to increase.",
            "Escalated patient complaints.",
            "Burnout-related absenteeism.",
        ],
        "expected_impact": [
            "10–18% LCV improvement through labor realignment.",
            "6–10% VVI improvement from workflow stabilization.",
            "Noticeable margin recovery within 1–2 quarters.",
        ],
    },

    # For 5–16, keep same structure and paste from the doc
    "scenario_05": {
        "id": 5,
        "rf_tier": "Stable",
        "lf_tier": "Excellent",
        "title": "Scenario 5 — RF: Stable / LF: Excellent",
        "label": "Stable Revenue + Efficient Labor",
        "executive_narrative": "TODO: paste Scenario 5 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_06": {
        "id": 6,
        "rf_tier": "Stable",
        "lf_tier": "Stable",
        "title": "Scenario 6 — RF: Stable / LF: Stable",
        "label": "Balanced Revenue + Balanced Labor",
        "executive_narrative": "TODO: paste Scenario 6 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_07": {
        "id": 7,
        "rf_tier": "Stable",
        "lf_tier": "At Risk",
        "title": "Scenario 7 — RF: Stable / LF: At Risk",
        "label": "Balanced Revenue + Emerging Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 7 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_08": {
        "id": 8,
        "rf_tier": "Stable",
        "lf_tier": "Critical",
        "title": "Scenario 8 — RF: Stable / LF: Critical",
        "label": "Balanced Revenue + Severe Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 8 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_09": {
        "id": 9,
        "rf_tier": "At Risk",
        "lf_tier": "Excellent",
        "title": "Scenario 9 — RF: At Risk / LF: Excellent",
        "label": "Low Revenue + Strong Labor Efficiency",
        "executive_narrative": "TODO: paste Scenario 9 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_10": {
        "id": 10,
        "rf_tier": "At Risk",
        "lf_tier": "Stable",
        "title": "Scenario 10 — RF: At Risk / LF: Stable",
        "label": "Low Revenue + Steady Labor",
        "executive_narrative": "TODO: paste Scenario 10 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_11": {
        "id": 11,
        "rf_tier": "At Risk",
        "lf_tier": "At Risk",
        "title": "Scenario 11 — RF: At Risk / LF: At Risk",
        "label": "Dual Drift: Revenue Softness + Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 11 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_12": {
        "id": 12,
        "rf_tier": "At Risk",
        "lf_tier": "Critical",
        "title": "Scenario 12 — RF: At Risk / LF: Critical",
        "label": "Low Revenue + Severe Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 12 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_13": {
        "id": 13,
        "rf_tier": "Critical",
        "lf_tier": "Excellent",
        "title": "Scenario 13 — RF: Critical / LF: Excellent",
        "label": "Severe Revenue Leakage + Highly Efficient Labor",
        "executive_narrative": "TODO: paste Scenario 13 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_14": {
        "id": 14,
        "rf_tier": "Critical",
        "lf_tier": "Stable",
        "title": "Scenario 14 — RF: Critical / LF: Stable",
        "label": "Severe Revenue Leakage + Labor Near Benchmark",
        "executive_narrative": "TODO: paste Scenario 14 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_15": {
        "id": 15,
        "rf_tier": "Critical",
        "lf_tier": "At Risk",
        "title": "Scenario 15 — RF: Critical / LF: At Risk",
        "label": "Severe Revenue Leakage + Early Labor Inefficiency",
        "executive_narrative": "TODO: paste Scenario 15 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
    "scenario_16": {
        "id": 16,
        "rf_tier": "Critical",
        "lf_tier": "Critical",
        "title": "Scenario 16 — RF: Critical / LF: Critical",
        "label": "Systemic Distress: Low Revenue + High Labor Cost",
        "executive_narrative": "TODO: paste Scenario 16 Executive Narrative.",
        "root_causes": [],
        "do_tomorrow": [],
        "next_7_days": [],
        "next_30_60_days": [],
        "next_60_90_days": [],
        "risks": [],
        "expected_impact": [],
    },
}

def get_insight_pack_for_tiers(rf_t: str, lf_t: str):
    """Return the static Insight Pack for the RF/LF tier pair, with fallbacks."""
    key = SCENARIO_LOOKUP.get((rf_t, lf_t))
    if not key:
        st.error(f"No scenario mapping configured for RF={rf_t}, LF={lf_t}.")
        return None, None

    pack = INSIGHT_PACKS.get(key)
    if not pack:
        st.error(f"Scenario '{key}' not yet configured in INSIGHT_PACKS.")
        return key, None

    return key, pack


def render_insight_pack_expanders(pack: dict):
    """5-expander layout for a single static Insight Pack."""

    if not pack:
        st.info("Insight Pack content not available for this scenario yet.")
        return

    # Subheading for the scenario
    st.markdown(
        f"#### {pack.get('title', 'Insight Pack')}  \n"
        f"<span style='color:#777;font-size:0.85rem;'>"
        f"{pack.get('label','')}</span>",
        unsafe_allow_html=True,
    )

    # 1. Executive Narrative
    with st.expander("1. Executive Narrative", expanded=True):
        st.markdown(pack.get("executive_narrative", "").strip() or "_Not yet configured._")

    # 2. Why This Is Happening (Root Cause)
    with st.expander("2. Why This Is Happening (Root Cause)"):
        roots = pack.get("root_causes") or []
        if not roots:
            st.info("Root causes not yet configured for this scenario.")
        else:
            st.markdown("**Primary drivers:**")
            for r in roots:
                st.markdown(f"- {r}")

    # 3. What To Do Next (Time-Phased Action Plan)
    with st.expander("3. What To Do Next (Time-Phased Action Plan)"):
        def render_phase(title, items):
            if not items:
                return
            st.markdown(f"**{title}**")
            for i, item in enumerate(items, start=1):
                st.markdown(f"{i}. {item}")
            st.markdown("")

        render_phase("Do Tomorrow — Non-negotiable staples", pack.get("do_tomorrow"))
        render_phase("Next 7 Days (Quick Wins)", pack.get("next_7_days"))
        render_phase("Next 30–60 Days (High-Impact Moves)", pack.get("next_30_60_days"))
        render_phase("Next 60–90 Days (Structural Fixes)", pack.get("next_60_90_days"))

        if not any([
            pack.get("do_tomorrow"),
            pack.get("next_7_days"),
            pack.get("next_30_60_days"),
            pack.get("next_60_90_days"),
        ]):
            st.info("Action plan not yet configured for this scenario.")

    # 4. Risks to Monitor
    with st.expander("4. Risks to Monitor"):
        risks = pack.get("risks") or []
        if not risks:
            st.info("Risks to monitor not yet configured for this scenario.")
        else:
            for r in risks:
                st.markdown(f"- {r}")

    # 5. Expected Impact
    with st.expander("5. Expected Impact"):
        impacts = pack.get("expected_impact") or []
        if not impacts:
            st.info("Expected impact not yet configured for this scenario.")
        else:
            for r in impacts:
                st.markdown(f"- {r}")


def format_money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

# ------------------------------------------------------
# AI Coach — System Prompt (strict rules for Q&A agent)
# ------------------------------------------------------
AI_COACH_SYSTEM_PROMPT = """
You are the VVI AI Coach for Bramhall Consulting.

Your role is narrow and specific:
- You ONLY answer from a fixed set of canned questions provided to you.
- You MUST refuse to answer any other questions or side conversations.

Authoritative sources:
- The Insight Pack content for the current scenario (title, label, executive narrative, root causes, actions, risks, expected impact).
- The numeric results: RF, LF, VVI, NRPV (rpv), LCV (lcv), SWB%, tiers.

Strict rules:
1) Do NOT add or modify actions. You may restate or summarize them, but never invent new steps, timelines, or levers.
2) Do NOT contradict the Insight Pack. If the Insight Pack is silent on something prescriptive, speak in high-level principles only.
3) Treat the Insight Pack as the authoritative source on scenario framing, root causes, and time-phased actions.
4) Treat RF/LF/VVI and other numeric values as immutable ground truth. Never change them.
5) Never generate prescriptive content beyond what is already implied in the Insight Pack. You may explain, contextualize, rephrase, or format for different audiences (CFO, clinic manager, staff).
6) You ONLY answer one of the allowed canned questions passed in as `selected_question`. 
   - If the user text or instructions seem to ask for anything else, reply:
     "I’m only configured to answer the specific questions in the dropdown above."
7) Stay on-brand: concise, professional, practical, and aligned with Bramhall Consulting’s tone.

Output:
- Answer in markdown.
- Be direct, avoid fluff, and keep responses scannable (bullets, short paragraphs).
"""
def ai_coach_answer(
    selected_question: str,
    rf_score: float,
    lf_score: float,
    vvi_score: float,
    rpv: float,
    lcv: float,
    swb_pct: float,
    insight_pack: dict,
):
    """
    Returns (ok, markdown_text) for the AI Coach panel.
    Enforces:
      - only canned questions are allowed
      - uses Insight Pack + metrics as context
    """

    if OpenAI is None:
        return False, "OpenAI SDK not installed. Add `openai` to requirements.txt to enable the AI Coach."

    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return False, "Missing `OPENAI_API_KEY` in Streamlit Secrets. Add it to enable the AI Coach."

    # Hard whitelist of allowed questions
    ALLOWED_QUESTIONS = [
        "Explain this scenario to a CFO who is new to VVI.",
        "What should I tell frontline managers in tomorrow’s huddle?",
        "If our LF improved to 80, what would that do to VVI?",
        "Summarize this clinic in 3 bullets.",
        "Why did we land in this scenario?",
        "What early indicators should we monitor based on this scenario?",
        "How do I build effective front-desk POS scripting?",
        "What are practical ways to improve morale?",
        "What steps can reduce burnout for MAs and front-desk staff?",
        "Convert this scenario into a 1-minute message for staff.",
    ]

    if selected_question not in ALLOWED_QUESTIONS:
        # Enforce "no conversation outside canned questions"
        return False, "I’m only configured to answer the specific questions in the dropdown above."

    # Build a compact context payload for the model
    pack = insight_pack or {}
    context = {
        "rf_score": rf_score,
        "lf_score": lf_score,
        "vvi_score": vvi_score,
        "rpv": rpv,
        "lcv": lcv,
        "swb_pct": swb_pct,
        "scenario_title": pack.get("title", ""),
        "scenario_label": pack.get("label", ""),
        "executive_narrative": pack.get("executive_narrative", ""),
        "root_causes": pack.get("root_causes", []),
        "do_tomorrow": pack.get("do_tomorrow", []),
        "next_7_days": pack.get("next_7_days", []),
        "next_30_60_days": pack.get("next_30_60_days", []),
        "next_60_90_days": pack.get("next_60_90_days", []),
        "risks": pack.get("risks", []),
        "expected_impact": pack.get("expected_impact", []),
    }

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            messages=[
                {"role": "system", "content": AI_COACH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Here is the current clinic context as JSON. "
                        "Use it strictly as your factual basis:\n"
                        f"{context}\n\n"
                        "Now answer ONLY this selected question, following all rules above:\n"
                        f"{selected_question}"
                    ),
                },
            ],
        )
        answer = resp.choices[0].message.content.strip()
        return True, answer
    except Exception as e:
        return False, f"AI Coach call failed: {e}"


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

    # Static Insight Pack for RF/LF
    scenario_key, insight_pack = get_insight_pack_for_tiers(rf_t, lf_t)

    # For compatibility with AI + PDF, derive simple fallbacks from static pack
    if insight_pack:
        scenario_text = (
            insight_pack.get("executive_narrative", "").strip()
            or insight_pack.get("label", "")
        )

        raw_actions = (
            (insight_pack.get("do_tomorrow") or [])
            + (insight_pack.get("next_7_days") or [])
        )
        top3_actions = raw_actions[:3]

        extended_actions = (
            (insight_pack.get("do_tomorrow") or [])
            + (insight_pack.get("next_7_days") or [])
            + (insight_pack.get("next_30_60_days") or [])
            + (insight_pack.get("next_60_90_days") or [])
        )
    else:
        scenario_text = f"{rf_t} Revenue / {lf_t} Labor"
        top3_actions = []
        extended_actions = []

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

    # 🔥 Divider + spacing between RF/LF and scenario
    st.markdown(
        """
        <hr style="
            border: none;
            border-top: 1px solid #e6e6e6;
            margin-top: 30px;
            margin-bottom: 30px;
        ">
        """,
        unsafe_allow_html=True,
    )

    # ---------- Insight Pack Detail (5 expanders) ----------
    render_insight_pack_expanders(insight_pack)

    # ---------- AI Coach (optional) ----------
    st.subheader("AI Coach (optional)")

    with st.expander("Ask a guided question about this clinic", expanded=False):
        st.caption(
            "The AI Coach can help you interpret results and communicate with leaders and staff. "
            "It only answers the specific questions in this list."
        )

        question = st.selectbox(
            "Select a question:",
            [
                "Explain this scenario to a CFO who is new to VVI.",
                "What should I tell frontline managers in tomorrow’s huddle?",
                "If our LF improved to 80, what would that do to VVI?",
                "Summarize this clinic in 3 bullets.",
                "Why did we land in this scenario?",
                "What early indicators should we monitor based on this scenario?",
                "How do I build effective front-desk POS scripting?",
                "What are practical ways to improve morale?",
                "What steps can reduce burnout for MAs and front-desk staff?",
                "Convert this scenario into a 1-minute message for staff.",
            ],
        )

        if st.button("Ask AI Coach"):
            ok, md = ai_coach_answer(
                selected_question=question,
                rf_score=rf_score,
                lf_score=lf_score,
                vvi_score=vvi_score,
                rpv=rpv,
                lcv=lcv,
                swb_pct=swb_pct,
                insight_pack=insight_pack,
            )
            if ok:
                st.markdown(md)
            else:
                st.warning(md)

    
    # ---------- Impact Simulator (optional what-if) ----------
    with st.expander("Optional: Simulate impact of improvement", expanded=False):
        ...
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
        line("Scenario:", scenario_text)  # 👈 use scenario_text instead of actions["diagnosis"]
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
        for i, t3 in enumerate(top3_actions, start=1):  # 👈 uses top3_actions list
            c.drawString(50, y, f"{i}) {t3}")
            y -= 14

        y -= 6
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Extended Actions")
        y -= 14
        c.setFont("Helvetica", 11)
        for ex in extended_actions:  # 👈 uses extended_actions list
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
