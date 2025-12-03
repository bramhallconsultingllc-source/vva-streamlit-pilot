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
    if 95 <= score < 100:
        return "Stable"
    if 90 <= score < 95:
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
        "executive_narrative": (
            "This clinic is performing at a top-quartile level: revenue per visit is strong and labor "
            "is deployed efficiently. Visits are being converted into margin without obvious waste, "
            "and the operating rhythm is likely reliable and well led. The focus here is not a major "
            "fix but protecting what works, avoiding hidden burnout, and selectively scaling this playbook "
            "to other sites."
        ),
        "root_causes": [
            "Clear roles and accountability across front desk, MAs, providers, and billing.",
            "Staffing templates closely aligned with visit patterns and acuity.",
            "Reliable workflows for intake, rooming, documentation, and checkout.",
            "Disciplined revenue-cycle habits (accurate registration, coding, and POS).",
            "Engaged leadership presence with regular huddles and KPI review.",
        ],
        "do_tomorrow": [
            "Brief huddle to recognize performance and reinforce “what good looks like.”",
            "Verify yesterday’s charts are closed and POS collections reconciled.",
            "Ask staff where today’s biggest risk to flow might be and mitigate early.",
        ],
        "next_7_days": [
            "Run a simple time-study on a busy session to confirm throughput remains tight.",
            "Spot-check coding and POS for any early signs of revenue leakage.",
            "Check schedule templates against actual demand to confirm continued fit.",
        ],
        "next_30_60_days": [
            "Document this clinic’s playbook (staffing, workflows, huddle routines).",
            "Use this site as a peer-teaching location for under-performing clinics.",
            "Refresh stay interviews or engagement touchpoints with key staff.",
        ],
        "next_60_90_days": [
            "Review succession plans for front-line leaders and key roles.",
            "Stress-test capacity for modest volume growth without harming VVI.",
            "Refine KPIs and dashboards to keep leading indicators visible.",
        ],
        "risks": [
            "Complacency or “we’re fine” mindset leading to gradual drift.",
            "Hidden burnout from high performers carrying too much load.",
            "Key-person risk in front-line leadership or revenue-cycle experts.",
            "Volume growth that outpaces capacity and erodes performance.",
        ],
        "expected_impact": [
            "Sustain VVI above benchmark while absorbing moderate volume growth.",
            "Protect margin through early detection of drift or leakage.",
            "Create a repeatable model that can be lifted to other clinics.",
        ],
    },

    "scenario_02": {
        "id": 2,
        "rf_tier": "Excellent",
        "lf_tier": "Stable",
        "title": "Scenario 2 — RF: Excellent / LF: Stable",
        "label": "High Revenue + Stable Labor",
        "executive_narrative": (
            "Revenue performance is strong and labor cost per visit is on benchmark. The clinic is "
            "converting visits into margin reliably, with room for thoughtful efficiency gains. The "
            "goal is to preserve revenue integrity while gently tuning staffing, workflows, and "
            "throughput to move labor from Stable toward Excellent—without destabilizing the team."
        ),
        "root_causes": [
            "Effective front-end and coding practices driving strong NRPV.",
            "Staffing levels generally matched to demand, with some pockets of slack or rework.",
            "Workflows that function but may have unnecessary steps or handoffs.",
            "Predictable schedule templates but limited cross-training or flexibility.",
        ],
        "do_tomorrow": [
            "5-minute huddle to celebrate strong revenue and share today’s flow priorities.",
            "Check yesterday’s POS collections and registration accuracy.",
            "Ask leaders and staff where they see wasted steps or downtime in the day.",
        ],
        "next_7_days": [
            "Complete a light throughput review on a busy clinic session.",
            "Identify 1–2 tasks that can be streamlined or re-sequenced to save time.",
            "Review overtime and schedule patterns for small, recurring inefficiencies.",
        ],
        "next_30_60_days": [
            "Tune staffing templates using recent volume and no-show patterns.",
            "Cross-train select staff to flex across roles during peaks.",
            "Standardize best practices from this site into simple checklists and huddle scripts.",
        ],
        "next_60_90_days": [
            "Target a modest labor efficiency lift (e.g., 2–4% LCV improvement) with no loss of access.",
            "Formalize a quarterly review of staffing, throughput metrics, and VVI trends.",
            "Share efficiency wins and lessons learned across peer clinics.",
        ],
        "risks": [
            "Over-tightening labor and harming access, morale, or revenue.",
            "Ignoring emerging inefficiencies because overall results look “good enough.”",
            "Under-investing in engagement, leading to avoidable turnover later.",
        ],
        "expected_impact": [
            "2–4% LCV improvement while sustaining Excellent revenue performance.",
            "3–6% VVI lift from balanced revenue and labor tuning.",
            "Stronger resilience to demand swings without major staffing changes.",
        ],
    },

    "scenario_03": {
        "id": 3,
        "rf_tier": "Excellent",
        "lf_tier": "At Risk",
        "title": "Scenario 3 — RF: Excellent / LF: At Risk",
        "label": "High Revenue + Emerging Labor Inefficiency",
        "executive_narrative": (
            "Revenue performance is strong, but labor cost per visit is beginning to drift above "
            "benchmark. This is an early warning scenario: the clinic is still creating value, "
            "but it is spending more labor than necessary to do so. The priority is to correct "
            "role drift and workflow friction now, before it progresses to severe inefficiency."
        ),
        "root_causes": [
            "Gradual role drift for MAs and front-desk staff (extra tasks, unclear ownership).",
            "Throughput slowdowns causing more labor minutes per visit.",
            "Scheduling templates that no longer match actual visit patterns.",
            "Rising overtime or heavier use of float/PRN coverage.",
            "Rework from documentation lag, callbacks, or unresolved patient issues.",
        ],
        "do_tomorrow": [
            "Stability-focused huddle naming this as an early-warning labor trend.",
            "Review yesterday’s overtime and float/PRN usage.",
            "Ask staff to identify “top 2” time-wasters in their day.",
        ],
        "next_7_days": [
            "Conduct a simple time-study on one busy clinic session.",
            "Map MA and front-desk tasks to identify duplication or low-value work.",
            "Review staffing and schedule templates vs. actual volume by hour and day.",
            "Spot-check chart closure timeliness and documentation rework.",
        ],
        "next_30_60_days": [
            "Refine staffing templates and shift patterns to match demand more closely.",
            "Clarify roles and expectations to reduce role drift and handoff confusion.",
            "Streamline 1–2 high-friction workflows (e.g., intake, rooming, phone callbacks).",
            "Introduce a basic labor and throughput KPI review into weekly huddles.",
        ],
        "next_60_90_days": [
            "Set a modest labor efficiency target (e.g., 4–8% LCV improvement) with guardrails.",
            "Invest in cross-training to increase flexibility without adding FTEs.",
            "Reassess burnout and engagement through quick pulse checks or stay interviews.",
        ],
        "risks": [
            "Drift into Scenario 4 if labor issues are not addressed early.",
            "Burnout rising quietly as staff absorb more tasks and complexity.",
            "Provider frustration if support becomes inconsistent.",
            "Access or patient experience declining if throughput continues to slow.",
        ],
        "expected_impact": [
            "4–8% LCV improvement by correcting role drift and rework.",
            "5–9% VVI improvement from restoring balance between revenue and labor.",
            "Protection of a strong revenue base while keeping the team sustainable.",
        ],
    },

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
        "executive_narrative": (
            "This clinic has strong labor efficiency and predictable operational performance "
            "but is underperforming slightly on revenue capture. The team is running lean and "
            "effectively, creating an opportunity to leverage labor strength to drive additional "
            "revenue. This scenario often signals missed front-end or mid-cycle revenue "
            "opportunities that can be corrected without major operational disruption."
        ),
        "root_causes": [
            "Registration or payer mapping errors may be lowering revenue capture.",
            "Providers may be undercoding, missing modifiers, or documenting insufficiently.",
            "Chart closure is likely good, but front-end scripting may be inconsistent.",
            "Patient flow is efficient, but front-desk variability could be reducing POS performance.",
            "Revenue leakage may be occurring in small, repeatable ways (mid-cycle leakage).",
        ],
        "do_tomorrow": [
            "Daily 5-minute huddle (focus: accuracy + consistency).",
            "Registration + POS audit.",
            "Chart closure ≤24 hours.",
        ],
        "next_7_days": [
            "Repeat all staples.",
            "Do a targeted coding audit (10–15 encounters/provider).",
            "Validate payer mapping accuracy for top 5 payers.",
            "Review POS scripting with front-desk staff.",
            "Observe 2 provider sessions for documentation efficiency.",
        ],
        "next_30_60_days": [
            "Train providers on proper E/M level selection and modifier usage.",
            "Implement weekly charge review for accuracy and completeness.",
            "Standardize registration workflow across all shifts.",
            "Launch front-desk scripting refresh with performance tracking.",
        ],
        "next_60_90_days": [
            "Build a quarterly revenue integrity review cadence.",
            "Develop internal “coding champions” among clinical staff.",
            "Integrate revenue checkpoints into shift-lead responsibilities.",
            "Create a simple dashboard for revenue drivers (POS, coding, denials).",
        ],
        "risks": [
            "Slow drift in coding accuracy.",
            "Increasing denial rates.",
            "Provider variation in documentation.",
            "Front-desk turnover impacting accuracy.",
            "Declining POS performance.",
        ],
        "expected_impact": [
            "2–5% revenue improvement through capture accuracy.",
            "3–6% VVI improvement from better revenue-to-labor balance.",
            "Margin strengthening without additional staffing.",
        ],
    },

    "scenario_06": {
        "id": 6,
        "rf_tier": "Stable",
        "lf_tier": "Stable",
        "title": "Scenario 6 — RF: Stable / LF: Stable",
        "label": "Balanced Revenue + Balanced Labor",
        "executive_narrative": (
            "The clinic is operating near benchmark on both revenue and labor. This is a balanced, "
            "steady performance state where operational reliability is good but not exceptional. "
            "The opportunity here is to avoid plateauing by identifying targeted improvements that "
            "can push the clinic into top-quartile performance."
        ),
        "root_causes": [
            "Revenue cycle workflows are functional but lack continuous improvement.",
            "Throughput is adequate but could be more efficient.",
            "Staffing may not be optimized for peak vs. trough demand.",
            "Variability in scripting, documentation, or handoffs may be diluting performance.",
            "Staff engagement and leadership cadence may be “good but not great.”",
        ],
        "do_tomorrow": [
            "Morning huddle.",
            "Registration/POS audit.",
            "Chart closure ≤24 hours.",
        ],
        "next_7_days": [
            "Repeat staples.",
            "Conduct a 1-day throughput observation to identify micro-delays.",
            "Audit provider documentation for consistency.",
            "Validate staffing alignment for high-volume days.",
            "Evaluate front-desk scripting adherence.",
        ],
        "next_30_60_days": [
            "Implement a staffing “load leveling” plan (balanced shifts).",
            "Enhance training for intake/documentation efficiency.",
            "Strengthen the KPI review cadence (weekly → scorecards).",
            "Improve cross-training depth to increase flexibility.",
        ],
        "next_60_90_days": [
            "Develop a quarterly operations optimization roadmap.",
            "Create a clinic-specific best-practice library.",
            "Improve leader rounding frequency and accountability.",
            "Launch a recognition program to maintain engagement.",
        ],
        "risks": [
            "Performance plateau → drift into At Risk category.",
            "Variability in throughput.",
            "Overtime creep beginning.",
            "Registration errors rising.",
            "Turnover in front-line roles.",
        ],
        "expected_impact": [
            "3–5% improvement in both RF and LF with targeted refinement.",
            "4–7% VVI improvement from balanced gains.",
            "Margin protection and steady improvement over the quarter.",
        ],
    },

    "scenario_07": {
        "id": 7,
        "rf_tier": "Stable",
        "lf_tier": "At Risk",
        "title": "Scenario 7 — RF: Stable / LF: At Risk",
        "label": "Balanced Revenue + Emerging Labor Inefficiency",
        "executive_narrative": (
            "Revenue is acceptable and near target, but labor costs are starting to drift upward. "
            "This is an early warning sign that operational inefficiency is emerging. Addressing "
            "labor drift now prevents margin compression and protects organizational stability. "
            "The good news: revenue is not the problem — so leadership can focus squarely on "
            "throughput and staffing alignment."
        ),
        "root_causes": [
            "Throughput is slowing, requiring more labor hours per visit.",
            "MA or front-desk role drift is increasing.",
            "Staffing templates may no longer match visit patterns.",
            "Overtime usage is rising.",
            "Task duplication or rework (handoff issues).",
            "Documentation delays from providers or staff.",
            "Early-stage burnout impacting performance.",
        ],
        "do_tomorrow": [
            "5-minute huddle.",
            "Registration + POS check.",
            "Chart closure ≤24 hours.",
        ],
        "next_7_days": [
            "Repeat staples.",
            "Complete a throughput time study for one high-volume day.",
            "Tighten OT approval for 7 days to reveal bottlenecks.",
            "Remove 1–2 nonclinical tasks from MA workflow.",
            "Conduct a quick stay interview with key staff.",
        ],
        "next_30_60_days": [
            "Re-align staffing templates using actual volume patterns.",
            "Conduct cross-training rotation to reduce bottlenecks.",
            "Strengthen provider documentation workflows.",
            "Rebuild shift handoff structure to reduce rework.",
            "Implement twice-weekly KPI review (LCV, throughput, chart closure).",
        ],
        "next_60_90_days": [
            "Redesign intake and rooming processes for efficiency.",
            "Develop a burnout-prevention and recognition framework.",
            "Establish a quarterly staffing forecast process.",
            "Reinforce leadership rounding and accountability.",
        ],
        "risks": [
            "OT >8% of SWB.",
            "Rising MA/front-desk turnover.",
            "Slower rooming or intake times.",
            "Provider frustration with delays.",
            "Chart closure dropping below 90%.",
            "Increasing patient wait times.",
        ],
        "expected_impact": [
            "5–10% LCV improvement once labor drift is corrected.",
            "4–7% VVI improvement with throughput gains.",
            "Strong margin stabilization within 1–2 quarters.",
        ],
    },

    "scenario_08": {
        "id": 8,
        "rf_tier": "Stable",
        "lf_tier": "Critical",
        "title": "Scenario 8 — RF: Stable / LF: Critical",
        "label": "Balanced Revenue + Severe Labor Inefficiency",
        "executive_narrative": (
            "The clinic is generating acceptable revenue, but labor performance has deteriorated "
            "significantly, creating a major margin pressure point. This is a high-risk scenario: "
            "revenue is fine, but the clinic’s cost structure and workflow reliability are breaking "
            "down. Without rapid intervention, staff turnover, burnout, and throughput failure are likely."
        ),
        "root_causes": [
            "Chronic overstaffing or poor schedule alignment.",
            "Heavy overtime or PRN usage.",
            "Workflow breakdowns creating rework.",
            "Intake, rooming, or triage inefficiencies slowing throughput.",
            "Documentation delays causing extra workload.",
            "Poor role clarity or excessive administrative burden.",
            "Burnout across support roles.",
        ],
        "do_tomorrow": [
            "Daily huddle.",
            "Registration/POS check.",
            "Chart closure ≤24 hours.",
        ],
        "next_7_days": [
            "Repeat staples.",
            "Conduct daily staffing alignment review for each shift.",
            "Temporarily freeze overtime except emergencies.",
            "Reassign tasks to reduce MA overload and role drift.",
            "Add cross-trained float staff to stabilize high-risk shifts.",
            "Begin daily throughput monitoring with leaders (MA + provider).",
        ],
        "next_30_60_days": [
            "Redesign staffing templates using real visit data.",
            "Improve handoff structure between shifts.",
            "Rebuild intake and rooming workflow.",
            "Reinforce provider documentation expectations.",
            "Conduct burnout assessment with targeted support plans.",
        ],
        "next_60_90_days": [
            "Launch a 12-week staffing recovery plan (Operations + HR).",
            "Remove non–value-added tasks permanently.",
            "Formalize reliability cadence (weekly KPI + monthly review).",
            "Invest in culture and recognition to reduce turnover.",
        ],
        "risks": [
            "High turnover (>10% quarterly).",
            "Overtime consistently high.",
            "Provider dissatisfaction with support.",
            "Increasing patient wait times.",
            "Underutilized or misassigned staff.",
            "Workflow inconsistency across shifts.",
        ],
        "expected_impact": [
            "10–15% reduction in LCV with targeted intervention.",
            "5–9% improvement in VVI from throughput restoration.",
            "Meaningful margin recovery within 1–2 quarters.",
        ],
    },
        "scenario_09": {
        "id": 9,
        "rf_tier": "At Risk",
        "lf_tier": "Excellent",
        "title": "Scenario 9 — RF: At Risk / LF: Excellent",
        "label": "Low Revenue + Strong Labor Efficiency",
        "executive_narrative": (
            "This clinic is running efficiently from a labor standpoint, but revenue is underperforming. "
            "The team is doing the work with discipline and reliability, yet value is not fully captured. "
            "This pattern typically signals front-end, coding, or mid-cycle revenue leakage rather than a "
            "staffing problem. The opportunity is to keep labor intact while tightening revenue integrity."
        ),
        "root_causes": [
            "Under-coding or conservative E/M level selection by providers.",
            "Missing modifiers or incomplete charge capture.",
            "Registration and payer mapping errors reducing collectible revenue.",
            "Inconsistent front-desk POS scripting and collection follow-through.",
            "Denials and write-offs not being aggressively worked and prevented.",
            "Documentation gaps limiting appropriate coding and billing.",
        ],
        "do_tomorrow": [
            "5-minute huddle (focus: revenue integrity).",
            "Perform a quick POS and registration accuracy check.",
            "Confirm all charts are closed within 24 hours.",
        ],
        "next_7_days": [
            "Repeat daily staples.",
            "Conduct a targeted coding audit (10–20 encounters per provider).",
            "Review top denial categories and identify preventable patterns.",
            "Observe front-desk check-in and POS scripting for 1–2 sessions.",
            "Validate payer plan selection and mapping for your top payers.",
        ],
        "next_30_60_days": [
            "Deliver focused coding education to providers using real cases.",
            "Standardize registration, POS, and insurance verification workflows.",
            "Implement a weekly charge review for accuracy and completeness.",
            "Stand up a simple denial-prevention playbook for staff.",
        ],
        "next_60_90_days": [
            "Build a quarterly revenue integrity review cadence.",
            "Designate coding or documentation champions among clinicians.",
            "Integrate revenue checkpoints into front-line leader routines.",
            "Roll out a basic dashboard for revenue drivers and denials.",
        ],
        "risks": [
            "Denial rates creeping up over time.",
            "Revenue per visit drifting further below benchmark.",
            "Provider frustration if feedback is delayed or unclear.",
            "Front-desk turnover disrupting scripting and accuracy.",
            "Leadership assuming a “volume problem” instead of a capture issue.",
        ],
        "expected_impact": [
            "4–8% NRPV improvement through better capture and coding.",
            "5–9% VVI improvement with revenue gains on an efficient labor base.",
            "Margin lift without adding labor hours or FTEs.",
        ],
    },

    "scenario_10": {
        "id": 10,
        "rf_tier": "At Risk",
        "lf_tier": "Stable",
        "title": "Scenario 10 — RF: At Risk / LF: Stable",
        "label": "Low Revenue + Steady Labor",
        "executive_narrative": (
            "Labor is reasonably controlled, but revenue is lagging. The clinic is covering demand with an "
            "adequate staffing model, yet value is not fully realized per visit. This is a classic revenue-"
            "cycle improvement scenario: stabilizing and optimizing front-end, coding, and mid-cycle processes "
            "to lift revenue without major labor changes."
        ),
        "root_causes": [
            "Under-coding or inconsistent use of modifiers.",
            "Inadequate documentation to support higher complexity visits.",
            "Leaky POS execution or weak pre-visit financial clearance.",
            "Missed ancillary services or add-on charges.",
            "Denials not being worked systematically or fed back to the front end.",
        ],
        "do_tomorrow": [
            "Morning huddle (revenue focus).",
            "Review yesterday’s POS collections and scripting adherence.",
            "Confirm same-day or ≤24-hour chart closure with providers.",
        ],
        "next_7_days": [
            "Repeat daily staples.",
            "Perform a small-sample charge and coding audit per provider.",
            "Identify top denial reasons and correct preventable front-end errors.",
            "Shadow front-desk and registration for a half-day to observe failure points.",
            "Double-check payer mapping for common plans and products.",
        ],
        "next_30_60_days": [
            "Implement standardized scripting for registration and POS.",
            "Launch provider documentation improvement using real examples.",
            "Create a weekly revenue huddle reviewing denials, AR, and NRPV trends.",
            "Tighten processes for ancillary orders, referrals, and follow-ups.",
        ],
        "next_60_90_days": [
            "Establish a recurring revenue integrity review (monthly/quarterly).",
            "Deploy simple dashboards for NRPV, denials, and collections.",
            "Integrate revenue-cycle performance into manager scorecards.",
            "Formalize feedback loops between billing and clinic operations.",
        ],
        "risks": [
            "Continued revenue softness eroding margin.",
            "Denial volumes increasing without prevention efforts.",
            "Front-desk fatigue if scripting expectations are unclear.",
            "Provider disengagement if documentation asks feel arbitrary.",
        ],
        "expected_impact": [
            "3–7% revenue uplift via improved capture and prevention of leakage.",
            "4–8% VVI improvement based on revenue gains at steady labor cost.",
            "Better financial performance with minimal disruption to staffing.",
        ],
    },

    "scenario_11": {
        "id": 11,
        "rf_tier": "At Risk",
        "lf_tier": "At Risk",
        "title": "Scenario 11 — RF: At Risk / LF: At Risk",
        "label": "Dual Drift: Revenue Softness + Labor Inefficiency",
        "executive_narrative": (
            "Both revenue and labor performance are drifting away from benchmark. The clinic is doing more work "
            "than it needs to for less revenue than it should earn per visit. Left unaddressed, this dual drift "
            "erodes margin and creates instability. The objective is to stabilize operations while simultaneously "
            "strengthening revenue capture and labor efficiency."
        ),
        "root_causes": [
            "Throughput inefficiencies increasing labor hours per visit.",
            "Role drift and unclear task ownership for MAs and front-desk staff.",
            "Under-coding and documentation gaps reducing revenue per visit.",
            "Weak POS performance and inconsistent scripting.",
            "Lack of routine KPI review for both revenue and labor metrics.",
            "Early burnout signals: fatigue, errors, rising absenteeism.",
        ],
        "do_tomorrow": [
            "5-minute stability huddle (focus: today’s flow + high-risk bottlenecks).",
            "Registration/POS accuracy check with real-time feedback.",
            "Verify all charts from the prior day are closed.",
        ],
        "next_7_days": [
            "Repeat stability staples.",
            "Complete a basic throughput time study (door-to-room, room-to-provider).",
            "Perform a small coding and charge capture audit.",
            "Review scheduling templates vs. actual demand patterns.",
            "Hold brief stay interviews with key staff to identify friction points.",
        ],
        "next_30_60_days": [
            "Refine staffing templates and shift patterns to match visit volume.",
            "Clarify and rebalance MA/front-desk task lists to reduce rework.",
            "Deliver focused documentation and coding refresh sessions.",
            "Install weekly KPI review for NRPV, LCV, throughput, and chart closure.",
        ],
        "next_60_90_days": [
            "Implement a mini operating system: huddles, scorecards, leader rounding.",
            "Streamline or eliminate low-value tasks contributing to burnout.",
            "Create an internal continuous-improvement backlog and cadence.",
            "Invest in morale and recognition tied to measurable improvement.",
        ],
        "risks": [
            "Slow slide into Critical for either RF or LF.",
            "Turnover among experienced staff and MAs.",
            "Provider frustration with inconsistent support.",
            "Patient dissatisfaction as waits increase and flow slows.",
        ],
        "expected_impact": [
            "6–12% VVI improvement with balanced gains across RF and LF.",
            "8–15% LCV improvement by tightening staffing and throughput.",
            "Reversal of margin erosion within 1–2 quarters.",
        ],
    },

    "scenario_12": {
        "id": 12,
        "rf_tier": "At Risk",
        "lf_tier": "Critical",
        "title": "Scenario 12 — RF: At Risk / LF: Critical",
        "label": "Low Revenue + Severe Labor Inefficiency",
        "executive_narrative": (
            "This clinic is underperforming on revenue while also carrying a highly inefficient labor cost structure. "
            "The result is rapid margin compression and growing operational risk. The priority is to stabilize the "
            "workforce and restore basic throughput reliability while simultaneously closing critical revenue leaks. "
            "Without decisive action, this site will remain a chronic underperformer."
        ),
        "root_causes": [
            "Misaligned staffing levels relative to volume and acuity.",
            "High overtime, PRN, or agency usage.",
            "Fragmented workflows causing rework and idle time.",
            "Under-coding and missed charges suppressing NRPV.",
            "Inconsistent or weak POS and registration execution.",
            "Staff burnout driving errors, absenteeism, and turnover.",
        ],
        "do_tomorrow": [
            "Daily stabilization huddle (flow + staffing + safety).",
            "Immediate POS and registration spot check.",
            "Confirm chart closure ≤24 hours with clear expectations.",
        ],
        "next_7_days": [
            "Repeat daily stabilization staples.",
            "Implement short-term overtime controls with exception approvals only.",
            "Conduct a rapid staffing and schedule review for each shift.",
            "Identify 2–3 obvious workflow bottlenecks and address them.",
            "Perform a focused coding and charge capture sample review.",
        ],
        "next_30_60_days": [
            "Redesign staffing templates to align with actual visit patterns.",
            "Clarify roles and responsibilities to reduce duplication and rework.",
            "Rebuild intake, rooming, and checkout workflows for efficiency.",
            "Deliver targeted coding and documentation training using clinic data.",
            "Establish a weekly operations + revenue review huddle.",
        ],
        "next_60_90_days": [
            "Implement a structured 8–12 week recovery plan with HR + Operations.",
            "Systematically eliminate non–value-added tasks from MA and front-desk workload.",
            "Formalize reliability cadence: huddles, KPI review, and escalation paths.",
            "Invest in culture, recognition, and burnout mitigation strategies.",
        ],
        "risks": [
            "Sustained negative margin at the clinic level.",
            "Accelerating turnover among high performers.",
            "Increasing patient dissatisfaction and complaints.",
            "Provider exit risk due to operational instability.",
        ],
        "expected_impact": [
            "12–20% VVI improvement when both revenue and labor are corrected.",
            "15–25% LCV improvement as labor inefficiency is addressed.",
            "Movement toward breakeven or positive margin within 2–3 quarters.",
        ],
    },

    "scenario_13": {
        "id": 13,
        "rf_tier": "Critical",
        "lf_tier": "Excellent",
        "title": "Scenario 13 — RF: Critical / LF: Excellent",
        "label": "Severe Revenue Leakage + Highly Efficient Labor",
        "executive_narrative": (
            "Labor performance is strong and efficient, but revenue is severely underperforming. "
            "This is a classic severe revenue-leakage scenario: the clinic is doing the work, but "
            "value is not being captured. Addressing front-end accuracy, coding, and denials can "
            "drive large revenue gains without increasing labor cost."
        ),
        "root_causes": [
            "Significant under-coding and conservative provider behavior.",
            "High rates of missing or incorrect modifiers.",
            "Frequent registration and insurance eligibility errors.",
            "Weak or inconsistent POS execution and follow-up.",
            "Denials not being corrected, fed back, or prevented at the front end.",
            "Documentation not supporting visit complexity.",
        ],
        "do_tomorrow": [
            "Revenue integrity huddle (front-end + coding focus).",
            "Immediate POS/registration audit for error rates.",
            "Confirm timely chart closure and documentation completeness.",
        ],
        "next_7_days": [
            "Repeat revenue integrity staples.",
            "Perform a high-yield coding/charge capture audit per provider.",
            "Review denial data for top 3 preventable categories.",
            "Shadow front-desk at check-in, POS, and insurance verification.",
            "Validate payer mapping and plan selection for common visit types.",
        ],
        "next_30_60_days": [
            "Deliver targeted coding and documentation training with clinic cases.",
            "Standardize registration, financial clearance, and POS workflows.",
            "Implement weekly denial-prevention and charge review huddles.",
            "Add simple checklists for front-desk and billing handoffs.",
        ],
        "next_60_90_days": [
            "Create a quarterly revenue integrity review cadence.",
            "Integrate revenue KPIs into clinic leader scorecards.",
            "Develop internal coding champions and coaching loops.",
            "Pair high-performing providers with those needing support.",
        ],
        "risks": [
            "Sustained revenue underperformance despite efficient labor.",
            "Denials and write-offs rising without prevention.",
            "Provider resistance if issues aren’t framed with data and support.",
            "Leadership misinterpreting the issue as a volume or staffing problem.",
        ],
        "expected_impact": [
            "10–20% NRPV improvement with focused revenue integrity work.",
            "8–15% VVI improvement leveraging strong labor efficiency.",
            "Significant margin recovery without additional FTEs.",
        ],
    },

    "scenario_14": {
        "id": 14,
        "rf_tier": "Critical",
        "lf_tier": "Stable",
        "title": "Scenario 14 — RF: Critical / LF: Stable",
        "label": "Severe Revenue Leakage + Labor Near Benchmark",
        "executive_narrative": (
            "Labor is near benchmark, but revenue performance is severely below expectations. "
            "The clinic is staffed reasonably, yet significant value is being lost in the revenue "
            "cycle. The priority is to aggressively identify and fix the biggest sources of revenue "
            "leakage while keeping labor steady and focused on high-reliability execution."
        ),
        "root_causes": [
            "Under-coding and incomplete documentation.",
            "High frequency of missed or incorrect modifiers and add-on codes.",
            "Front-end eligibility, registration, or plan selection errors.",
            "Weak POS collections and inconsistent scripting.",
            "Denials being worked slowly or without preventing recurrence.",
        ],
        "do_tomorrow": [
            "Revenue-focused morning huddle with front-desk + providers.",
            "Quick POS/registration accuracy spot check.",
            "Ensure all charts from the previous day are closed and documented.",
        ],
        "next_7_days": [
            "Repeat daily revenue staples.",
            "Run a focused coding/charge audit for high-volume visit types.",
            "Identify top 3 denial reasons and map them to front-end fixes.",
            "Shadow 1–2 providers to observe documentation and coding habits.",
            "Confirm AR follow-up and denial workqueues have clear ownership.",
        ],
        "next_30_60_days": [
            "Standardize financial clearance, registration, and POS workflows.",
            "Implement structured provider education using real denial and audit data.",
            "Launch a weekly micro-review of NRPV, denials, and collections.",
            "Tighten handoffs between clinic and billing teams with simple SLAs.",
        ],
        "next_60_90_days": [
            "Establish a quarterly revenue integrity and denial-prevention cadence.",
            "Elevate revenue KPIs into leadership scorecards and performance reviews.",
            "Build a simple “playbook” for common revenue failure modes and fixes.",
            "Spread lessons learned to peer clinics in the portfolio.",
        ],
        "risks": [
            "Persistent negative margin driven by low revenue.",
            "Provider disengagement if feedback is infrequent or unclear.",
            "Front-desk burnout if scripting and expectations are not supported.",
            "Denials normalizing as “background noise” instead of urgent signals.",
        ],
        "expected_impact": [
            "9–18% uplift in NRPV with targeted revenue-cycle work.",
            "7–14% VVI improvement with revenue gains on stable labor.",
            "Margin turnaround within 2–3 quarters if execution is consistent.",
        ],
    },

    "scenario_15": {
        "id": 15,
        "rf_tier": "Critical",
        "lf_tier": "At Risk",
        "title": "Scenario 15 — RF: Critical / LF: At Risk",
        "label": "Severe Revenue Leakage + Early Labor Inefficiency",
        "executive_narrative": (
            "Revenue performance is severely below expectations, and labor costs are beginning to drift upward. "
            "The clinic is at an inflection point: without intervention, it will progress toward full systemic "
            "distress. The play here is to stabilize labor efficiency while aggressively fixing front-end and "
            "coding-related revenue leakage."
        ),
        "root_causes": [
            "Front-end errors and under-coding driving low NRPV.",
            "Throughput slow-downs modestly increasing labor per visit.",
            "Role drift and unclear task ownership for MAs and front-desk staff.",
            "Rising overtime or schedule inefficiencies.",
            "Denials not being systematically prevented or fed back to operations.",
        ],
        "do_tomorrow": [
            "Stability huddle (flow + revenue + staffing).",
            "Spot check POS, registration, and insurance verification accuracy.",
            "Confirm same-day or ≤24-hour chart closure expectations.",
        ],
        "next_7_days": [
            "Repeat daily stability and revenue staples.",
            "Conduct a short throughput time study on one high-volume day.",
            "Run a focused coding and charge capture audit by provider.",
            "Review schedules vs. volume to identify misaligned shifts.",
            "Hold quick stay interviews with key staff to identify pain points.",
        ],
        "next_30_60_days": [
            "Refine staffing templates to better match visit patterns.",
            "Clarify and rebalance MA/front-desk task load to reduce rework.",
            "Deliver targeted provider documentation and coding training.",
            "Initiate a weekly operations + revenue performance huddle.",
        ],
        "next_60_90_days": [
            "Develop a 12-week improvement plan spanning revenue and labor.",
            "Eliminate low-value tasks contributing to burnout and inefficiency.",
            "Formalize reliability routines: huddles, KPIs, and escalation pathways.",
            "Invest in morale-building and recognition linked to measurable gains.",
        ],
        "risks": [
            "Drift into Scenario 16 (systemic distress) if not corrected.",
            "Increasing staff turnover and absenteeism.",
            "Provider dissatisfaction with support levels and throughput.",
            "Worsening patient experience as waits increase and errors persist.",
        ],
        "expected_impact": [
            "10–18% VVI improvement with coordinated revenue and labor work.",
            "12–20% NRPV and LCV combined impact over 2–3 quarters.",
            "Clear path away from systemic distress toward stability.",
        ],
    },

    "scenario_16": {
        "id": 16,
        "rf_tier": "Critical",
        "lf_tier": "Critical",
        "title": "Scenario 16 — RF: Critical / LF: Critical",
        "label": "Systemic Distress: Low Revenue + High Labor Cost",
        "executive_narrative": (
            "This is the most severe scenario: revenue is significantly underperforming while labor cost per visit "
            "is very high. The clinic is in systemic distress, with acute margin pressure and high risk of workforce "
            "instability. Immediate, coordinated intervention is required across staffing, workflow, and revenue "
            "integrity to prevent further deterioration."
        ),
        "root_causes": [
            "Chronic misalignment between staffing levels and actual demand.",
            "High overtime, PRN, or agency usage driving LCV up.",
            "Major workflow breakdowns creating rework and idle time.",
            "Severe under-coding, missed charges, or registration errors.",
            "Denials not being worked effectively or prevented.",
            "Burnout, disengagement, and turnover across key roles.",
        ],
        "do_tomorrow": [
            "Crisis huddle with clear focus: safety, flow, and revenue integrity.",
            "Immediate review of today’s staffing vs. schedule; correct obvious misalignments.",
            "Quick POS/registration and chart-closure compliance check.",
        ],
        "next_7_days": [
            "Hold daily stabilization huddles (staffing, throughput, revenue).",
            "Temporarily tighten overtime approvals and track usage daily.",
            "Conduct a rapid diagnostic on throughput and workflow bottlenecks.",
            "Sample audit of coding, charges, and denials by provider and visit type.",
            "Begin stay interviews and burnout check-ins with core staff.",
        ],
        "next_30_60_days": [
            "Redesign staffing templates and schedule structure to match volume.",
            "Rebuild core workflows (intake, rooming, checkout, documentation).",
            "Deliver focused provider documentation/coding training with immediate feedback.",
            "Stand up weekly operations + revenue steering meetings with clear owners.",
        ],
        "next_60_90_days": [
            "Implement a 12-week recovery roadmap owned by Operations and HR.",
            "Remove non–value-added tasks to reduce burnout and rework.",
            "Institutionalize reliability cadence: daily huddles, weekly KPI review, monthly deep dives.",
            "Rebuild culture and engagement through recognition, communication, and visible wins.",
        ],
        "risks": [
            "Sustained negative margin and consideration of service reduction or closure.",
            "High turnover among providers and key clinical support roles.",
            "Rising safety risk if instability is not controlled.",
            "Poor patient experience and reputational damage in the market.",
        ],
        "expected_impact": [
            "15–25% VVI improvement over 2–4 quarters with disciplined execution.",
            "20–30% improvement in LCV and NRPV combined as workflows stabilize.",
            "Movement from crisis toward controlled, sustainable performance.",
        ],
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

    # 2. Why This May Be Happening (Root Cause)
    with st.expander("2. Why This May Be Happening (Root Cause)"):
        roots = pack.get("root_causes") or []
        if not roots:
            st.info("Root causes not yet configured for this scenario.")
        else:
            st.markdown("**Possible primary drivers:**")
            for r in roots:
                st.markdown(f"- {r}")

    # 3. What To Do Next (Suggested Actions Based on This Scenario)
    with st.expander("3. What To Do Next (Suggested Actions Based on This Scenario)"):
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

    # 4. Risks Commonly Seen in This Scenario
    with st.expander("4. Risks Commonly Seen in This Scenario"):
        risks = pack.get("risks") or []
        if not risks:
            st.info("Risks to monitor not yet configured for this scenario.")
        else:
            for r in risks:
                st.markdown(f"- {r}")

    # 5. Possible Impact of Improvement
    with st.expander("5. Possible Impact of Improvement"):
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
- You ONLY answer from the fixed set of canned questions provided to you.
- You MUST refuse to answer any other questions or side conversations.

Authoritative sources:
- The Insight Pack content for the current scenario (title, label, executive narrative, root causes, actions, risks, expected impact).
- The numeric results: RF, LF, VVI, NRPV (rpv), LCV (lcv), SWB%, tiers.

Strict rules:
1) Do NOT add or modify actions. You may restate or summarize them, but never invent new steps, timelines, or operational levers.
2) Do NOT contradict the Insight Pack. If the Insight Pack is silent on something prescriptive, speak only in high-level principles.
3) Treat the Insight Pack as the authoritative source on scenario framing, patterns, and recommended actions.
4) Treat RF/LF/VVI and all numeric values as immutable ground truth. Never alter or reinterpret them.
5) Never give prescriptive content beyond what is already implied in the Insight Pack. You may explain, contextualize, rephrase, or format for different audiences (CFO, clinic manager, frontline staff).
6) You ONLY answer one of the allowed canned questions passed as `selected_question`.
   - If the user asks something outside the approved list, reply:
     “I’m only configured to answer the specific questions in the dropdown above.”
