# app.py — Visit Value Agent 4.0 (Pilot)
# Bramhall Consulting, LLC — predict. perform. prosper.

import io
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# PDF export
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ----------------------------
# Page config & branding
# ----------------------------
st.set_page_config(page_title="Visit Value Agent 4.0 (Pilot)", page_icon="🩺", layout="centered")
st.markdown("<h1 style='text-align:center;margin-bottom:0'>Visit Value Agent 4.0 — Pilot</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;margin-top:0'><em>Bramhall Consulting, LLC — predict. perform. prosper.</em></p>", unsafe_allow_html=True)
st.divider()

# ==============================
# Scenario grid helpers
# ==============================
TIER_ORDER = ["Critical", "At Risk", "Stable", "Excellent"]  # RF left→right, LF top→bottom

def tier_from_score(score: float) -> str:
    if score >= 100: return "Excellent"
    if 95 <= score <= 99: return "Stable"
    if 90 <= score <= 94: return "At Risk"
    return "Critical"

SCENARIO_MAP = {
    ("Critical", "Critical"): 1,   ("Critical", "At Risk"): 2,   ("Critical", "Stable"): 3,   ("Critical", "Excellent"): 4,
    ("At Risk", "Critical"): 5,    ("At Risk", "At Risk"): 6,    ("At Risk", "Stable"): 7,    ("At Risk", "Excellent"): 8,
    ("Stable", "Critical"): 9,     ("Stable", "At Risk"): 10,    ("Stable", "Stable"): 11,    ("Stable", "Excellent"): 12,
    ("Excellent", "Critical"): 13, ("Excellent", "At Risk"): 14, ("Excellent", "Stable"): 15, ("Excellent", "Excellent"): 16,
}

def scenario_name(rf_t: str, lf_t: str) -> str:
    rev_map = {"Excellent": "High Revenue", "Stable": "Stable Revenue", "At Risk": "Low Revenue", "Critical": "Critical Revenue"}
    lab_map = {"Excellent": "Efficient Labor", "Stable": "Stable Labor", "At Risk": "At-Risk Labor", "Critical": "Critical Labor"}
    return f"{rev_map[rf_t]} / {lab_map[lf_t]}"

def build_scenario_grid(active_rf_tier: str, active_lf_tier: str):
    rf_cols = TIER_ORDER
    lf_rows = TIER_ORDER
    data = []
    for lf in lf_rows:
        row = []
        for rf in rf_cols:
            row.append(SCENARIO_MAP[(lf, rf)])
        data.append(row)
    df = pd.DataFrame(data, index=[f"LF: {r}" for r in lf_rows], columns=[f"RF: {c}" for c in rf_cols])

    def highlight_active(val, row_idx, col_idx):
        lf_here = lf_rows[row_idx]; rf_here = rf_cols[col_idx]
        if (lf_here == active_lf_tier) and (rf_here == active_rf_tier):
            return "background-color: #fdd835; color: #000; font-weight: 700;"
        return ""

    styler = df.style.format(precision=0)
    for r in range(len(lf_rows)):
        for c in range(len(rf_cols)):
            styler = styler.set_properties(subset=(df.index[r], df.columns[c]),
                                           **{"text-align": "center", "font-weight": "500"})
            styler = styler.apply(lambda s, r=r, c=c: [highlight_active(v, r, c) for v in s], axis=1,
                                  subset=(df.index[r], df.columns[c]))
    styler = (styler
              .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
              .hide(axis="index", level=None))
    return df, styler

def format_money(x: float) -> str:
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

def tier(score: float) -> str:
    if score >= 100: return "Excellent"
    if 95 <= score <= 99: return "Stable"
    if 90 <= score <= 94: return "At Risk"
    return "Critical"

def pos_should_be_top3(rpv_gap: float, avg_copay: float = 30.0, copay_eligibility: float = 0.5, leakage_rate: float = 0.25) -> bool:
    lift = avg_copay * copay_eligibility * leakage_rate
    return lift >= rpv_gap

