from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CompanyConfig:
    # ── Salary structure ──────────────────────────────────────────────────────
    basic_ratio_of_ctc_less_employer_pf: float = 0.50
    hra_rate_on_basic: float = 0.40
    lta_monthly_old_regime: float = 5000.0
    periodicals_monthly_old_regime: float = 500.0
    phone_internet_monthly: float = 2000.0
    food_allowance_monthly: float = 2200.0        # Sec 17(2) – meal vouchers
    pf_rate: float = 0.12
    pf_salary_ceiling_monthly: float = 15000.0
    professional_tax_monthly: float = 200.0
    professional_tax_february: float = 300.0
    professional_tax_salary_threshold: float = 25000.0
    minimum_special_allowance: float = 0.0

    # ── Standard deductions ───────────────────────────────────────────────────
    standard_deduction_old: float = 50000.0
    standard_deduction_new: float = 75000.0

    # ── Chapter VI-A caps ─────────────────────────────────────────────────────
    section_80c_cap: float = 150000.0
    section_80ccd_1b_cap: float = 50000.0
    section_80ccd_2_rate_private: float = 0.10    # 10 % for private-sector employers
    section_80ccd_2_rate_govt: float = 0.14       # 14 % for central-govt employers
    section_80d_self_family: float = 25000.0      # rises to 50 000 for senior citizen self
    section_80d_parents_normal: float = 25000.0
    section_80d_parents_senior: float = 50000.0
    section_80dd_normal: float = 75000.0
    section_80dd_severe: float = 125000.0
    section_80ddb_normal: float = 40000.0
    section_80ddb_senior: float = 100000.0
    section_80ee_cap: float = 50000.0
    section_80eea_cap: float = 150000.0
    section_80gg_monthly: float = 5000.0          # max ₹5 000 /month
    section_80tta_cap: float = 10000.0
    section_80ttb_cap: float = 50000.0            # senior citizens only
    section_80u_normal: float = 75000.0
    section_80u_severe: float = 125000.0
    self_occupied_home_loan_cap_old: float = 200000.0

    # ── Branding ──────────────────────────────────────────────────────────────
    app_title: str = "SmartPay — Employee Tax & Salary Hub"
    app_subtitle: str = (
        "Premium Income Tax & Take-Home Calculator  ·  FY 2025-26 & FY 2026-27  ·  "
        "Old Regime & New Regime  ·  All Deductions & Exemptions"
    )
    company_name: str = "Your Company"
    company_tagline: str = "Empowering Employees with Financial Clarity"


COMPANY_CONFIG = CompanyConfig()

# ── Lookup dictionaries ────────────────────────────────────────────────────────

AGE_CATEGORIES: Dict[str, str] = {
    "under_60": "Below 60 years",
    "senior": "60 to 79 years",
    "super_senior": "80 years and above",
}

PF_OPTIONS: Dict[str, str] = {
    "basic": "12% on Basic Salary",
    "restricted": "12% on ₹15,000 statutory ceiling",
}

REGIMES: Dict[str, str] = {
    "old": "Old Tax Regime",
    "new": "New Tax Regime",
}

FINANCIAL_YEARS: List[str] = ["FY 2025-26", "FY 2026-27"]

EMPLOYER_TYPE_OPTIONS: Dict[str, str] = {
    "private": "Private Sector (NPS 80CCD(2) @ 10%)",
    "govt": "Central Govt / PSU (NPS 80CCD(2) @ 14%)",
}

# ── Tax slabs ─────────────────────────────────────────────────────────────────

OLD_SLABS: Dict[str, List[Tuple[float, float]]] = {
    "under_60": [
        (250_000.0, 0.00),
        (500_000.0, 0.05),
        (1_000_000.0, 0.20),
        (float("inf"), 0.30),
    ],
    "senior": [
        (300_000.0, 0.00),
        (500_000.0, 0.05),
        (1_000_000.0, 0.20),
        (float("inf"), 0.30),
    ],
    "super_senior": [
        (500_000.0, 0.00),
        (1_000_000.0, 0.20),
        (float("inf"), 0.30),
    ],
}

# Finance Act 2025 – new regime slabs (effective AY 2026-27 / FY 2025-26 onward)
NEW_SLABS: List[Tuple[float, float]] = [
    (400_000.0, 0.00),
    (800_000.0, 0.05),
    (1_200_000.0, 0.10),
    (1_600_000.0, 0.15),
    (2_000_000.0, 0.20),
    (2_400_000.0, 0.25),
    (float("inf"), 0.30),
]

SURCHARGE_THRESHOLDS_OLD: List[Tuple[float, float]] = [
    (5_000_000.0, 0.10),
    (10_000_000.0, 0.15),
    (20_000_000.0, 0.25),
    (50_000_000.0, 0.37),
]

SURCHARGE_THRESHOLDS_NEW: List[Tuple[float, float]] = [
    (5_000_000.0, 0.10),
    (10_000_000.0, 0.15),
    (20_000_000.0, 0.25),
    (50_000_000.0, 0.25),   # capped at 25 % under new regime
]

# ── Source URLs ───────────────────────────────────────────────────────────────

SOURCE_URLS: Dict[str, str] = {
    "income_tax_act_1961": "https://incometaxindia.gov.in/Acts/IT%20Act%201961/2023/102120000000006799.htm",
    "budget_2025_speech": "https://incometaxindia.gov.in/budgets%20and%20bills/2025/budget_speech-2025.pdf",
    "finance_act_2025_115bac": "https://incometaxindia.gov.in/Acts/Finance%20Acts/2025/102520000000148617.htm",
    "tax_rates": "https://incometaxindia.gov.in/Charts%20%20Tables/Tax%20rates.htm",
    "deductions_chart": "https://incometaxindia.gov.in/charts%2520%2520tables/deductions.htm",
    "resident_benefits": "https://incometaxindia.gov.in/Charts%2520%2520Tables/Benefits_available_only_to_Resident_Persons.htm",
    "budget_2026_memo": "https://incometaxindia.gov.in/Budgets%2520and%2520Bills/2026/memo-2026.pdf",
    "budget_2026_faq": "https://incometaxindia.gov.in/Documents/Budget2026/FAQs-Budget-2026.pdf",
}

FOOTER_NOTES: List[str] = [
    "This calculator is for employee planning purposes only and does not constitute professional tax advice.",
    "Consult a Chartered Accountant for final tax planning, ITR filing, or complex income scenarios.",
    "FY 2026-27 uses the same slab structure as FY 2025-26 — Budget 2026 did not revise personal income-tax slabs.",
    "Professional tax is modeled at ₹200 per eligible month and ₹300 in February.",
    "Final payroll TDS may differ based on your company's monthly proration, proof cut-offs, and rounding.",
    "New Tax Regime is the default regime from FY 2023-24 unless the employee opts out explicitly.",
]
