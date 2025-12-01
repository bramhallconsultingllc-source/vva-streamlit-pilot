# app.py
# Visit Value Agent 4.0 — Executive Operating System for Ambulatory Medicine™
# Bramhall Consulting | predict → perform → prosper

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import io
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ==============================
# Page Config & Luxury Dark Theme
# ==============================
st.set_page_config(
    page_title="Visit Value Agent 4.0",
    page_icon="Scalpel",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main {background:#0a0a0a; color:#f5f5f5;}
    h1, h2, h3 {color:#b08c3e; font-weight:600; text-align:center;}
    .big {font-size:5.5rem; font-weight:800; margin:0; line-height:1;}
    .gold {color:#b08c3e;}
    .metric-label {font-size:0.85rem; text-transform:uppercase; letter-spacing:0.1em; color:#888;}
    .stButton>button {background:#b08c3e; color:black; font-weight:bold; border:none;}
    .scenario-box {background:#1a1a1a; padding:1.2rem; border-radius:12px; border-left:5px solid #b08c3e;}
</style>
""", unsafe_allow_html=True)

# Logo
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=200)
st.markdown("<h1>Visit Value Agent 4.0</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#888; margin-top:-15px;'>predict → perform → prosper™</p>", unsafe_allow_html=True)
st.markdown("---")

# ==============================
# Core Logic
# ==============================
def get_tier(score: float) -> str:
    if score >= 100: return "Excellent"
    elif score >= 95: return "Stable"
    elif score >= 90: return "At Risk"
    else: return "Critical"

SCENARIO_DIAGNOSES = {
    ("Excellent","Excellent"): "Optimal alignment — benchmark clinic",
    ("Excellent","Stable"): "Strong revenue, minor labor drift",
    ("Excellent","At Risk"): "Revenue strong, labor strain emerging",
    ("Excellent","Critical"): "Revenue strong, labor crisis",
    ("Stable","Excellent"): "Lean staffing, untapped revenue potential",
    ("Stable","Stable"): "Sustainable — protect the baseline",
    ("Stable","At Risk"): "Revenue stable, labor cost creeping",
    ("Stable","Critical"): "Margin compression accelerating",
    ("At Risk","Excellent"): "Revenue leakage despite efficient staffing",
    ("At Risk","Stable"): "Front-end leakage likely",
    ("At Risk","At Risk"): "Dual drift — act fast",
    ("At Risk","Critical"): "Severe margin risk",
    ("Critical","Excellent"): "Systemic revenue capture failure",
    ("Critical","Stable"): "Profitability erosion",
    ("Critical","At Risk"): "Dual erosion",
    ("Critical","Critical"): "Systemic distress — immediate intervention required",
}

# Simple top-3 actions (replace with your full matrix later if desired)
TOP3_ACTIONS = {
    "Excellent": ["Sustain performance", "Share best practices", "Quarterly validation"],
    "Stable": ["Monthly revenue-cycle review", "Template optimization", "Recognition program"],
    "At Risk": ["Daily revenue huddle", "POS collection push", "Overtime review"],
    "Critical": ["Immediate charge-scrub", "Daily reconciliation", "12-week recovery plan"],
}

# ==============================
# Input Form
# ==============================
st.markdown("### Clinic Assessment")
with st.form("vvi_form"):
    c1, c2 = st.columns(2)
    with c1:
        visits = st.number_input("Total Visits", min_value=1, value=2400, step=100)
        net_rev = st.number_input("Net Operating Revenue ($)", min_value=0.01, value=480000.00)
    with c2:
        labor = st.number_input("Labor Expense – SWB ($)", min_value=0.01, value=312000.00)
        st.markdown("**Targets**")
        r_target = st.number_input("Target NRPV ($)", value=200.00, step=5.0)
        l_target = st.number_input("Target LCV ($)", value=130.00, step=5.0)

    submitted = st.form_submit_button("Run Assessment", type="primary", use_container_width=True)

if submitted:
    # Core calculations
    rpv = net_rev / visits
    lcv = labor / visits
    swb_pct = labor / net_rev * 100

    rf_score = (rpv / r_target) * 100
    lf_score = (l_target / lcv) * 100
    vvi_score = (rpv / lcv) / (r_target / l_target) * 100

    rf_tier = get_tier(rf_score)
    lf_tier = get_tier(lf_score)
    vvi_tier = get_tier(vvi_score)
    scenario = SCENARIO_DIAGNOSES.get((rf_tier, lf_tier), "Custom scenario")

    # Annualized opportunity
    rev_gap = max(0, r_target - rpv) * visits * 12
    labor_gap = max(0, lcv - l_target) * visits * 12
    total_opp = rev_gap + labor_gap

    # ==============================
    # Executive Dashboard
    # ==============================
    st.markdown(f"<div class='big gold'>{vvi_score:.1f}</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:1.8rem; margin-top:-10px;'>{vvi_tier} Tier</p>", unsafe_allow_html=True)

    # Half-circle gauges
    def half_gauge(score, label):
        fig, ax = plt.subplots(figsize=(4, 2.4))
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.1, 1.2)
        ax.set_axis_off()
        # background arc
        bg = plt.Circle((0,0), 1, color='#222', alpha=0.9)
        ax.add_patch(bg)
        # filled arc
        theta = 180 * min(score/100, 1)
        wedge = plt.matplotlib.patches.Wedge((0,0), 1, 180-theta, 180, color='#b08c3e', width=0.2)
        ax.add_patch(wedge)
        # text
        ax.text(0, 0.1, f"{score:.0f}%", ha='center', va='center', fontsize=28, fontweight='bold', color='white')
        ax.text(0, -0.35, label, ha='center', va='center', fontsize=11, color='#aaa')
        st.pyplot(fig, use_container_width=False)

    g1, g2 = st.columns(2)
    with g1: half_gauge(rf_score, "Revenue Factor")
    with g2: half_gauge(lf_score, "Labor Factor")

    st.markdown(f"<div class='scenario-box'><strong>Scenario:</strong> {scenario}</div>", unsafe_allow_html=True)

    # Key metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NRPV", f"${rpv:.2f}", delta=f"{rpv-r_target:+.2f}")
    m2.metric("LCV", f"${lcv:.2f}", delta=f"{lcv-l_target:+.2f}")
    m3.metric("SWB %", f"{swb_pct:.1f}%")
    m4.metric("Annual Opportunity", f"${total_opp:,.0f}")

    # Top 3 Actions
    st.markdown("### Immediate Playbook — Top 3 Actions")
    actions = TOP3_ACTIONS.get(vvi_tier, TOP3_ACTIONS["At Risk"])
    for i, action in enumerate(actions, 1):
        st.markdown(f"<h4 style='color:#b08c3e; margin:0.8rem 0;'>{i}. {action}</h4>", unsafe_allow_html=True)

    # PDF Download (clean & beautiful)
    def create_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=LETTER)
        width, height = LETTER
        c.setFillColor("#0a0a0a")
        c.rect(0, height-120, width, 120, fill=1)
        c.setFillColor("#b08c3e")
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width/2, height-80, f"VVI = {vvi_score:.1f}  |  {vvi_tier}")
        c.setFillColor("white")
        c.setFont("Helvetica", 12)
        c.drawCentredString(width/2, height-110, f"Generated {datetime.now():%b %d, %Y}")
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    st.download_button(
        label="Download Executive Summary (PDF)",
        data=create_pdf(),
        file_name=f"VVA_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

else:
    st.info("Enter clinic financials above → get instant executive intelligence.")
    st.stop()

st.markdown("---")
st.caption("Visit Value Agent 4.0 © 2025 Bramhall Consulting, LLC")
