# app.py
# Visit Value Agent 4.0 — Executive Operating System for Ambulatory Medicine™
# Bramhall Consulting | predict → perform → prosper

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import io
import base64
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ----------------------------
# Page Config & Branding
# ----------------------------
st.set_page_config(
    page_title="Visit Value Agent 4.0",
    page_icon="Scalpel",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Luxury dark theme CSS (Tesla/Starlink vibe)
st.markdown("""
<style>
    .main {background-color: #0a0a0a; color: #f5f5f5;}
    .stApp {background-color: #0a0a0a;}
    h1, h2, h3, h4 {color: #b08c3e; font-family: 'Helvetica Neue', sans-serif;}
    .gold {color: #b08c3e;}
    .big-number {font-size: 5.5rem; font-weight: 800; line-height: 1;}
    .metric-label {font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; color: #888;}
    .stButton>button {background: #b08c3e; color: black; font-weight: bold;}
    .stDownloadButton>button {background: #1e1e1e; border: 1px solid #b08c3e;}
    hr {border-color: #333;}
    .scenario-box {background: #1e1e1e; padding: 1.2rem; border-radius: 12px; border-left: 5px solid #b08c3e;}
</style>
""", unsafe_allow_html=True)

# Logo
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=180)
else:
    st.markdown("<h1 style='text-align:center; color:#b08c3e;'>Visit Value Agent 4.0</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align:center; color:#888; margin-top:-10px;'>predict → perform → prosper™</h3>", unsafe_allow_html=True)
st.markdown("---")

# ----------------------------
# Core Logic & Tiers
# ----------------------------
TIER_COLORS = {"Excellent": "#1e4d2b", "Stable": "#996f00", "At Risk": "#a03c00", "Critical": "#8b1e1e"}
BG_COLORS   = {"Excellent": "#12222", "Stable": "#2b2500", "At Risk": "#331b00", "Critical": "#331111"}

def get_tier(score):
    if score >= 100: return "Excellent"
    elif score >= 95: return "Stable"
    elif score >= 90: return "At Risk"
    else: return "Critical"

SCENARIO_DIAGNOSES = {
    ("Excellent", "Excellent"): "Optimal alignment — benchmark clinic",
    ("Excellent", "Stable"): "Strong revenue, minor labor drift",
    ("Excellent", "At Risk"): "Revenue strong, labor strain emerging",
    ("Excellent", "Critical"): "Revenue strong, labor crisis",
    ("Stable", "Excellent"): "Lean staffing, untapped revenue potential",
    ("Stable", "Stable"): "Sustainable — protect the baseline",
    ("Stable", "At Risk"): "Revenue stable, labor cost creeping",
    ("Stable", "Critical"): "Margin compression accelerating",
    ("At Risk", "Excellent"): "Revenue leakage despite efficient staffing",
    ("At Risk", "Stable"): "Front-end leakage likely",
    ("At Risk", "At Risk"): "Dual drift — act fast",
    ("At Risk", "Critical"): "Severe margin risk",
    ("Critical", "Excellent"): "Systemic revenue capture failure",
    ("Critical", "Stable"): "Profitability erosion",
    ("Critical", "At Risk"): "Dual erosion",
    ("Critical", "Critical"): "Systemic distress — immediate intervention required",
}