# ------------------------------------------------------
# Scenario-specific prescriptive logic
# ------------------------------------------------------
def prescriptive_actions(rf_t: str, lf_t: str, rpv_gap: float):
    """Returns dict with diagnosis, top3, extended, huddle_script, daily_patch."""
    diag = scenario_name(rf_t, lf_t)

    top3 = []
    ext = []

    # Revenue levers
    if rf_t in ("Critical", "At Risk", "Stable") and rpv_gap > 0:
        top3 += [
            "Increase revenue density: prioritize higher-acuity visit types and coding accuracy.",
            "Tighten documentation quality (provider coaching + targeted audits).",
            "Add capacity at peak hours to capture higher-value demand."
        ]
    # Labor levers
    if lf_t in ("Critical", "At Risk"):
        top3 += [
            "Align staffing to the demand curve (templates & throughput fixes).",
            "Reduce avoidable OT / premium coverage with scheduling discipline.",
            "Speed chart closure / cycle-time to improve throughput."
        ]
    if not top3:
        top3 = [
            "Sustain revenue integrity (quarterly audits).",
            "Sustain labor efficiency (periodic productivity checks).",
            "Share best practices across sites; maintain cycle-time discipline."
        ]

    # POS patch
    if rf_t in ("Critical", "At Risk", "Stable"):
        if pos_should_be_top3(rpv_gap):
            top3.append("Run POS co-pay capture push (scripts, training, accountability).")
        else:
            ext.append("Quick POS audit (co-pay scripts, training, ClearPay accountability).")

    # Huddle + SWB messaging
    huddle = (
        "5-Minute Morning Huddle:\n"
        "• Today’s priorities: Top 3 levers above\n"
        "• Throughput focus: door-to-room < 10 min; room-to-provider < 15 min\n"
        "• Reliability: close charts same day; handoffs clear; escalate bottlenecks early"
    )
    daily_patch = "Daily reminder: review Top 3, confirm staffing vs demand, call out risks, recognize wins."

    ext.append("Daily 5-minute morning huddle: review Top 3 levers, VPDA drivers, risks.")
    ext.append("Treat SWB% as context only; anchor decisions in VVI (RPV/LPV, RF/LF).")

    return {
        "diagnosis": diag,
        "top3": top3[:3],
        "extended": ext,
        "huddle_script": huddle,
        "daily_patch": daily_patch
    }

# ----------------------------
# Session state
# ----------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "runs" not in st.session_state:
    st.session_state.runs = []  # list of dicts (name + results)

def next_step(): st.session_state.step += 1
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
        "4) a Shiny-style KPI bar chart, and 5) a print-ready Executive Summary/PDF."
    )

# ----------------------------
# Input Flow
# ----------------------------
st.markdown("### Start VVI Assessment")
if st.session_state.step == 1:
    visits = st.number_input("How many total patient visits occurred during this time period?",
                             min_value=1, step=1, key="visits_input")
    st.button("Next", disabled=visits <= 0, on_click=lambda: (
        st.session_state.answers.update({"visits": int(visits)}), next_step()
    ))
elif st.session_state.step == 2:
    net_rev = st.number_input("What was the total net revenue collected? ($)",
                              min_value=0.01, step=100.0, format="%.2f", key="net_rev_input")
    st.button("Next", disabled=net_rev <= 0, on_click=lambda: (
        st.session_state.answers.update({"net_revenue": float(net_rev)}), next_step()
    ))
elif st.session_state.step == 3:
    labor_cost = st.number_input("Total labor cost ($) (W2 + PRN + OT + contract/locum)",
                                 min_value=0.01, step=100.0, format="%.2f", key="labor_cost_input")
    st.button("Next", disabled=labor_cost <= 0, on_click=lambda: (
        st.session_state.answers.update({"labor_cost": float(labor_cost)}), next_step()
    ))
elif st.session_state.step == 4:
    period = st.selectbox("What time period does this represent?", ["Week", "Month", "Quarter", "Year"],
                          key="period_input")
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"period": period}), next_step()
    ))
elif st.session_state.step == 5:
    focus = st.selectbox("Optional: Focus area", ["All areas", "Revenue improvement", "Staffing efficiency",
                                                  "Patient flow", "Burnout", "None"], key="focus_input")
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"focus": focus}), next_step()
    ))