7) Maintain Bramhall Consulting’s tone: calm, professional, operational, supportive, and practical.

────────────────────────────────────────────────────────
ABSOLUTE-LANGUAGE GUARDRAILS — DO NOT BREAK THESE:
────────────────────────────────────────────────────────
Causality:
- Never present causes as certainties.
- Always frame contributors as possibilities: “may,” “could,” “often,” “commonly,” “typically,” “may be contributing,” “may reflect.”
- Never say “This clinic is burned out,” “Your staff is overstaffed,” “This caused…,” or “This is why…”
- Instead: “This scenario often reflects…,” “Possible contributors include…,” “This pattern may suggest areas to examine.”

Burnout / HR-Sensitive Issues:
- Never diagnose burnout, disengagement, morale problems, or personnel issues.
- If the Insight Pack references burnout, frame it as a *potential scenario pattern*, not a statement about the clinic.
- Avoid implying knowledge of individual behaviors, emotions, or health.

Staffing:
- Never assert staffing levels, turnover, or performance problems with certainty.
- Only reference what the Insight Pack states, framed as patterns typical of the scenario.

Prohibited Phrases (NEVER use):
- “your staff is…”
- “your providers are…”
- “this caused…”
- “this is the reason…”
- “you have burnout…”
- “you are overstaffed…”
- “this means your clinic…”
- “you need to…”
Use conditional phrasing instead.

