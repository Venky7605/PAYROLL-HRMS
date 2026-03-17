from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from company_config import (
    AGE_CATEGORIES,
    COMPANY_CONFIG,
    EMPLOYER_TYPE_OPTIONS,
    FINANCIAL_YEARS,
    FOOTER_NOTES,
    PF_OPTIONS,
    REGIMES,
    SOURCE_URLS,
)
from deductions_guide import (
    SALARY_EXEMPTIONS,
    CHAPTER_VIA_DEDUCTIONS,
    HOUSE_PROPERTY_DEDUCTIONS,
    NEW_REGIME_AVAILABLE,
    NEW_REGIME_SLABS_INFO,
    OLD_REGIME_SLABS_INFO,
    SURCHARGE_INFO,
    CESS_INFO,
)
from export_utils import build_export_workbook
from tax_engine import (
    CalculatorInputs,
    annual_breakup_frame,
    calculate_both_regimes,
    comparison_table,
    financial_year_bounds,
    recommended_regime,
    tax_optimizer,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=COMPANY_CONFIG.app_title,
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Premium CSS
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

* { font-family: 'Inter', sans-serif !important; }

:root {
    --navy:   #0f2444;
    --blue1:  #1e3a8a;
    --blue2:  #2563eb;
    --emerald:#059669;
    --amber:  #d97706;
    --red:    #dc2626;
    --bg:     #f1f5f9;
    --card:   #ffffff;
    --border: #e2e8f0;
    --muted:  #64748b;
    --dark:   #0f172a;
}

.stApp { background: linear-gradient(160deg,#f0f7ff 0%,#e8f0fe 30%,#f1f5f9 100%) !important; }

.block-container { padding-top: 0.8rem !important; padding-bottom: 2rem !important; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0f2444 0%, #1e3a8a 55%, #1d4ed8 100%);
    border-radius: 20px;
    padding: 1.6rem 2rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 20px 60px rgba(15,36,68,.22);
    position: relative; overflow: hidden;
}
.hero::after {
    content:''; position:absolute; top:-60px; right:-60px;
    width:260px; height:260px;
    background:radial-gradient(circle,rgba(255,255,255,.07) 0%,transparent 70%);
    border-radius:50%;
}
.hero-title { font-size:1.85rem; font-weight:800; color:#fff; margin:0; letter-spacing:-.02em; }
.hero-sub   { color:rgba(255,255,255,.75); font-size:.95rem; margin-top:.35rem; }
.chip {
    display:inline-block; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18);
    color:#fff; padding:.28rem .7rem; border-radius:999px; font-size:.78rem; margin:.5rem .35rem 0 0;
    font-weight:500;
}
.chip.green  { background:rgba(5,150,105,.25); border-color:rgba(5,150,105,.4); }
.chip.amber  { background:rgba(217,119,6,.25); border-color:rgba(217,119,6,.4); }
.chip.white  { background:rgba(255,255,255,.18); border-color:rgba(255,255,255,.3); }

/* ── Metric cards ── */
.mcard {
    background:#fff; border-radius:16px; padding:1.15rem 1.2rem;
    border:1px solid #e2e8f0;
    box-shadow:0 4px 24px rgba(15,36,68,.06);
    transition: transform .2s, box-shadow .2s;
}
.mcard:hover { transform:translateY(-2px); box-shadow:0 8px 32px rgba(15,36,68,.1); }
.mcard-label { color:#64748b; font-size:.82rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em; }
.mcard-value { font-size:1.65rem; font-weight:800; color:#0f172a; margin:.2rem 0; }
.mcard-sub   { font-size:.82rem; color:#64748b; }
.mcard-badge { display:inline-block; padding:.18rem .55rem; border-radius:6px; font-size:.75rem; font-weight:700; margin-top:.4rem; }
.badge-green { background:#dcfce7; color:#166534; }
.badge-red   { background:#fee2e2; color:#991b1b; }
.badge-blue  { background:#dbeafe; color:#1e40af; }
.badge-amber { background:#fef3c7; color:#92400e; }

/* ── Reco box ── */
.reco-box {
    background:linear-gradient(90deg,rgba(37,99,235,.06),rgba(5,150,105,.06));
    border-left:5px solid #2563eb; border-radius:12px;
    padding:.9rem 1rem; margin:.6rem 0 1rem;
}
.reco-text { font-size:.9rem; color:#1e293b; line-height:1.6; }

/* ── Section header ── */
.sec-hdr {
    background:linear-gradient(90deg,#1e3a8a,#2563eb);
    color:#fff; padding:.55rem 1rem; border-radius:10px;
    font-size:.95rem; font-weight:700; margin:1rem 0 .6rem;
    letter-spacing:.02em;
}

/* ── Deduction card ── */
.ded-card {
    background:#fff; border-radius:12px; padding:1rem 1.1rem;
    border:1px solid #e2e8f0; margin-bottom:.7rem;
    box-shadow:0 2px 12px rgba(15,36,68,.04);
}
.ded-card-title { font-weight:700; color:#1e3a8a; font-size:.95rem; }
.ded-card-section { color:#2563eb; font-size:.8rem; font-weight:600; }
.ded-limit { color:#059669; font-weight:700; font-size:.88rem; }
.ded-note { color:#64748b; font-size:.82rem; margin-top:.35rem; }
.regime-tag {
    display:inline-block; padding:.12rem .45rem; border-radius:5px;
    font-size:.72rem; font-weight:700; margin-right:.25rem;
}
.tag-old { background:#fef3c7; color:#92400e; }
.tag-new { background:#dcfce7; color:#166534; }
.tag-both { background:#dbeafe; color:#1e40af; }

/* ── Compare year cards ── */
.yr-card {
    background:#fff; border-radius:16px; padding:1.2rem 1.3rem;
    border:2px solid #e2e8f0;
    box-shadow:0 4px 20px rgba(15,36,68,.06);
}
.yr-card.active { border-color:#2563eb; box-shadow:0 8px 32px rgba(37,99,235,.12); }
.yr-title { font-size:1rem; font-weight:800; color:#1e3a8a; }
.yr-amt { font-size:1.5rem; font-weight:800; color:#0f172a; }

/* ── Optimizer card ── */
.opt-high  { border-left:4px solid #dc2626; background:#fff5f5; }
.opt-medium{ border-left:4px solid #d97706; background:#fffbeb; }
.opt-low   { border-left:4px solid #059669; background:#f0fdf4; }
.opt-card  { border-radius:12px; padding:.9rem 1rem; margin-bottom:.6rem; }
.opt-title { font-weight:700; font-size:.92rem; color:#1e293b; }
.opt-desc  { font-size:.84rem; color:#475569; margin-top:.3rem; }
.opt-saving{ font-weight:800; color:#059669; }

/* ── Payslip ── */
.payslip {
    background:#fff; border:1px solid #cbd5e1; border-radius:16px;
    padding:1.5rem; max-width:700px; margin:0 auto;
    box-shadow:0 4px 24px rgba(15,36,68,.08);
    font-size:.88rem;
}
.payslip-header { background:linear-gradient(135deg,#0f2444,#1e3a8a); border-radius:10px; padding:1.1rem 1.4rem; color:#fff; margin-bottom:1rem; }
.payslip-row { display:flex; justify-content:space-between; padding:.35rem 0; border-bottom:1px solid #f1f5f9; }
.payslip-total { font-weight:800; font-size:.95rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#f8faff 0%,#eef3ff 100%) !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
    color:#1e3a8a !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:#fff; border-radius:12px; padding:.3rem .4rem;
    border:1px solid #e2e8f0; box-shadow:0 2px 8px rgba(15,36,68,.04);
    gap:.2rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius:8px; padding:.5rem .9rem !important;
    font-weight:600 !important; font-size:.85rem !important;
    color:#475569 !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;
    color:#fff !important;
}

/* ── Tables ── */
.stDataFrame { border-radius:12px !important; overflow:hidden; }

/* ── Download buttons ── */
.stDownloadButton button {
    background:linear-gradient(135deg,#1e3a8a,#2563eb) !important;
    color:#fff !important; border:none !important; border-radius:10px !important;
    font-weight:700 !important; padding:.55rem 1.2rem !important;
}
.stDownloadButton button:hover {
    background:linear-gradient(135deg,#1e40af,#3b82f6) !important;
    transform:translateY(-1px); box-shadow:0 6px 20px rgba(37,99,235,.3) !important;
}

/* ── Progress bars ── */
.prog-wrap { background:#e2e8f0; border-radius:999px; height:8px; overflow:hidden; margin:.35rem 0; }
.prog-bar  { height:100%; border-radius:999px; transition:width .5s ease; }
.prog-blue { background:linear-gradient(90deg,#2563eb,#60a5fa); }
.prog-green{ background:linear-gradient(90deg,#059669,#34d399); }
.prog-red  { background:linear-gradient(90deg,#dc2626,#f87171); }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def inr(value: float, decimals: int = 0) -> str:
    sign = "-" if value < 0 else ""
    v = abs(float(value))
    formatted = f"{v:.{decimals}f}"
    whole, _, frac = formatted.partition(".")
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        chunks = []
        while len(rest) > 2:
            chunks.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            chunks.insert(0, rest)
        whole = ",".join(chunks + [last3])
    result = f"₹{sign}{whole}"
    if decimals > 0:
        result += f".{frac}"
    return result


CURRENCY_COLS = {
    "Basic","HRA","LTA","Periodicals & Journals","Telephone & Internet","Special Allowance",
    "Gross Salary","Employer PF","Employee PF","Professional Tax","HRA Exemption",
    "Total CTC","Phone Exemption","LTA Exemption","Periodicals Exemption","Salary Exemptions",
    "TDS","Take Home Before TDS","Net Take Home","Amount","CTC Paid in FY",
    "Standard Deduction","Chapter VIA Deductions","Taxable Income","Annual Tax",
    "Annual Take Home","Avg Monthly Take Home",
}


def style_df(df: pd.DataFrame):
    fmts = {}
    for col in df.columns:
        if col in CURRENCY_COLS:
            fmts[col] = lambda x: inr(x, 0) if pd.notnull(x) else ""
        elif col == "Employment Factor":
            fmts[col] = lambda x: f"{x:.4f}" if pd.notnull(x) else ""
    return df.style.format(fmts)


def progress_html(pct: float, color_class: str = "prog-blue") -> str:
    w = min(max(pct, 0), 100)
    return f'<div class="prog-wrap"><div class="prog-bar {color_class}" style="width:{w}%"></div></div>'


def metric_card(label: str, value: str, sub: str = "", badge: str = "", badge_class: str = "badge-blue") -> None:
    badge_html = f'<div class="mcard-badge {badge_class}">{badge}</div>' if badge else ""
    st.markdown(
        f"""<div class="mcard">
            <div class="mcard-label">{label}</div>
            <div class="mcard-value">{value}</div>
            <div class="mcard-sub">{sub}</div>
            {badge_html}
        </div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def build_sidebar():
    with st.sidebar:
        st.markdown('<h1 style="font-size:1.2rem;font-weight:800;color:#1e3a8a;margin-bottom:.3rem;">⚙️ Calculator Inputs</h1>', unsafe_allow_html=True)

        # ── Employee Profile ──────────────────────────────────────────────────
        with st.expander("👤 Employee Profile", expanded=True):
            emp_name = st.text_input("Employee Name", placeholder="Enter your name")
            emp_id   = st.text_input("Employee ID", placeholder="EMP-0001")
            dept     = st.text_input("Department", placeholder="Engineering / Finance")
            desig    = st.text_input("Designation", placeholder="Software Engineer")

        # ── Salary & FY ───────────────────────────────────────────────────────
        with st.expander("💰 Salary & Financial Year", expanded=True):
            financial_year = st.selectbox("Financial Year", FINANCIAL_YEARS, index=0)
            fy_start, fy_end = financial_year_bounds(financial_year)

            annual_ctc = st.number_input(
                "Annualized CTC (₹)", min_value=0.0, value=1_200_000.0,
                step=50_000.0, format="%.0f",
                help="Total Cost to Company per year including employer PF."
            )
            join_date = st.date_input(
                "Date of Joining",
                value=fy_start,
                min_value=date(fy_start.year - 3, 1, 1),
                max_value=date(fy_end.year + 1, 12, 31),
            )
            pf_label  = st.selectbox("Provident Fund Option", list(PF_OPTIONS.values()), index=0)
            pf_option = {v: k for k, v in PF_OPTIONS.items()}[pf_label]

            age_label    = st.selectbox("Age Category", list(AGE_CATEGORIES.values()), index=0)
            age_category = {v: k for k, v in AGE_CATEGORIES.items()}[age_label]

        # ── Regime ────────────────────────────────────────────────────────────
        with st.expander("📊 Tax Regime", expanded=True):
            regime_label = st.radio(
                "Selected Regime for Take-Home View",
                list(REGIMES.values()), index=1,
                help="New Tax Regime is the default from FY 2023-24."
            )
            selected_regime_key = {v: k for k, v in REGIMES.items()}[regime_label]

        # ── HRA & Reimbursements ──────────────────────────────────────────────
        with st.expander("🏠 HRA & Reimbursements", expanded=False):
            monthly_rent = st.number_input("Monthly Rent Paid (₹)", min_value=0.0, value=0.0, step=1000.0)
            metro_city   = st.checkbox("Metro city (Delhi/Mumbai/Chennai/Kolkata)", value=False)
            phone_claim  = st.number_input(
                "Annual Telephone & Internet Bills (₹)", min_value=0.0, value=24_000.0, step=1_000.0,
                help="Capped to component in salary slip."
            )
            lta_claim         = st.number_input("LTA Claim (₹) — Old Regime", min_value=0.0, value=0.0, step=1_000.0)
            periodicals_claim = st.number_input("Periodicals & Journals Claim (₹) — Old Regime", min_value=0.0, value=0.0, step=500.0)

        # ── Old Regime Deductions ─────────────────────────────────────────────
        with st.expander("🧾 Old Regime — Chapter VI-A Deductions", expanded=False):
            st.caption("These inputs only affect Old Tax Regime computation.")
            other_80c     = st.number_input("Other 80C Investments (₹)\n(excl. Employee PF — ELSS / PPF / NSC / LIC etc.)", min_value=0.0, value=0.0, step=5_000.0)
            nps_80ccd_1b  = st.number_input("Additional NPS u/s 80CCD(1B) (₹) — max ₹50,000", min_value=0.0, value=0.0, step=5_000.0, max_value=50_000.0)
            st.markdown("**Employer NPS (80CCD(2)) — available in BOTH regimes**")
            employer_type_label = st.selectbox("Employer Type", list(EMPLOYER_TYPE_OPTIONS.values()), index=0)
            is_govt = {v: k for k, v in EMPLOYER_TYPE_OPTIONS.items()}[employer_type_label] == "govt"
            employer_nps_pct = st.slider("Employer NPS contribution (% of Basic)", 0.0, 14.0, 0.0, step=0.5)

            st.markdown("**Section 80D — Health Insurance**")
            medical_self   = st.number_input("Health Insurance — Self & Family (₹)", min_value=0.0, value=0.0, step=1_000.0)
            medical_parents= st.number_input("Health Insurance — Parents (₹)", min_value=0.0, value=0.0, step=1_000.0)
            parents_senior = st.checkbox("Parents are Senior Citizens (60+)", value=False)

            medical_80ddb  = st.number_input("Specified Disease Treatment u/s 80DDB (₹)", min_value=0.0, value=0.0, step=1_000.0)

            education_loan = st.number_input("Education Loan Interest u/s 80E (₹)", min_value=0.0, value=0.0, step=1_000.0)
            home_loan_24b  = st.number_input("Self-Occupied Home Loan Interest Sec 24(b) (₹) — max ₹2L", min_value=0.0, value=0.0, step=10_000.0)
            home_loan_80eea= st.number_input("Affordable Housing Loan Interest u/s 80EEA (₹) — max ₹1.5L", min_value=0.0, value=0.0, step=10_000.0)

            savings_80tta  = st.number_input("Savings Bank Interest u/s 80TTA (₹) — max ₹10,000 (if below 60)", min_value=0.0, value=0.0, step=1_000.0)
            savings_80ttb  = st.number_input("Senior Citizen Interest u/s 80TTB (₹) — max ₹50,000 (if 60+)", min_value=0.0, value=0.0, step=1_000.0)

            eligible_80g   = st.number_input("Donations u/s 80G (eligible amount) (₹)", min_value=0.0, value=0.0, step=1_000.0)

            st.markdown("**Disability Deductions**")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                self_disabled = st.checkbox("Self Disability (80U)")
            with col_d2:
                self_dis_severe = st.checkbox("Severe (80%+)", key="self_dis_severe")
            med_80dd = st.number_input("Disabled Dependent Deduction (80DD) — enter 1 if claiming", min_value=0.0, max_value=1.0, value=0.0)
            dis_severe_dd = st.checkbox("Severe Disability — Dependent (80%+)", key="dis_severe_dd")

        # ── Other Income ──────────────────────────────────────────────────────
        with st.expander("📈 Other Income", expanded=False):
            other_income = st.number_input(
                "Other Taxable Income (₹)\n(Interest, dividends, other income at slab rates)",
                value=0.0, step=10_000.0,
            )

    inputs = CalculatorInputs(
        financial_year=financial_year,
        annual_ctc=annual_ctc,
        join_date=join_date,
        pf_option=pf_option,
        age_category=age_category,
        monthly_rent=monthly_rent,
        metro_city=metro_city,
        phone_internet_claim=phone_claim,
        lta_claim=lta_claim,
        periodicals_claim=periodicals_claim,
        other_80c_investments=other_80c,
        nps_80ccd_1b=nps_80ccd_1b,
        employer_nps_pct=employer_nps_pct,
        is_govt_employer=is_govt,
        medical_80d_self=medical_self,
        medical_80d_parents=medical_parents,
        parents_senior_citizen=parents_senior,
        medical_80ddb=medical_80ddb,
        education_loan_80e=education_loan,
        home_loan_interest_self_occupied=home_loan_24b,
        home_loan_interest_80eea=home_loan_80eea,
        savings_interest_80tta=savings_80tta,
        savings_interest_80ttb=savings_80ttb,
        eligible_80g=eligible_80g,
        self_disability_80u=self_disabled,
        self_disability_severe=self_dis_severe,
        medical_80dd=med_80dd,
        disability_severe_80dd=dis_severe_dd,
        other_income=other_income,
        resident_individual=True,
    )
    profile = {"name": emp_name, "id": emp_id, "dept": dept, "desig": desig}
    return inputs, selected_regime_key, profile


# ─────────────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────────────

CHART_TEMPLATE = dict(
    template="plotly_white",
    font=dict(family="Inter, sans-serif", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=45, b=10),
)

COLORS = {
    "navy": "#1e3a8a", "blue": "#2563eb", "light_blue": "#93c5fd",
    "emerald": "#059669", "green": "#22c55e", "amber": "#d97706",
    "red": "#dc2626", "purple": "#7c3aed", "slate": "#64748b",
}


def chart_regime_comparison(results) -> go.Figure:
    labels = [r.regime_label for r in results.values()]
    tax_vals = [r.annual_tax for r in results.values()]
    th_vals  = [r.annual_take_home_after_tds for r in results.values()]
    bar_colors = [COLORS["red"], COLORS["amber"]]
    th_colors  = [COLORS["emerald"], COLORS["blue"]]
    fig = go.Figure()
    fig.add_bar(x=labels, y=tax_vals, name="Annual Tax", marker_color=bar_colors,
                text=[inr(v) for v in tax_vals], textposition="outside")
    fig.add_bar(x=labels, y=th_vals, name="Net Take Home", marker_color=th_colors,
                text=[inr(v) for v in th_vals], textposition="outside")
    fig.update_layout(
        **CHART_TEMPLATE, title="Old vs New Regime: Tax & Take-Home",
        height=400, barmode="group",
        legend=dict(orientation="h", y=1.12),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
    )
    return fig


def chart_monthly_takehome(result) -> go.Figure:
    df = result.monthly_df
    active = df[df["Employment Factor"] > 0]
    fig = go.Figure()
    fig.add_bar(x=active["Month"], y=active["Net Take Home"], name="Net Take Home",
                marker_color=COLORS["blue"],
                text=[inr(v) for v in active["Net Take Home"]], textposition="outside",
                textfont=dict(size=10))
    fig.add_scatter(x=active["Month"], y=active["TDS"], mode="lines+markers",
                    name="Monthly TDS", line=dict(color=COLORS["red"], width=2),
                    marker=dict(size=6), yaxis="y2")
    fig.update_layout(
        **CHART_TEMPLATE,
        title=f"{result.regime_label}: Monthly Take-Home & TDS",
        height=400,
        yaxis=dict(title="Net Take Home (₹)", showgrid=True, gridcolor="#f1f5f9"),
        yaxis2=dict(title="TDS (₹)", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12),
    )
    return fig


def chart_ctc_breakdown(result) -> go.Figure:
    df = result.monthly_df
    components = {
        "Basic": df["Basic"].sum(),
        "HRA": df["HRA"].sum(),
        "Special Allowance": df["Special Allowance"].sum(),
        "Tel & Internet": df["Telephone & Internet"].sum(),
        "LTA": df["LTA"].sum(),
        "Periodicals": df["Periodicals & Journals"].sum(),
        "Employer PF": df["Employer PF"].sum(),
    }
    components = {k: v for k, v in components.items() if abs(v) > 0.01}
    palette = [COLORS["navy"], COLORS["blue"], COLORS["light_blue"],
               COLORS["emerald"], COLORS["amber"], COLORS["purple"], COLORS["slate"]]
    fig = go.Figure(go.Pie(
        labels=list(components.keys()),
        values=list(components.values()),
        hole=0.55, textinfo="label+percent",
        marker=dict(colors=palette[:len(components)]),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>",
    ))
    fig.update_layout(**CHART_TEMPLATE, title="Salary Component Mix", height=380)
    return fig


def chart_waterfall(result) -> go.Figure:
    exmp_total = sum(result.salary_exemptions.values())
    via_total  = sum(result.chapter_via_deductions.values())
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute","relative","relative","relative","relative","relative","relative","total"],
        x=["CTC","−Employer PF","−Employee PF","−Prof Tax","−Exemptions","−Deductions","−Tax","Net Take Home"],
        y=[
            result.annual_ctc_paid_in_fy,
            -result.employer_pf_paid_in_fy,
            -result.employee_pf_paid_in_fy,
            -result.professional_tax_paid_in_fy,
            -exmp_total,
            -via_total,
            -result.annual_tax,
            result.annual_take_home_after_tds,
        ],
        connector={"line": {"color": "#cbd5e1"}},
        increasing={"marker": {"color": COLORS["emerald"]}},
        decreasing={"marker": {"color": COLORS["red"]}},
        totals={"marker": {"color": COLORS["navy"]}},
    ))
    fig.update_layout(**CHART_TEMPLATE, title="CTC → Net Take-Home Bridge", height=420)
    return fig


def chart_tax_breakup(result) -> go.Figure:
    labels = ["Slab Tax", "Surcharge", "Cess (4%)"]
    vals   = [result.tax_after_rebate, result.surcharge, result.cess]
    colors = [COLORS["red"], COLORS["amber"], COLORS["slate"]]
    vals_f = [(l, v) for l, v in zip(labels, vals) if v > 0.01]
    if not vals_f:
        return go.Figure().update_layout(**CHART_TEMPLATE, title="Tax Composition (Zero Tax)")
    fig = go.Figure(go.Bar(
        x=[l for l, _ in vals_f],
        y=[v for _, v in vals_f],
        marker_color=colors[:len(vals_f)],
        text=[inr(v) for _, v in vals_f],
        textposition="outside",
    ))
    fig.update_layout(**CHART_TEMPLATE, title="Tax Composition", height=320,
                      yaxis=dict(showgrid=True, gridcolor="#f1f5f9"))
    return fig


def chart_fy_comparison(r25, r26) -> go.Figure:
    cats = ["Annual CTC", "Gross Salary", "Taxable Income", "Annual Tax", "Net Take Home"]
    v25 = [r25.annual_ctc_paid_in_fy, r25.gross_salary_paid_in_fy, r25.taxable_income,
           r25.annual_tax, r25.annual_take_home_after_tds]
    v26 = [r26.annual_ctc_paid_in_fy, r26.gross_salary_paid_in_fy, r26.taxable_income,
           r26.annual_tax, r26.annual_take_home_after_tds]
    fig = go.Figure()
    fig.add_bar(x=cats, y=v25, name="FY 2025-26", marker_color=COLORS["blue"])
    fig.add_bar(x=cats, y=v26, name="FY 2026-27", marker_color=COLORS["emerald"])
    fig.update_layout(**CHART_TEMPLATE, barmode="group", title="FY 2025-26 vs FY 2026-27 Comparison",
                      height=400, legend=dict(orientation="h", y=1.1),
                      yaxis=dict(showgrid=True, gridcolor="#f1f5f9"))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Tab builders
# ─────────────────────────────────────────────────────────────────────────────

def tab_dashboard(results, selected_key, inputs, profile):
    sel  = results[selected_key]
    alt_key = "new" if selected_key == "old" else "old"
    alt  = results[alt_key]
    reco = recommended_regime(results)
    diff = abs(results["old"].annual_tax - results["new"].annual_tax)

    # Recommendation banner
    if reco == "same":
        banner = "Both regimes yield nearly identical tax for this income profile."
        banner_color = "#2563eb"
    elif reco == selected_key:
        banner = f"✅ <b>{REGIMES[selected_key]}</b> is the <b>recommended</b> regime — saves <b>{inr(diff)}</b> vs the alternative."
        banner_color = "#059669"
    else:
        banner = (f"⚠️ <b>{REGIMES[reco]}</b> would save <b>{inr(diff)}</b> more. "
                  f"You are currently viewing <b>{REGIMES[selected_key]}</b>.")
        banner_color = "#d97706"

    st.markdown(
        f'<div class="reco-box" style="border-left-color:{banner_color}">'
        f'<div class="reco-text">{banner}</div></div>',
        unsafe_allow_html=True,
    )

    # Key metric cards
    avg_th = sel.monthly_take_home_avg
    eff_rate = sel.effective_tax_rate_on_gross
    tax_badge_cls = "badge-red" if eff_rate > 20 else ("badge-amber" if eff_rate > 10 else "badge-green")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("Actual CTC Paid in FY", inr(sel.annual_ctc_paid_in_fy),
                    f"Annualized: {inr(inputs.annual_ctc)}", f"{sel.active_months} months", "badge-blue")
    with m2:
        metric_card("Annual Tax", inr(sel.annual_tax),
                    f"Eff. rate: {eff_rate:.2f}% of gross",
                    f"{eff_rate:.1f}% of gross", tax_badge_cls)
    with m3:
        th_delta = sel.annual_take_home_after_tds - alt.annual_take_home_after_tds
        badge_th = f"{'▲' if th_delta > 0 else '▼'} {inr(abs(th_delta))} vs {alt.regime_label}"
        metric_card("Annual Net Take-Home", inr(sel.annual_take_home_after_tds),
                    f"Avg monthly: {inr(avg_th)}", badge_th,
                    "badge-green" if th_delta >= 0 else "badge-red")
    with m4:
        rebate_info = f"Rebate 87A: {inr(sel.rebate_87a)}" if sel.rebate_87a > 0 else f"Taxable income: {inr(sel.taxable_income)}"
        metric_card("Taxable Income", inr(sel.taxable_income),
                    rebate_info, f"{sel.service_days} service days", "badge-blue")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        st.plotly_chart(chart_regime_comparison(results), use_container_width=True)
    with c2:
        st.plotly_chart(chart_ctc_breakdown(sel), use_container_width=True)

    st.plotly_chart(chart_waterfall(sel), use_container_width=True)

    st.markdown('<div class="sec-hdr">📋 Regime Comparison Table</div>', unsafe_allow_html=True)
    st.dataframe(style_df(comparison_table(results)), use_container_width=True, height=120)


def tab_monthly(results, selected_key):
    sel = results[selected_key]

    st.plotly_chart(chart_monthly_takehome(sel), use_container_width=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(chart_tax_breakup(sel), use_container_width=True)
    with c2:
        st.markdown('<div class="sec-hdr">📊 Monthly Snapshot</div>', unsafe_allow_html=True)
        snap = {
            "Regime": sel.regime_label,
            "Active Months": sel.active_months,
            "Avg Monthly Take-Home": inr(sel.monthly_take_home_avg),
            "Avg Monthly TDS": inr(sel.annual_tax / sel.active_months) if sel.active_months else "—",
            "Employee PF (Annual)": inr(sel.employee_pf_paid_in_fy),
            "Professional Tax (Annual)": inr(sel.professional_tax_paid_in_fy),
            "Effective Tax Rate": f"{sel.effective_tax_rate_on_gross:.2f}%",
        }
        for k, v in snap.items():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:.35rem 0;'
                f'border-bottom:1px solid #f1f5f9"><span style="color:#64748b;font-size:.88rem">{k}</span>'
                f'<span style="font-weight:700;font-size:.88rem;color:#1e293b">{v}</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="sec-hdr">📅 Month-wise Salary Breakup</div>', unsafe_allow_html=True)
    display = sel.monthly_df.copy().drop(columns=["Month Start"])
    st.dataframe(style_df(display), use_container_width=True, height=480)


def tab_fy_comparison(inputs, selected_key):
    st.markdown('<div class="sec-hdr">🔮 FY 2025-26 vs FY 2026-27 — Full Year Comparison (Same CTC & Regime)</div>',
                unsafe_allow_html=True)
    st.caption("Both years modeled with full-year service (April to March). Tax slabs unchanged in Budget 2026.")

    fy25_inputs = CalculatorInputs(**{**inputs.__dict__, "financial_year": "FY 2025-26",
                                      "join_date": date(2025, 4, 1)})
    fy26_inputs = CalculatorInputs(**{**inputs.__dict__, "financial_year": "FY 2026-27",
                                      "join_date": date(2026, 4, 1)})
    r25 = calculate_both_regimes(fy25_inputs)[selected_key]
    r26 = calculate_both_regimes(fy26_inputs)[selected_key]

    st.plotly_chart(chart_fy_comparison(r25, r26), use_container_width=True)

    cols = st.columns(2)
    metrics = [
        ("Annual CTC",        r25.annual_ctc_paid_in_fy,        r26.annual_ctc_paid_in_fy),
        ("Gross Salary",      r25.gross_salary_paid_in_fy,      r26.gross_salary_paid_in_fy),
        ("Salary Exemptions", sum(r25.salary_exemptions.values()),sum(r26.salary_exemptions.values())),
        ("Standard Deduction",r25.standard_deduction,            r26.standard_deduction),
        ("Total Deductions",  sum(r25.chapter_via_deductions.values()), sum(r26.chapter_via_deductions.values())),
        ("Taxable Income",    r25.taxable_income,                r26.taxable_income),
        ("Slab Tax",          r25.slab_tax,                      r26.slab_tax),
        ("Rebate 87A",        r25.rebate_87a,                    r26.rebate_87a),
        ("Annual Tax",        r25.annual_tax,                    r26.annual_tax),
        ("Avg Monthly Take-Home", r25.monthly_take_home_avg,     r26.monthly_take_home_avg),
        ("Annual Net Take-Home", r25.annual_take_home_after_tds, r26.annual_take_home_after_tds),
    ]

    with cols[0]:
        st.markdown('<div class="yr-card active" style="border-color:#2563eb">'
                    '<div class="yr-title">📅 FY 2025-26</div></div>', unsafe_allow_html=True)
        for label, v25, _ in metrics:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:.32rem 0;'
                f'border-bottom:1px solid #f1f5f9"><span style="color:#64748b;font-size:.86rem">{label}</span>'
                f'<span style="font-weight:700;font-size:.86rem">{inr(v25)}</span></div>',
                unsafe_allow_html=True,
            )
    with cols[1]:
        st.markdown('<div class="yr-card" style="border-color:#059669">'
                    '<div class="yr-title">📅 FY 2026-27</div></div>', unsafe_allow_html=True)
        for label, v25, v26 in metrics:
            diff = v26 - v25
            diff_html = (
                f'<span style="color:#059669;font-size:.75rem;font-weight:600"> +{inr(diff)}</span>'
                if diff > 0 else
                (f'<span style="color:#dc2626;font-size:.75rem;font-weight:600"> {inr(diff)}</span>' if diff < 0 else "")
            )
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:.32rem 0;'
                f'border-bottom:1px solid #f1f5f9"><span style="color:#64748b;font-size:.86rem">{label}</span>'
                f'<span style="font-weight:700;font-size:.86rem">{inr(v26)}{diff_html}</span></div>',
                unsafe_allow_html=True,
            )


def tab_tax_working(results, selected_key):
    sel = results[selected_key]
    alt_key = "new" if selected_key == "old" else "old"
    alt = results[alt_key]

    st.markdown('<div class="sec-hdr">🧮 Detailed Tax Computation — Both Regimes</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### {sel.regime_label}")
        st.dataframe(style_df(annual_breakup_frame(sel)), use_container_width=True, height=620)
    with c2:
        st.markdown(f"#### {alt.regime_label}")
        st.dataframe(style_df(annual_breakup_frame(alt)), use_container_width=True, height=620)

    st.markdown('<div class="sec-hdr">📂 Deductions Detail — Selected Regime</div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1:
        st.markdown("**Salary Exemptions**")
        exemp_df = pd.DataFrame(
            [(k, v) for k, v in sel.salary_exemptions.items()],
            columns=["Exemption", "Amount"],
        )
        st.dataframe(style_df(exemp_df), use_container_width=True)
    with d2:
        st.markdown("**Chapter VI-A Deductions**")
        via_df = pd.DataFrame(
            [(k, v) for k, v in sel.chapter_via_deductions.items() if v > 0],
            columns=["Section", "Amount"],
        )
        st.dataframe(style_df(via_df) if not via_df.empty else via_df, use_container_width=True)


def tab_optimizer(results, inputs):
    reco = recommended_regime(results)
    suggestions = tax_optimizer(inputs, results)

    sel = results[reco] if reco != "same" else results["new"]
    other_key = "old" if reco == "new" else "new"
    other = results[other_key]

    st.markdown('<div class="sec-hdr">💡 AI-Powered Tax Optimizer</div>', unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    with r1:
        metric_card("Best Regime", REGIMES[reco] if reco != "same" else "Either",
                    f"Tax: {inr(sel.annual_tax)}", "Recommended", "badge-green")
    with r2:
        diff_tax = abs(results["old"].annual_tax - results["new"].annual_tax)
        metric_card("Tax Savings vs Alt. Regime", inr(diff_tax),
                    "Potential annual saving", "Switch to save" if diff_tax > 0 else "Same", "badge-amber")
    with r3:
        # 80C utilization
        pf = results["old"].employee_pf_paid_in_fy
        other_80c_used = min(inputs.other_80c_investments, max(150_000 - pf, 0))
        total_80c = min(pf + other_80c_used, 150_000)
        pct_80c = total_80c / 150_000 * 100
        metric_card("80C Utilization", f"{pct_80c:.0f}%",
                    f"{inr(total_80c)} of {inr(150_000)}", f"{inr(max(150_000-total_80c,0))} more available",
                    "badge-green" if pct_80c >= 90 else "badge-amber")

    # 80C progress
    st.markdown('<div class="sec-hdr">📊 Deduction Utilization Tracker</div>', unsafe_allow_html=True)
    via = results["old"].chapter_via_deductions

    utilization_items = [
        ("Section 80C", min(results["old"].employee_pf_paid_in_fy + inputs.other_80c_investments, 150_000), 150_000, "prog-blue"),
        ("Section 80CCD(1B) — NPS", min(inputs.nps_80ccd_1b, 50_000), 50_000, "prog-green"),
        ("Section 80D — Self/Family", min(inputs.medical_80d_self, 50_000), 50_000, "prog-blue"),
        ("Section 80D — Parents", min(inputs.medical_80d_parents, 50_000), 50_000, "prog-green"),
        ("Section 80TTA/TTB", via.get("Section 80TTA/TTB — Interest", 0),
         50_000 if inputs.age_category in ("senior","super_senior") else 10_000, "prog-blue"),
    ]

    for label, used, cap, cls in utilization_items:
        pct = min(used / cap * 100, 100) if cap > 0 else 0
        st.markdown(
            f'<div style="margin:.6rem 0"><div style="display:flex;justify-content:space-between">'
            f'<span style="font-size:.86rem;font-weight:600;color:#1e293b">{label}</span>'
            f'<span style="font-size:.84rem;color:#64748b">{inr(used)} / {inr(cap)} ({pct:.0f}%)</span>'
            f'</div>{progress_html(pct, cls)}</div>',
            unsafe_allow_html=True,
        )

    # Suggestions
    st.markdown('<div class="sec-hdr">🎯 Personalized Recommendations</div>', unsafe_allow_html=True)
    if not suggestions:
        st.success("🎉 Excellent! Your tax planning appears well-optimized for the current inputs.")
    for s in suggestions:
        cls_map = {"high": "opt-high", "medium": "opt-medium", "low": "opt-low"}
        priority_badge = {"high": "🔴 High Priority", "medium": "🟡 Medium", "low": "🟢 Low"}
        saving_html = f'<div class="opt-saving">Potential Saving: {inr(s["potential_saving"])}</div>' if s.get("potential_saving") else ""
        st.markdown(
            f'<div class="opt-card {cls_map[s["priority"]]}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center">'
            f'<div class="opt-title">{s["section"]} — {s["action"]}</div>'
            f'<span style="font-size:.75rem;font-weight:600;color:#475569">{priority_badge[s["priority"]]}</span></div>'
            f'{saving_html}<div class="opt-desc">{s["description"]}</div></div>',
            unsafe_allow_html=True,
        )

    # Investment calendar
    st.markdown('<div class="sec-hdr">📆 Tax-Saving Investment Calendar</div>', unsafe_allow_html=True)
    calendar_data = [
        ("April–June", "Begin 80C investments. Declare investment proofs to payroll."),
        ("July–September", "Review 80D health insurance renewal. Consider NPS top-up."),
        ("October–December", "Ensure home loan interest certificate from bank for Sec 24(b)."),
        ("January (15th)", "Submit investment/proof declarations to payroll team."),
        ("January–February", "Review TDS deductions for the year. Settle any gaps."),
        ("March (31st)", "Last date for tax-saving investments for the FY."),
    ]
    c1, c2 = st.columns(2)
    for i, (period, action) in enumerate(calendar_data):
        col = c1 if i % 2 == 0 else c2
        with col:
            st.markdown(
                f'<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:10px;padding:.7rem .9rem;margin-bottom:.5rem">'
                f'<div style="font-weight:700;color:#1e3a8a;font-size:.88rem">{period}</div>'
                f'<div style="color:#475569;font-size:.83rem;margin-top:.2rem">{action}</div></div>',
                unsafe_allow_html=True,
            )


def tab_deductions_guide():
    st.markdown('<div class="sec-hdr">📖 Complete Deductions & Exemptions Guide — Income Tax Act 1961 & Finance Act 2025</div>',
                unsafe_allow_html=True)

    sub_tabs = st.tabs(["🆕 New Regime", "📜 Old Regime — Chapter VI-A", "🏠 Salary Exemptions", "🏡 House Property", "📊 Tax Slabs", "📈 Surcharge & Cess"])

    # ── New Regime tab ────────────────────────────────────────────────────────
    with sub_tabs[0]:
        st.markdown(
            '<div style="background:linear-gradient(90deg,#dcfce7,#d1fae5);border-radius:12px;'
            'padding:1rem 1.2rem;border:1px solid #6ee7b7;margin-bottom:1rem">'
            '<div style="font-weight:800;font-size:1rem;color:#065f46">🌟 New Tax Regime — Default Regime from FY 2023-24</div>'
            '<div style="font-size:.88rem;color:#047857;margin-top:.4rem">'
            'Zero tax on income up to ₹12,75,000 after standard deduction of ₹75,000 (via 87A rebate). '
            'Fewer deductions but lower rates and simplicity.</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown("**✅ What is AVAILABLE under the New Tax Regime:**")
        for item in NEW_REGIME_AVAILABLE:
            st.markdown(
                f'<div class="ded-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="ded-card-section">{item["section"]}</div>'
                f'<div class="ded-card-title">{item["name"]}</div>'
                f'<div class="ded-limit">{item["limit_text"]}</div></div>'
                f'<span class="regime-tag tag-new">NEW ✓</span></div>'
                f'<div class="ded-note">{item["notes"]}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Old Regime Chapter VI-A ───────────────────────────────────────────────
    with sub_tabs[1]:
        st.markdown(
            '<div style="background:linear-gradient(90deg,#fef3c7,#fde68a);border-radius:12px;'
            'padding:1rem 1.2rem;border:1px solid #fcd34d;margin-bottom:1rem">'
            '<div style="font-weight:800;font-size:1rem;color:#78350f">📜 Old Tax Regime — Chapter VI-A Deductions</div>'
            '<div style="font-size:.88rem;color:#92400e;margin-top:.4rem">'
            'Higher tax rates but rich deduction ecosystem. Beneficial for those with significant investments, '
            'HRA, home loans, or medical expenses.</div></div>',
            unsafe_allow_html=True,
        )
        for item in CHAPTER_VIA_DEDUCTIONS:
            old_tag = '<span class="regime-tag tag-old">OLD</span>'
            new_tag = '<span class="regime-tag tag-new">NEW ✓</span>' if item["new_regime"] else ""
            instruments_html = ""
            if item.get("instruments"):
                bullets = "".join(f"<li>{i}</li>" for i in item["instruments"])
                instruments_html = f'<ul style="margin:.4rem 0 0 1rem;font-size:.82rem;color:#334155">{bullets}</ul>'
            st.markdown(
                f'<div class="ded-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="ded-card-section">{item["section"]}</div>'
                f'<div class="ded-card-title">{item["name"]}</div>'
                f'<div class="ded-limit">{item["limit_text"]}</div></div>'
                f'<div>{old_tag}{new_tag}</div></div>'
                f'{instruments_html}'
                f'<div class="ded-note">{item["notes"]}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Salary Exemptions ─────────────────────────────────────────────────────
    with sub_tabs[2]:
        st.markdown("**Section 10 Exemptions — Partially or Fully Exempt Salary Components**")
        for item in SALARY_EXEMPTIONS:
            old_tag = '<span class="regime-tag tag-old">OLD</span>' if item["old_regime"] else ""
            new_tag = '<span class="regime-tag tag-new">NEW ✓</span>' if item["new_regime"] else ""
            both_tag = '<span class="regime-tag tag-both">BOTH</span>' if (item["old_regime"] and item["new_regime"]) else ""
            tags = both_tag if (item["old_regime"] and item["new_regime"]) else (old_tag + new_tag)
            st.markdown(
                f'<div class="ded-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                f'<div><div class="ded-card-section">{item["section"]}</div>'
                f'<div class="ded-card-title">{item["name"]}</div>'
                f'<div class="ded-limit">{item["limit"]}</div></div>'
                f'<div>{tags}</div></div>'
                f'<div class="ded-note">{item["notes"]}</div></div>',
                unsafe_allow_html=True,
            )

    # ── House Property ────────────────────────────────────────────────────────
    with sub_tabs[3]:
        st.markdown("**Income from House Property Deductions (Old Regime only)**")
        for item in HOUSE_PROPERTY_DEDUCTIONS:
            st.markdown(
                f'<div class="ded-card">'
                f'<div class="ded-card-section">{item["section"]}</div>'
                f'<div class="ded-card-title">{item["name"]}</div>'
                f'<div class="ded-limit">{item["limit_text"]}</div>'
                f'<div class="ded-note">{item["notes"]}</div></div>',
                unsafe_allow_html=True,
            )

    # ── Tax Slabs ─────────────────────────────────────────────────────────────
    with sub_tabs[4]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"### {NEW_REGIME_SLABS_INFO['title']}")
            st.info(f"📌 {NEW_REGIME_SLABS_INFO['effective_zero_tax']}")
            slab_df = pd.DataFrame(NEW_REGIME_SLABS_INFO["slabs"])
            st.dataframe(slab_df, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("### Old Tax Regime Slabs")
            st.markdown("**Below 60 Years**")
            st.dataframe(pd.DataFrame(OLD_REGIME_SLABS_INFO["under_60"]), use_container_width=True, hide_index=True)
            st.markdown("**60–79 Years (Senior Citizen)**")
            st.dataframe(pd.DataFrame(OLD_REGIME_SLABS_INFO["senior_60_80"]), use_container_width=True, hide_index=True)
            st.markdown("**80+ Years (Super Senior)**")
            st.dataframe(pd.DataFrame(OLD_REGIME_SLABS_INFO["super_senior_80_plus"]), use_container_width=True, hide_index=True)

    # ── Surcharge & Cess ──────────────────────────────────────────────────────
    with sub_tabs[5]:
        st.markdown("### Surcharge Rates")
        st.info("Surcharge applies when taxable income exceeds ₹50 lakhs. It is calculated on the income tax amount (not income).")
        sur_df = pd.DataFrame(SURCHARGE_INFO)
        st.dataframe(sur_df, use_container_width=True, hide_index=True)
        st.markdown(f"### {CESS_INFO}")
        st.info("Cess of 4% is applied on (Income Tax + Surcharge) for ALL taxpayers regardless of income level.")


def tab_payslip(results, selected_key, inputs, profile):
    sel = results[selected_key]

    st.markdown('<div class="sec-hdr">📄 Monthly Pay Slip Generator</div>', unsafe_allow_html=True)

    month_options = [row["Month"] for _, row in sel.monthly_df.iterrows() if row["Employment Factor"] > 0]
    if not month_options:
        st.error("No active months found for the selected inputs.")
        return

    selected_month = st.selectbox("Select Month for Pay Slip", month_options)
    row = sel.monthly_df[sel.monthly_df["Month"] == selected_month].iloc[0]

    emp_name = profile.get("name") or "Employee Name"
    emp_id   = profile.get("id") or "—"
    dept     = profile.get("dept") or "—"
    desig    = profile.get("desig") or "—"

    def ps_row(label, amount, bold=False):
        style = "font-weight:800;" if bold else ""
        return (
            f'<div class="payslip-row" style="{style}">'
            f'<span>{label}</span><span>{inr(amount)}</span></div>'
        )

    payslip_html = f"""
    <div class="payslip">
        <div class="payslip-header">
            <div style="font-size:1.1rem;font-weight:800">{COMPANY_CONFIG.company_name}</div>
            <div style="font-size:.85rem;opacity:.8;margin-top:.2rem">Salary Slip for {selected_month}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;font-size:.85rem;margin-bottom:1rem">
            <div><b>Employee:</b> {emp_name}</div><div><b>ID:</b> {emp_id}</div>
            <div><b>Department:</b> {dept}</div><div><b>Designation:</b> {desig}</div>
            <div><b>PF Option:</b> {PF_OPTIONS[inputs.pf_option]}</div>
            <div><b>Regime:</b> {sel.regime_label}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
            <div>
                <div style="font-weight:800;color:#1e3a8a;border-bottom:2px solid #dbeafe;padding-bottom:.3rem;margin-bottom:.5rem">EARNINGS</div>
                {ps_row("Basic Salary", row["Basic"])}
                {ps_row("HRA", row["HRA"])}
                {ps_row("Special Allowance", row["Special Allowance"])}
                {ps_row("Telephone & Internet", row["Telephone & Internet"])}
                {''.join([ps_row("LTA", row["LTA"])] if row["LTA"] > 0 else [])}
                {''.join([ps_row("Periodicals & Journals", row["Periodicals & Journals"])] if row["Periodicals & Journals"] > 0 else [])}
                {ps_row("Gross Salary", row["Gross Salary"], bold=True)}
            </div>
            <div>
                <div style="font-weight:800;color:#dc2626;border-bottom:2px solid #fee2e2;padding-bottom:.3rem;margin-bottom:.5rem">DEDUCTIONS</div>
                {ps_row("Employee PF", row["Employee PF"])}
                {ps_row("Professional Tax", row["Professional Tax"])}
                {ps_row("TDS (Income Tax)", row["TDS"])}
                <br>
                <div style="font-weight:800;color:#059669;border-top:2px solid #dcfce7;padding-top:.5rem;margin-top:.3rem">
                    <div class="payslip-row payslip-total"><span>NET PAY</span><span>{inr(row["Net Take Home"])}</span></div>
                </div>
            </div>
        </div>
        <div style="margin-top:1rem;padding-top:.8rem;border-top:1px solid #e2e8f0;font-size:.78rem;color:#94a3b8;text-align:center">
            Generated by SmartPay — Employee Tax & Salary Hub · This is a computer-generated estimate.
        </div>
    </div>
    """
    st.markdown(payslip_html, unsafe_allow_html=True)
    st.caption("Note: Actual pay slip from your payroll system may differ slightly due to rounding, proof cut-offs, or salary revisions.")


def tab_downloads(inputs, results, selected_key, profile):
    st.markdown('<div class="sec-hdr">📥 Download Center</div>', unsafe_allow_html=True)

    sel = results[selected_key]
    monthly_csv = sel.monthly_df.to_csv(index=False).encode("utf-8")
    comparison_csv = comparison_table(results).to_csv(index=False).encode("utf-8")

    export_bytes = build_export_workbook(
        inputs, results, selected_key,
        employee_name=profile.get("name",""),
        employee_id=profile.get("id",""),
        department=profile.get("dept",""),
        designation=profile.get("desig",""),
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:14px;padding:1.2rem;text-align:center">'
            '<div style="font-size:2rem">📊</div>'
            '<div style="font-weight:700;color:#1e3a8a;margin:.4rem 0">Full Excel Report</div>'
            '<div style="font-size:.83rem;color:#64748b;margin-bottom:.8rem">7-sheet workbook with all calculations, monthly details, sources</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️ Download Excel (.xlsx)",
            data=export_bytes,
            file_name=f"SmartPay_{inputs.financial_year.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:14px;padding:1.2rem;text-align:center">'
            '<div style="font-size:2rem">📅</div>'
            '<div style="font-weight:700;color:#1e3a8a;margin:.4rem 0">Monthly Salary CSV</div>'
            '<div style="font-size:.83rem;color:#64748b;margin-bottom:.8rem">Month-wise salary breakup for selected regime</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️ Download Monthly CSV",
            data=monthly_csv,
            file_name=f"Monthly_{selected_key}_{inputs.financial_year.replace(' ','_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown(
            '<div style="background:#f8faff;border:1px solid #dbeafe;border-radius:14px;padding:1.2rem;text-align:center">'
            '<div style="font-size:2rem">🔀</div>'
            '<div style="font-weight:700;color:#1e3a8a;margin:.4rem 0">Comparison CSV</div>'
            '<div style="font-size:.83rem;color:#64748b;margin-bottom:.8rem">Old vs New regime comparison summary</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️ Download Comparison CSV",
            data=comparison_csv,
            file_name=f"Regime_Comparison_{inputs.financial_year.replace(' ','_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def tab_about():
    st.markdown('<div class="sec-hdr">ℹ️ About This Application</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Salary Structure Assumptions")
        assumptions = [
            "Basic = 50% of (CTC minus Employer PF)",
            "HRA = 40% of Basic (40% non-metro, 50% metro for HRA exemption)",
            "PF Option 1 = 12% of Basic; PF Option 2 = 12% of ₹15,000 ceiling",
            "LTA (₹5,000/month) and Periodicals (₹500/month) included only under Old Regime",
            "Telephone & Internet = ₹2,000/month — claim-based reimbursement",
            "Professional Tax = ₹200/month, ₹300 in February (on gross > ₹25,000)",
            "First month salary prorated by calendar days from joining date to month-end",
            "Assumes Resident Individual tax treatment only",
        ]
        for a in assumptions:
            st.markdown(f"- {a}")

        st.markdown("### Tax Law References Used")
        for key, url in SOURCE_URLS.items():
            st.markdown(f"- **{key.replace('_',' ').title()}**: [{url}]({url})")

    with c2:
        st.markdown("### Important Disclaimers")
        for note in FOOTER_NOTES:
            st.markdown(f"- {note}")

        st.markdown("### Features in This App")
        features = [
            "FY 2025-26 & FY 2026-27 side-by-side comparison",
            "New Tax Regime (Finance Act 2025) — Budget 2025 slabs",
            "Old Tax Regime with all Chapter VI-A deductions",
            "87A rebate with marginal relief (New Regime up to ₹60,000)",
            "80CCD(2) Employer NPS — available in both regimes",
            "80D, 80DD, 80DDB, 80E, 80EEA, 80G, 80GG, 80TTA/TTB, 80U",
            "Surcharge with marginal relief",
            "Month-wise salary breakup with TDS distribution",
            "Tax optimizer with personalized recommendations",
            "Monthly pay slip generator",
            "7-sheet Excel download with full working",
        ]
        for f in features:
            st.markdown(f"- ✅ {f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(CSS, unsafe_allow_html=True)
inputs, selected_regime_key, profile = build_sidebar()

# Hero
reco_chip_text = "New Regime Preferred" if selected_regime_key == "new" else "Old Regime Selected"
st.markdown(
    f"""<div class="hero">
        <div class="hero-title">{COMPANY_CONFIG.app_title}</div>
        <div class="hero-sub">{COMPANY_CONFIG.app_subtitle}</div>
        <div>
            <span class="chip white">📅 {inputs.financial_year}</span>
            <span class="chip green">✅ {REGIMES[selected_regime_key]}</span>
            <span class="chip amber">🔁 FY Comparison Available</span>
            <span class="chip white">📖 Full Deductions Guide</span>
            <span class="chip white">💡 Tax Optimizer</span>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# Guard: no salary this FY
fy_start, fy_end = financial_year_bounds(inputs.financial_year)
if inputs.join_date > fy_end:
    st.error("⚠️ Joining date is after the end of the selected financial year. No salary will be computed.")
    st.stop()

results = calculate_both_regimes(inputs)
selected_result = results[selected_regime_key]

for warning in selected_result.warnings:
    st.warning(warning)

# Main tabs
tabs = st.tabs([
    "🏠 Dashboard",
    "📅 Monthly Salary",
    "🔮 FY 2025-26 vs 2026-27",
    "🧮 Tax Working",
    "💡 Tax Optimizer",
    "📖 Deductions Guide",
    "📄 Pay Slip",
    "📥 Downloads",
    "ℹ️ About",
])

with tabs[0]:
    tab_dashboard(results, selected_regime_key, inputs, profile)
with tabs[1]:
    tab_monthly(results, selected_regime_key)
with tabs[2]:
    tab_fy_comparison(inputs, selected_regime_key)
with tabs[3]:
    tab_tax_working(results, selected_regime_key)
with tabs[4]:
    tab_optimizer(results, inputs)
with tabs[5]:
    tab_deductions_guide()
with tabs[6]:
    tab_payslip(results, selected_regime_key, inputs, profile)
with tabs[7]:
    tab_downloads(inputs, results, selected_regime_key, profile)
with tabs[8]:
    tab_about()