# ----------------------------
# Input Form
# ----------------------------
st.markdown("### Clinic Assessment")
with st.form("vvi_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        visits = st.number_input("Total Visits", min_value=1, value=2400, step=100)
        net_rev = st.number_input("Net Operating Revenue ($)", min_value=0.01, value=480000.00, format="%.2f")
    with col2:
        labor = st.number_input("Labor Expense – SWB ($)", min_value=0.01, value=312000.00, format="%.2f")
        st.markdown("**Targets (customize if known)**")
        r_target = st.number_input("Target Net Revenue per Visit ($)", value=200.00, step=5.0)
        l_target = st.number_input("Target Labor Cost per Visit ($)", value=130.00, step=5.0)

    submitted = st.form_submit_button("Run Assessment", use_container_width=True, type="primary")

if submitted:
    # Calculations
    rpv = net_rev / visits
    lcv = labor / visits
    swb_pct = labor / net_rev * 100

    rf_score = (rpv / r_target) * 100
    lf_score = (l_target / lcv) * 100
    vvi_raw = rpv / lcv
    vvi_target_ratio = r_target / l_target
    vvi_score = (vvi_raw / vvi_target_ratio) * 100

    rf_tier = get_tier(rf_score)
    lf_tier = get_tier(lf_score)
    vvi_tier = get_tier(vvi_score)

    scenario = SCENARIO_DIAGNOSES.get((rf_tier, lf_tier), "Custom scenario")

    # Opportunity
    rev_opp = max(0, (r_target - rpv) * visits * 12)  # annualized
    labor_opp = max(0, (lcv - l_target) * visits * 12)

    # ----------------------------
    # Executive Dashboard
    # ----------------------------
    st.markdown(f"<h1 class='big-number' style='text-align:center; color:{'#b08c3e'}'>{vvi_score:.1f}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:1.4rem; color:#b08c3e; margin-top:-20px;'>{vvi_tier} Tier</p>", unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig, ax = plt.subplots(figsize=(3,2))
        ax.pie([min(rf_score,100), 20), 100-min(rf_score,100) 20], colors=['#b08c3e','#222'], startangle=90, counterclock=False)
        ax.text(0,0, f"{rf_score:.0f}%", ha='center', va='center', fontsize=20, fontweight='bold', color='white')
        plt.title("Revenue Factor (RF)", color='#b08c3e', fontsize=12, pad=15)
        st.pyplot(fig)
    with col_g2:
        fig, ax = plt.subplots(figsize=(3,2))
        ax.pie([min(lf_score,100 20), 100-min(lf_score,100) 20], colors=['#b08c3e','#222'], startangle=90, counterclock=False)
        ax.text(0,0, f"{lf_score:.0f}%", ha='center', va='center', fontsize=20, fontweight='bold', color='white')
        plt.title("Labor Factor (LF)", color='#b08c3e', fontsize=12, pad=15)
        st.pyplot(fig)

    st.markdown(f"<div class='scenario-box'><strong>Scenario:</strong> {scenario}</div>", unsafe_allow_html=True)

    # Key Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NRPV", f"${rpv:.2f}", f"{rpv-r_target:+.2f} vs target")
    m2.metric("LCV", f"${lcv:.2f}", f"{lcv-l_target:+.2f} vs target")
    m3.metric("SWB %", f"{swb_pct:.1f}%")
    m4.metric("Annualized Opportunity", f"${rev_opp+labor_opp:,.0f}")

    # Prescriptive Actions (Top 3)
    st.markdown("### Immediate Playbook — Top 3 Actions")
    top3 = [
        "Launch daily 5-minute revenue huddle — focus on charge capture & chart closure",
        "Audit front-desk POS collection scripts and accountability this week",
        "Align next week’s template with actual volume using PCM logic",
    ][:3]  # placeholder — replace with your full logic later
    for i, action in enumerate(top3, 1):
        st.markdown(f"<h4 style='color:#b08c3e;'>{i}. {action}</h4>", unsafe_allow_html=True)

    # PDF Export
    def create_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=LETTER)
        width, height = LETTER
        c.setFillColor("#0a0a0a")
        c.rect(0, height-100, width, 100, fill=1)
        c.setFillColor("#b08c3e")
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height-70, f"VVI = {vvi_score:.1f} | {vvi_tier}")
        # add more content as desired
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    st.download_button(
        label="Download Executive Summary (PDF)",
        data=create_pdf(),
        file_name=f"VVA_Executive_Summary_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

    st.markdown("---")
    st.caption("Visit Value Agent 4.0 © 2025 Bramhall Consulting, LLC | All Rights Reserved")

else:
    st.info("Enter clinic data above to instantly generate the executive intelligence.")
    st.stop()