────────────────────────────────────────────────────────
TONE & FORMATTING RULES:
────────────────────────────────────────────────────────
- Use concise paragraphs and bullet points for scannability.
- Maintain an advisory, coaching tone — not diagnostic, not directive.
- Ground everything in the scenario, not assumptions about the clinic.
- Stay neutral, factual, and steady.
- Avoid emotional language or personal commentary.
- When referencing risks or patterns, always use conditional phrasing.

────────────────────────────────────────────────────────
ENDING REQUIREMENT (MANDATORY):
────────────────────────────────────────────────────────
End every answer with ONE short motivational closing line, aligned with Bramhall Consulting’s tone:
- It must be operational, calm, and leadership-focused.
- It must not be emotional, cliché, or personal.
- It must be one sentence.

Acceptable tones:
- “Steady progress compounds.”
- “Small, consistent steps shift long-term performance.”
- “Clarity and calm execution strengthen reliability.”
- “Momentum is built one disciplined action at a time.”

Do NOT use any other inspirational language or emotional affirmations.
Keep it professional, brief, and grounded in operational excellence.

FORMATTING FOR THE MOTIVATIONAL CLOSING LINE:
- Always separate the motivational closing line from the main content using a markdown divider (“---”).
- Above the motivational line, add a bold label: **Leadership Reflection**
- Format the motivational line itself in italics.
- The final format should be:

---
**Leadership Reflection**  
*Steady progress compounds.*

- Always follow this structure exactly.
────────────────────────────────────────────────────────
Output:
- Answer in markdown.
- Be direct, avoid fluff, and keep responses scannable.
────────────────────────────────────────────────────────
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
        "Net Operating Revenue (NOR) ($)",
        min_value=0.01,
        step=100.0,
        format="%.2f",
        value=100000.00,
        key="net_rev_input",
    )

    labor_cost = st.number_input(
        "Labor Expense – Salaries, Wages, Benefits (SWB) ($)",
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
        "Budgeted NOR per Visit ($)",
        min_value=1.0,
        value=140.0,
        step=1.0,
        format="%.2f",
        key="rev_target_input",
    )

    l_target = st.number_input(
        "Budgeted SWB per Visit ($)",
        min_value=1.0,
        value=85.0,
        step=1.0,
        format="%.2f",
        key="lab_target_input",
    )

    # ✅ SUBMIT BUTTON *INSIDE* THE FORM
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

    rf_score_raw = rf_raw * 100
    lf_score_raw = lf_raw * 100

    # VVI (raw) and normalized using benchmark ratio
    vvi_raw = (rpv / lcv) if lcv else 0.0
    vvi_target = (rt / lt) if (rt and lt) else 1.67
    vvi_score_raw = (vvi_raw / vvi_target) * 100

    # One-decimal display scores
    rf_score = round(rf_score_raw, 1)
    lf_score = round(lf_score_raw, 1)
    vvi_score = round(vvi_score_raw, 1)

    # Tiers based on what we actually display
    rf_t = tier(rf_score)
    lf_t = tier(lf_score)
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
        <b>Excellent</b>: ≥100 <span style="color:#555;">(Top performing)</span>
    </div>
    <div style="margin-bottom:0.25rem;">
        <span style="font-size:1rem; margin-right:0.35rem;">🟡</span>
        <b>Stable</b>: 95–99.9 <span style="color:#555;">(Healthy, within benchmark)</span>
    </div>
    <div style="margin-bottom:0.25rem;">
        <span style="font-size:1rem; margin-right:0.35rem;">🟠</span>
        <b>At Risk</b>: 90–94.9 <span style="color:#555;">(Performance drift emerging)</span>
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
            {rf_score:.1f}
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
            {lf_score:.1f}
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