elif st.session_state.step == 6:
    r_target = st.number_input("Revenue target per visit (default $140)",
                               min_value=1.0, value=140.0, step=1.0, format="%.2f", key="rev_target_input")
    st.button("Next", on_click=lambda: (
        st.session_state.answers.update({"rev_target": float(r_target)}), next_step()
    ))
elif st.session_state.step == 7:
    l_target = st.number_input("Labor target per visit (default $85)",
                               min_value=1.0, value=85.0, step=1.0, format="%.2f", key="lab_target_input")
    st.button("Run Assessment", on_click=lambda: (
        st.session_state.answers.update({"lab_target": float(l_target)}), next_step()
    ))

# ----------------------------
# Results
# ----------------------------
if st.session_state.step >= 8:
    a = st.session_state.answers
    visits  = float(a.get("visits", 0))
    net_rev = float(a.get("net_revenue", 0.0))
    labor   = float(a.get("labor_cost", 0.0))
    period  = a.get("period", "-")
    focus   = a.get("focus", "All areas")
    rt      = float(a.get("rev_target", 140.0))
    lt      = float(a.get("lab_target", 85.0))

    if visits <= 0 or net_rev <= 0 or labor <= 0:
        st.warning("Please enter non-zero values for visits, net revenue, and labor cost, then run again.")
        st.stop()

    # Core metrics
    rpv = net_rev / visits
    lpv = labor / visits
    swb_pct = labor / net_rev

    # White Paper factors (RF, LF)
    rf_raw = (rpv / rt) if rt else 0.0
    lf_raw = (lt / lpv) if lpv else 0.0
    rf_score = round(rf_raw * 100, 2)
    lf_score = round(lf_raw * 100, 2)
    rf_t = tier(rf_score)
    lf_t = tier(lf_score)

    # VVI (raw) and normalized to 0–100 for charting (=100*RF_raw*LF_raw)
    vvi_raw = (rpv / lpv) if lpv else 0.0
    vvi_score = round(100 * rf_raw * lf_raw, 2)
    vvi_t = tier(vvi_score)

    rpv_gap = max(0.0, rt - rpv)
    scenario = scenario_name(rf_t, lf_t)

    st.success("Assessment complete. See results below.")

    # ---------- Optional Visit-Type Mix input & impact ----------
    with st.expander("Optional: Visit-Type Mix (impact on RF)", expanded=False):
        st.caption("Enter rough %-mix (numbers don’t need to total 100%). We’ll show estimated RF impact (not applied to core scores).")
        c1, c2, c3 = st.columns(3)
        lvl3  = c1.number_input("% Level 3", min_value=0.0, value=40.0, step=1.0)
        lvl4  = c2.number_input("% Level 4", min_value=0.0, value=35.0, step=1.0)
        occ   = c3.number_input("% Occ Health", min_value=0.0, value=10.0, step=1.0)
        c4, c5, c6 = st.columns(3)
        proc  = c4.number_input("% Procedure", min_value=0.0, value=5.0, step=1.0)
        dot   = c5.number_input("% DOT", min_value=0.0, value=5.0, step=1.0)
        vacc  = c6.number_input("% Vaccine", min_value=0.0, value=5.0, step=1.0)

        # simple weights (tune as wanted)
        weights = {
            "Level 3": 0.95, "Level 4": 1.08, "Occ Health": 1.02,
            "Procedure": 1.15, "DOT": 1.00, "Vaccine": 0.90
        }
        mix = {"Level 3": lvl3, "Level 4": lvl4, "Occ Health": occ, "Procedure": proc, "DOT": dot, "Vaccine": vacc}
        total = sum(mix.values()) or 1.0
        uplift = sum((mix[k]/total) * weights[k] for k in mix)
        est_rpv = rpv * uplift
        est_rf  = (est_rpv / rt) * 100
        st.write(f"Estimated RPV with mix: **{format_money(est_rpv)}** → Estimated RF: **{est_rf:.1f}**")
        figm, axm = plt.subplots(figsize=(5,1.8))
        axm.barh(["Current RF","Mix Est. RF"], [rf_score, est_rf], height=0.5, color=["#2e2e2e","#004b23"])
        axm.set_xlim(0, max(120, est_rf+10, rf_score+10)); axm.set_xlabel("Score")
        for v,bar in zip([rf_score, est_rf], axm.patches):
            axm.text(v+1, bar.get_y()+bar.get_height()/2, f"{v:.1f}", va="center")
        axm.grid(False); axm.spines["top"].set_visible(False); axm.spines["right"].set_visible(False)
        st.pyplot(figm)

    # ---------- KPI bars ----------
    def render_kpi_bars(vvi_score: float, rf_score: float, lf_score: float):
        labels = ["VVI (normalized 0–100)", "Revenue Factor", "Labor Factor"]
        values = [vvi_score, rf_score, lf_score]
        x_max = max(120, max(values) + 15)

        fig, ax = plt.subplots(figsize=(8.5, 2.8))
        bands = [(0,90,"#d9534f"), (90,95,"#f0ad4e"), (95,100,"#ffd666"), (100,x_max,"#5cb85c")]
        for s,e,c in bands: ax.axvspan(s,e,color=c,alpha=0.15,lw=0)
        bars = ax.barh(labels, values, color="#2e2e2e", height=0.55)
        for bar, v in zip(bars, values):
            ax.text(v + (x_max * 0.01), bar.get_y() + bar.get_height()/2, f"{v:.2f}", va="center", ha="left", fontsize=10)
        ax.set_xlim(0, x_max); ax.set_xlabel("Score"); ax.set_ylabel(""); ax.grid(False, axis="y")
        ax.spines["right"].set_visible(False); ax.spines["top"].set_visible(False); ax.spines["left"].set_visible(False)
        st.subheader("Key Metrics & Scores (Shiny-style)")
        st.pyplot(fig)
        return fig

    kpi_fig = render_kpi_bars(vvi_score, rf_score, lf_score)

    # ---------- Calculation table ----------
    calc_df = pd.DataFrame({
        "Metric": [
            "Total visits","Net revenue collected","Total labor cost","Revenue per visit (RPV)",
            "Labor cost per visit (LPV)","Revenue benchmark target","Labor benchmark target",
            "Labor cost as % of revenue (SWB%)","Revenue score (RF)","Labor score (LF)",
            "VVI (value per $ labor)","VVI score (normalized 0–100)","Scenario"
        ],
        "Value": [
            f"{int(visits):,}", format_money(net_rev), format_money(labor), format_money(rpv),
            format_money(lpv), format_money(rt), format_money(lt),
            f"{swb_pct*100:.1f}%", f"{rf_score} ({rf_t})", f"{lf_score} ({lf_t})",
            f"{vvi_raw:.3f}", f"{vvi_score} ({vvi_t})", scenario
        ],
    })
    st.subheader("Calculation Table")
    st.dataframe(calc_df, use_container_width=True, hide_index=True)

    # ---------- Scoring table ----------
    score_df = pd.DataFrame({
        "Index": ["Revenue Factor (RF)", "Labor Factor (LF)", "Visit Value Index (VVI)"],
        "Formula": ["RPV ÷ Target RPV", "Target LPV ÷ LPV", "RPV ÷ LPV  (normalized = 100 × RF_raw × LF_raw)"],
        "Raw Value": [f"{rf_raw:.3f}", f"{lf_raw:.3f}", f"{vvi_raw:.3f}"],
        "Weighted Score (0–100)": [f"{rf_score:.2f}", f"{lf_score:.2f}", f"{vvi_score:.2f}"],
        "Tier": [rf_t, lf_t, vvi_t],
    })
    st.subheader("VVI / RF / LF Scoring Table")
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    # ---------- Scenario Grid ----------
    st.subheader("📊 VVI 16-Scenario Grid")
    df_grid, styler = build_scenario_grid(rf_t, lf_t)
    st.dataframe(styler, use_container_width=True)

    # ---------- Prescriptive output ----------
    actions = prescriptive_actions(rf_t, lf_t, rpv_gap)
    st.subheader("Scenario")
    st.write(f"**{actions['diagnosis']}** — period: **{period}**. Focus: **{focus}**.")
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

    # ---------- AI Insights Panel ----------
    with st.expander("AI Insights Summary", expanded=True):
        bullets = []
        if rf_score < 95:
            if rpv_gap > 0:
                bullets.append(f"Revenue density suppressed by ~{format_money(rpv_gap)} per visit; focus on coding mix & acuity.")
            else:
                bullets.append("Revenue below target but gap isn’t explained by per-visit density — check payer yield/denials.")
        if lf_score < 95:
            bullets.append("Labor efficiency suggests throughput constraints or schedule misalignment.")
        if vvi_score < 95 and rf_score >= 95 and lf_score >= 95:
            bullets.append("Overall value suppressed by reliability variance; protect flow and chart closure.")
        if not bullets:
            bullets.append("Performance balanced; sustain best practices and standardize across sites.")
        for b in bullets: st.write(f"• {b}")

    # ---------- Print-ready PDF export ----------
    def make_pdf_buffer():
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=LETTER)
        w, h = LETTER

        # Header (black & gold)
        c.setFillColor(colors.black); c.rect(0, h-60, w, 60, fill=1, stroke=0)
        c.setFillColorRGB(0.48, 0.39, 0.0)  # gold-ish
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, h-40, "Visit Value Agent 4.0 — Executive Summary")
        c.setFillColor(colors.white); c.setFont("Helvetica", 10)
        c.drawRightString(w-40, h-40, "Bramhall Consulting, LLC — predict. perform. prosper.")

        y = h-90
        def line(lbl, val):
            nonlocal y
            c.setFont("Helvetica-Bold", 11); c.setFillColor(colors.black); c.drawString(40, y, lbl)
            c.setFont("Helvetica", 11); c.drawString(200, y, val); y -= 16

        line("Period:", period)
        line("Focus:", str(focus))
        line("Scenario:", actions["diagnosis"])
        line("RF / LF:", f"{rf_score:.2f} ({rf_t})  |  {lf_score:.2f} ({lf_t})")
        line("RPV / LPV / SWB%:", f"{format_money(rpv)}  |  {format_money(lpv)}  |  {swb_pct*100:.1f}%")
        y -= 6

        c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Top 3 Actions"); y -= 14
        c.setFont("Helvetica", 11)
        for i,t3 in enumerate(actions["top3"], start=1):
            c.drawString(50, y, f"{i}) {t3}"); y -= 14

        y -= 6; c.setFont("Helvetica-Bold", 12); c.drawString(40, y, "Extended Actions"); y -= 14
        c.setFont("Helvetica", 11)
        for ex in actions["extended"]:
            c.drawString(50, y, f"• {ex}"); y -= 14
            if y < 140:
                c.showPage(); y = h-80

        # Embed KPI chart
        img_buf = io.BytesIO()
        kpi_fig.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
        img_buf.seek(0)
        c.drawImage(img_buf, 40, 80, width=w-80, height=180, preserveAspectRatio=True, mask='auto')

        # Footer
        c.setFont("Helvetica-Oblique", 9); c.setFillColor(colors.grey)
        c.drawRightString(w-40, 40, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  •  VVA 4.0 (Pilot)")
        c.save(); buf.seek(0)
        return buf

    st.download_button("Download Executive Summary (PDF)", data=make_pdf_buffer(),
                       file_name="VVA_Executive_Summary.pdf", mime="application/pdf")

    # ---------- Save run & compare ----------
    st.subheader("Save this run")
    default_name = f"Clinic {len(st.session_state.runs)+1}"
    run_name = st.text_input("Name this clinic/run:", value=default_name)
    if st.button("Save to portfolio"):
        st.session_state.runs.append({
            "name": run_name,
            "period": period,
            "focus": focus,
            "RF": rf_score, "LF": lf_score, "VVI": vvi_score,
            "scenario": actions["diagnosis"]
        })
        st.success(f"Saved: {run_name}")

    if st.session_state.runs:
        st.subheader("Portfolio (compare clinics)")
        comp = pd.DataFrame(st.session_state.runs)
        st.dataframe(comp, use_container_width=True, hide_index=True)

    st.divider()
    if st.button("Start a New Assessment"):
        reset()

