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
from reportlab.lib.utils import ImageReader

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


def format_money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


# ----------------------------
# Page config & branded intro
# ----------------------------
st.set_page_config(
    page_title="Visit Value Agent 4.0 (Pilot)",
    page_icon="🩺",
    layout="centered",
)

# CSS for intro & supporting metrics
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

/* Mobile responsiveness — shrink logo on smaller screens */
@media (max-width: 600px) {
    .intro-logo {
        max-width: 110px !important;
        width: 110px !important;
        margin-top: 0.4rem !important;
    }
}

@media (max-width: 400px) {
    .intro-logo {
        max-width: 95px !important;
        width: 95px !important;
        margin-top: 0.4rem !important;
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

/* Animations */
@keyframes lineGrow {
    0%   { width: 0; }
    100% { width: 340px; }
}

@keyframes fadeInUp {
    0%   { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
}

/* Supporting metrics */
.supporting-metrics ul {
    margin-top: 0.25rem;
    margin-bottom: 0.4rem;
}
.supporting-metrics li {
    margin-bottom: 0.12rem;
}
</style>
"""

LOGO_PATH = "Logo BC.png"  # update if your filename is different

# Apply CSS
st.markdown(intro_css, unsafe_allow_html=True)

# Intro block
st.markdown("<div class='intro-container'>", unsafe_allow_html=True)

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

# Colors used for tier-based highlighting (soft backgrounds)
TIER_COLORS = {
    "Excellent": "#d9f2d9",  # light green
    "Stable": "#fff7cc",  # light yellow
    "At Risk": "#ffe0b3",  # light orange
    "Critical": "#f8cccc",  # light red
}

# Stronger text/badge colors for tiers
TIER_PILL_COLORS = {
    "Excellent": "#2e7d32",
    "Stable": "#b08c3e",
    "At Risk": "#ef6c00",
    "Critical": "#c62828",
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
    ("Excellent", "Critical"): "Revenue strong but
