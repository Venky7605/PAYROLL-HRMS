from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pandas as pd

from company_config import (
    AGE_CATEGORIES,
    COMPANY_CONFIG,
    NEW_SLABS,
    OLD_SLABS,
    PF_OPTIONS,
    REGIMES,
    SURCHARGE_THRESHOLDS_NEW,
    SURCHARGE_THRESHOLDS_OLD,
)


# ── Numeric helpers ────────────────────────────────────────────────────────────

def excel_round(value: float, digits: int = 0) -> float:
    quant = Decimal("1").scaleb(-digits)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def clamp(value: float) -> float:
    return max(float(value or 0), 0.0)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class CalculatorInputs:
    # ── Core ─────────────────────────────────────────────────────────────────
    financial_year: str
    annual_ctc: float
    join_date: date
    pf_option: str
    age_category: str
    # ── Rent & reimbursements ────────────────────────────────────────────────
    monthly_rent: float = 0.0
    metro_city: bool = False
    phone_internet_claim: float = 0.0
    lta_claim: float = 0.0
    periodicals_claim: float = 0.0
    # ── Old-regime Chapter VI-A ──────────────────────────────────────────────
    other_80c_investments: float = 0.0       # over and above employee PF
    nps_80ccd_1b: float = 0.0                # additional NPS u/s 80CCD(1B)
    employer_nps_pct: float = 0.0            # employer NPS as % of basic (0–14)
    is_govt_employer: bool = False           # 14 % cap vs 10 % cap for 80CCD(2)
    medical_80d_self: float = 0.0            # health insurance self + family
    medical_80d_parents: float = 0.0         # health insurance parents
    parents_senior_citizen: bool = False     # True = parent limit rises to ₹50K
    medical_80dd: float = 0.0               # disabled dependent (fixed deduction trigger)
    disability_severe_80dd: bool = False
    medical_80ddb: float = 0.0              # specified disease treatment
    education_loan_80e: float = 0.0         # education loan interest
    home_loan_interest_self_occupied: float = 0.0   # Sec 24(b) self-occupied
    home_loan_interest_80ee: float = 0.0    # additional 80EE
    home_loan_interest_80eea: float = 0.0   # additional 80EEA affordable housing
    rent_paid_80gg: float = 0.0             # if no HRA in salary, annual rent
    savings_interest_80tta: float = 0.0     # savings bank interest (below 60)
    savings_interest_80ttb: float = 0.0     # all interest for senior citizens
    self_disability_80u: bool = False
    self_disability_severe: bool = False
    eligible_80g: float = 0.0
    other_income: float = 0.0
    resident_individual: bool = True

    def normalized(self) -> "CalculatorInputs":
        return CalculatorInputs(
            financial_year=self.financial_year,
            annual_ctc=clamp(self.annual_ctc),
            join_date=self.join_date,
            pf_option=self.pf_option,
            age_category=self.age_category,
            monthly_rent=clamp(self.monthly_rent),
            metro_city=bool(self.metro_city),
            phone_internet_claim=clamp(self.phone_internet_claim),
            lta_claim=clamp(self.lta_claim),
            periodicals_claim=clamp(self.periodicals_claim),
            other_80c_investments=clamp(self.other_80c_investments),
            nps_80ccd_1b=clamp(self.nps_80ccd_1b),
            employer_nps_pct=max(0.0, min(float(self.employer_nps_pct or 0), 14.0)),
            is_govt_employer=bool(self.is_govt_employer),
            medical_80d_self=clamp(self.medical_80d_self),
            medical_80d_parents=clamp(self.medical_80d_parents),
            parents_senior_citizen=bool(self.parents_senior_citizen),
            medical_80dd=clamp(self.medical_80dd),
            disability_severe_80dd=bool(self.disability_severe_80dd),
            medical_80ddb=clamp(self.medical_80ddb),
            education_loan_80e=clamp(self.education_loan_80e),
            home_loan_interest_self_occupied=clamp(self.home_loan_interest_self_occupied),
            home_loan_interest_80ee=clamp(self.home_loan_interest_80ee),
            home_loan_interest_80eea=clamp(self.home_loan_interest_80eea),
            rent_paid_80gg=clamp(self.rent_paid_80gg),
            savings_interest_80tta=clamp(self.savings_interest_80tta),
            savings_interest_80ttb=clamp(self.savings_interest_80ttb),
            self_disability_80u=bool(self.self_disability_80u),
            self_disability_severe=bool(self.self_disability_severe),
            eligible_80g=clamp(self.eligible_80g),
            other_income=float(self.other_income or 0),
            resident_individual=bool(self.resident_individual),
        )


@dataclass
class RegimeResult:
    regime_key: str
    regime_label: str
    financial_year: str
    inputs: CalculatorInputs
    monthly_template: Dict[str, float]
    monthly_df: pd.DataFrame
    annual_ctc_input: float
    annual_ctc_paid_in_fy: float
    gross_salary_paid_in_fy: float
    employer_pf_paid_in_fy: float
    employee_pf_paid_in_fy: float
    professional_tax_paid_in_fy: float
    active_months: int
    service_days: int
    salary_exemptions: Dict[str, float]
    chapter_via_deductions: Dict[str, float]
    standard_deduction: float
    house_property_income: float
    other_income: float
    gross_total_income: float
    taxable_income: float
    slab_tax: float
    rebate_87a: float
    tax_after_rebate: float
    surcharge: float
    cess: float
    annual_tax: float
    annual_take_home_before_tds: float
    annual_take_home_after_tds: float
    effective_tax_rate_on_gross: float
    monthly_take_home_avg: float
    employer_nps_deduction: float
    warnings: List[str] = field(default_factory=list)


# ── Date / calendar helpers ────────────────────────────────────────────────────

def financial_year_bounds(financial_year: str) -> Tuple[date, date]:
    parts = financial_year.replace("FY", "").strip().split("-")
    start_year = int(parts[0])
    end_year = 2000 + int(parts[1])
    return date(start_year, 4, 1), date(end_year, 3, 31)


def month_starts_for_fy(financial_year: str) -> List[date]:
    start, _ = financial_year_bounds(financial_year)
    months: List[date] = []
    current = start
    for _ in range(12):
        months.append(current)
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    return months


def month_end(month_start: date) -> date:
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return date(month_start.year, month_start.month, last_day)


def employment_factor(month_start: date, join_date: date, fy_start: date, fy_end: date) -> float:
    if join_date < fy_start:
        join_date = fy_start
    current_month_end = month_end(month_start)
    if month_start > fy_end:
        return 0.0
    if join_date <= month_start:
        return 1.0
    if join_date > current_month_end:
        return 0.0
    days_in_month = (current_month_end - month_start).days + 1
    payable_days = (current_month_end - join_date).days + 1
    return excel_round(payable_days / days_in_month, 4)


def allocate_by_weights(total: float, weights: List[float], digits: int = 2) -> List[float]:
    if total <= 0:
        return [0.0 for _ in weights]
    cleaned = [max(float(w or 0), 0.0) for w in weights]
    total_weight = sum(cleaned)
    if total_weight <= 0:
        cleaned = [1.0 if i == 0 else 0.0 for i in range(len(weights))]
        total_weight = sum(cleaned)
    factor = 10 ** digits
    total_units = int(Decimal(str(total * factor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    sum_w = Decimal(str(total_weight))
    floors: List[int] = []
    remainders: List[Tuple[int, Decimal]] = []
    for idx, w in enumerate(cleaned):
        raw = (Decimal(total_units) * Decimal(str(w))) / sum_w
        fl = int(raw.to_integral_value(rounding=ROUND_FLOOR))
        floors.append(fl)
        remainders.append((idx, raw - fl))
    remainder_units = total_units - sum(floors)
    for idx, _ in sorted(remainders, key=lambda x: x[1], reverse=True)[:remainder_units]:
        floors[idx] += 1
    return [u / factor for u in floors]


def build_monthly_template(annual_ctc: float, pf_option: str, regime_key: str) -> Dict[str, float]:
    monthly_ctc = annual_ctc / 12.0
    if pf_option == "restricted":
        employer_pf = COMPANY_CONFIG.pf_salary_ceiling_monthly * COMPANY_CONFIG.pf_rate
        basic = excel_round((monthly_ctc - employer_pf) * COMPANY_CONFIG.basic_ratio_of_ctc_less_employer_pf, 0)
        employer_pf = excel_round(employer_pf, 0)
    else:
        basic = excel_round(
            COMPANY_CONFIG.basic_ratio_of_ctc_less_employer_pf * monthly_ctc
            / (1 + COMPANY_CONFIG.basic_ratio_of_ctc_less_employer_pf * COMPANY_CONFIG.pf_rate),
            0,
        )
        employer_pf = excel_round(basic * COMPANY_CONFIG.pf_rate, 0)

    hra = excel_round(basic * COMPANY_CONFIG.hra_rate_on_basic, 0)
    lta = COMPANY_CONFIG.lta_monthly_old_regime if regime_key == "old" else 0.0
    periodicals = COMPANY_CONFIG.periodicals_monthly_old_regime if regime_key == "old" else 0.0
    phone = COMPANY_CONFIG.phone_internet_monthly
    special = monthly_ctc - basic - hra - lta - periodicals - phone - employer_pf
    special = excel_round(special, 2)
    gross = excel_round(basic + hra + lta + periodicals + phone + special, 2)
    total_ctc = excel_round(gross + employer_pf, 2)
    return {
        "monthly_ctc": excel_round(monthly_ctc, 2),
        "basic": basic,
        "hra": hra,
        "lta": lta,
        "periodicals": periodicals,
        "phone_internet": phone,
        "special_allowance": special,
        "employer_pf": employer_pf,
        "employee_pf": employer_pf,
        "gross_salary": gross,
        "total_ctc": total_ctc,
    }


def professional_tax_for_month(gross_salary: float, month_num: int) -> float:
    if gross_salary <= COMPANY_CONFIG.professional_tax_salary_threshold:
        return 0.0
    return COMPANY_CONFIG.professional_tax_february if month_num == 2 else COMPANY_CONFIG.professional_tax_monthly


def piecewise_tax(income: float, slabs: List[Tuple[float, float]]) -> float:
    if income <= 0:
        return 0.0
    tax, lower = 0.0, 0.0
    for upper, rate in slabs:
        if income <= lower:
            break
        taxable_portion = min(income, upper) - lower
        if taxable_portion > 0 and rate > 0:
            tax += taxable_portion * rate
        lower = upper
    return excel_round(tax, 2)


def slab_tax(income: float, regime_key: str, age_category: str) -> float:
    slabs = OLD_SLABS[age_category] if regime_key == "old" else NEW_SLABS
    return piecewise_tax(income, slabs)


def rebate_87a(income: float, tax_before_rebate: float, regime_key: str, resident_individual: bool) -> float:
    if not resident_individual or tax_before_rebate <= 0:
        return 0.0
    if regime_key == "old":
        return min(tax_before_rebate, 12500.0) if income <= 500_000 else 0.0
    # New regime — Finance Act 2025
    if income <= 1_200_000:
        return min(tax_before_rebate, 60_000.0)
    excess = income - 1_200_000.0
    marginal = max(tax_before_rebate - excess, 0.0)
    return min(marginal, 60_000.0, tax_before_rebate)


@lru_cache(maxsize=None)
def _tax_before_cess_cached(income: float, regime_key: str, age_category: str, resident: bool) -> float:
    base = slab_tax(income, regime_key, age_category)
    reb = rebate_87a(income, base, regime_key, resident)
    after_reb = max(base - reb, 0.0)
    sur = _surcharge_cached(income, after_reb, regime_key, age_category, resident)
    return excel_round(after_reb + sur, 2)


def applicable_surcharge_rate(income: float, regime_key: str) -> Tuple[float, float]:
    thresholds = SURCHARGE_THRESHOLDS_OLD if regime_key == "old" else SURCHARGE_THRESHOLDS_NEW
    rate, start = 0.0, 0.0
    for threshold, current_rate in thresholds:
        if income > threshold:
            rate = current_rate
            start = threshold
    return rate, start


@lru_cache(maxsize=None)
def _surcharge_cached(income: float, tax_after_rebate: float, regime_key: str, age_category: str, resident: bool) -> float:
    rate, start = applicable_surcharge_rate(income, regime_key)
    if rate <= 0 or tax_after_rebate <= 0:
        return 0.0
    initial = tax_after_rebate * rate
    total_before_cess = tax_after_rebate + initial
    threshold_total = _tax_before_cess_cached(start, regime_key, age_category, resident)
    max_allowed = threshold_total + (income - start)
    final_total = min(total_before_cess, max_allowed)
    return excel_round(max(final_total - tax_after_rebate, 0.0), 2)


def month_label(month_start: date) -> str:
    return month_start.strftime("%b %Y")


def _service_days(join_date: date, fy_start: date, fy_end: date) -> int:
    effective = max(join_date, fy_start)
    if effective > fy_end:
        return 0
    return (fy_end - effective).days + 1


def _allocate_claims(df: pd.DataFrame, total: float, weight_col: str, out_col: str) -> pd.DataFrame:
    df[out_col] = allocate_by_weights(total, df[weight_col].tolist(), digits=2)
    return df


# ── Core calculation ───────────────────────────────────────────────────────────

def calculate_regime(inputs: CalculatorInputs, regime_key: str) -> RegimeResult:
    inputs = inputs.normalized()
    fy_start, fy_end = financial_year_bounds(inputs.financial_year)
    monthly_template = build_monthly_template(inputs.annual_ctc, inputs.pf_option, regime_key)
    month_starts = month_starts_for_fy(inputs.financial_year)
    warnings: List[str] = []

    if monthly_template["special_allowance"] < COMPANY_CONFIG.minimum_special_allowance:
        warnings.append("Special Allowance is negative. Increase CTC or review fixed-component values.")

    rows: List[Dict] = []
    annual_ctc_paid_exact = 0.0
    monthly_ctc_exact = inputs.annual_ctc / 12.0

    for ms in month_starts:
        factor = employment_factor(ms, inputs.join_date, fy_start, fy_end)
        basic = excel_round(monthly_template["basic"] * factor, 2)
        hra = excel_round(monthly_template["hra"] * factor, 2)
        lta = excel_round(monthly_template["lta"] * factor, 2)
        periodicals = excel_round(monthly_template["periodicals"] * factor, 2)
        phone = excel_round(monthly_template["phone_internet"] * factor, 2)
        special = excel_round(monthly_template["special_allowance"] * factor, 2)
        employer_pf = excel_round(monthly_template["employer_pf"] * factor, 2)
        employee_pf = excel_round(monthly_template["employee_pf"] * factor, 2)
        gross = excel_round(basic + hra + lta + periodicals + phone + special, 2)
        total_ctc = excel_round(gross + employer_pf, 2)
        prof_tax = professional_tax_for_month(gross, ms.month) if factor > 0 else 0.0

        hra_exemption = 0.0
        if regime_key == "old" and gross > 0 and inputs.monthly_rent > 0:
            rent_less = max(inputs.monthly_rent - (basic * 0.10), 0.0)
            pct_limit = basic * (0.50 if inputs.metro_city else 0.40)
            hra_exemption = excel_round(min(hra, rent_less, pct_limit), 2)

        annual_ctc_paid_exact += monthly_ctc_exact * factor
        rows.append({
            "Month": month_label(ms),
            "Month Start": ms,
            "Employment Factor": factor,
            "Basic": basic,
            "HRA": hra,
            "LTA": lta,
            "Periodicals & Journals": periodicals,
            "Telephone & Internet": phone,
            "Special Allowance": special,
            "Gross Salary": gross,
            "Employer PF": employer_pf,
            "Employee PF": employee_pf,
            "Professional Tax": prof_tax,
            "HRA Exemption": hra_exemption,
            "Total CTC": total_ctc,
        })

    monthly_df = pd.DataFrame(rows)

    total_phone = float(monthly_df["Telephone & Internet"].sum())
    total_lta = float(monthly_df["LTA"].sum())
    total_periodicals = float(monthly_df["Periodicals & Journals"].sum())

    phone_claim = min(inputs.phone_internet_claim, total_phone)
    lta_claim = min(inputs.lta_claim, total_lta) if regime_key == "old" else 0.0
    periodicals_claim = min(inputs.periodicals_claim, total_periodicals) if regime_key == "old" else 0.0

    monthly_df = _allocate_claims(monthly_df, phone_claim, "Telephone & Internet", "Phone Exemption")
    monthly_df = _allocate_claims(monthly_df, lta_claim, "LTA", "LTA Exemption")
    monthly_df = _allocate_claims(monthly_df, periodicals_claim, "Periodicals & Journals", "Periodicals Exemption")
    monthly_df["Salary Exemptions"] = (
        monthly_df["HRA Exemption"]
        + monthly_df["Phone Exemption"]
        + monthly_df["LTA Exemption"]
        + monthly_df["Periodicals Exemption"]
    )

    gross_salary_fy = float(monthly_df["Gross Salary"].sum())
    employer_pf_fy = float(monthly_df["Employer PF"].sum())
    employee_pf_fy = float(monthly_df["Employee PF"].sum())
    prof_tax_fy = float(monthly_df["Professional Tax"].sum())
    annual_ctc_paid_fy = excel_round(annual_ctc_paid_exact, 2)

    total_salary_exemptions = {
        "HRA Exemption": float(monthly_df["HRA Exemption"].sum()),
        "Telephone & Internet Exemption": float(monthly_df["Phone Exemption"].sum()),
        "LTA Exemption": float(monthly_df["LTA Exemption"].sum()),
        "Periodicals & Journals Exemption": float(monthly_df["Periodicals Exemption"].sum()),
    }

    gross_after_exemptions = gross_salary_fy - sum(total_salary_exemptions.values())
    sd_cap = COMPANY_CONFIG.standard_deduction_old if regime_key == "old" else COMPANY_CONFIG.standard_deduction_new
    standard_deduction = min(sd_cap, max(gross_after_exemptions, 0.0))
    prof_tax_deduction = prof_tax_fy if regime_key == "old" else 0.0
    salary_income = max(gross_after_exemptions - standard_deduction - prof_tax_deduction, 0.0)

    # House property income
    house_property_income = 0.0
    if regime_key == "old":
        house_property_income = -min(inputs.home_loan_interest_self_occupied, COMPANY_CONFIG.self_occupied_home_loan_cap_old)

    # Employer NPS deduction (80CCD(2)) — available BOTH regimes
    annual_basic = float(monthly_df["Basic"].sum())
    employer_nps_cap_rate = COMPANY_CONFIG.section_80ccd_2_rate_govt if inputs.is_govt_employer else COMPANY_CONFIG.section_80ccd_2_rate_private
    employer_nps_deduction = excel_round(
        min(inputs.employer_nps_pct / 100.0 * annual_basic, employer_nps_cap_rate * annual_basic),
        2,
    )

    # Chapter VI-A deductions (old regime only, except 80CCD(2))
    chapter_via_deductions: Dict[str, float] = {
        "Section 80C (EPF + investments)": 0.0,
        "Section 80CCD(1B) — Additional NPS": 0.0,
        "Section 80CCD(2) — Employer NPS": employer_nps_deduction,
        "Section 80D — Health Insurance": 0.0,
        "Section 80DD — Disabled Dependent": 0.0,
        "Section 80DDB — Specified Disease": 0.0,
        "Section 80E — Education Loan": 0.0,
        "Section 80EE — Home Loan (2016-17)": 0.0,
        "Section 80EEA — Affordable Housing": 0.0,
        "Section 80G — Donations": 0.0,
        "Section 80GG — Rent (no HRA)": 0.0,
        "Section 80TTA/TTB — Interest": 0.0,
        "Section 80U — Self Disability": 0.0,
    }

    if regime_key == "old":
        # 80C
        chapter_via_deductions["Section 80C (EPF + investments)"] = min(
            employee_pf_fy + inputs.other_80c_investments, COMPANY_CONFIG.section_80c_cap
        )
        # 80CCD(1B)
        chapter_via_deductions["Section 80CCD(1B) — Additional NPS"] = min(
            inputs.nps_80ccd_1b, COMPANY_CONFIG.section_80ccd_1b_cap
        )
        # 80D
        is_senior_self = inputs.age_category in ("senior", "super_senior")
        self_limit = COMPANY_CONFIG.section_80d_parents_senior if is_senior_self else COMPANY_CONFIG.section_80d_self_family
        parent_limit = COMPANY_CONFIG.section_80d_parents_senior if inputs.parents_senior_citizen else COMPANY_CONFIG.section_80d_parents_normal
        chapter_via_deductions["Section 80D — Health Insurance"] = (
            min(inputs.medical_80d_self, self_limit) + min(inputs.medical_80d_parents, parent_limit)
        )
        # 80DD
        if inputs.medical_80dd > 0:
            chapter_via_deductions["Section 80DD — Disabled Dependent"] = (
                COMPANY_CONFIG.section_80dd_severe if inputs.disability_severe_80dd else COMPANY_CONFIG.section_80dd_normal
            )
        # 80DDB
        is_senior_ddb = inputs.age_category in ("senior", "super_senior")
        ddb_limit = COMPANY_CONFIG.section_80ddb_senior if is_senior_ddb else COMPANY_CONFIG.section_80ddb_normal
        chapter_via_deductions["Section 80DDB — Specified Disease"] = min(inputs.medical_80ddb, ddb_limit)
        # 80E
        chapter_via_deductions["Section 80E — Education Loan"] = inputs.education_loan_80e
        # 80EE / 80EEA (mutually exclusive — take whichever is input)
        chapter_via_deductions["Section 80EE — Home Loan (2016-17)"] = min(
            inputs.home_loan_interest_80ee, COMPANY_CONFIG.section_80ee_cap
        )
        chapter_via_deductions["Section 80EEA — Affordable Housing"] = min(
            inputs.home_loan_interest_80eea, COMPANY_CONFIG.section_80eea_cap
        )
        # 80G
        chapter_via_deductions["Section 80G — Donations"] = inputs.eligible_80g
        # 80GG (only if employee has no HRA in salary and no HRA exemption)
        hra_total = sum(monthly_df["HRA"].tolist())
        if inputs.rent_paid_80gg > 0 and hra_total <= 0:
            total_income_estimate = salary_income + house_property_income + inputs.other_income
            limit_a = COMPANY_CONFIG.section_80gg_monthly * 12
            limit_b = 0.25 * max(total_income_estimate, 0)
            limit_c = max(inputs.rent_paid_80gg - 0.10 * max(total_income_estimate, 0), 0)
            chapter_via_deductions["Section 80GG — Rent (no HRA)"] = min(limit_a, limit_b, limit_c)
        # 80TTA / 80TTB
        if inputs.age_category in ("senior", "super_senior"):
            chapter_via_deductions["Section 80TTA/TTB — Interest"] = min(
                inputs.savings_interest_80ttb, COMPANY_CONFIG.section_80ttb_cap
            )
        else:
            chapter_via_deductions["Section 80TTA/TTB — Interest"] = min(
                inputs.savings_interest_80tta, COMPANY_CONFIG.section_80tta_cap
            )
        # 80U
        if inputs.self_disability_80u:
            chapter_via_deductions["Section 80U — Self Disability"] = (
                COMPANY_CONFIG.section_80u_severe if inputs.self_disability_severe else COMPANY_CONFIG.section_80u_normal
            )

    gross_total_income = salary_income + house_property_income + inputs.other_income
    # Remove 80CCD(2) from VI-A sum when computing taxable (it's above-the-line under both regimes)
    via_sum = sum(v for k, v in chapter_via_deductions.items() if "80CCD(2)" not in k)
    taxable_income = max(gross_total_income - via_sum - employer_nps_deduction, 0.0)
    taxable_income = excel_round(taxable_income, 2)

    slab_tax_amt = slab_tax(taxable_income, regime_key, inputs.age_category)
    rebate_amt = rebate_87a(taxable_income, slab_tax_amt, regime_key, inputs.resident_individual)
    tax_after_rebate = max(slab_tax_amt - rebate_amt, 0.0)
    surcharge_amt = _surcharge_cached(taxable_income, tax_after_rebate, regime_key, inputs.age_category, inputs.resident_individual)
    cess = excel_round((tax_after_rebate + surcharge_amt) * 0.04, 2)
    annual_tax = excel_round(tax_after_rebate + surcharge_amt + cess, 2)
    annual_tax_tds = excel_round(annual_tax, 0)

    taxable_weight = (monthly_df["Gross Salary"] - monthly_df["Salary Exemptions"]).clip(lower=0.0)
    active_mask = monthly_df["Employment Factor"] > 0
    weights = [w if a else 0.0 for w, a in zip(taxable_weight.tolist(), active_mask.tolist())]
    if sum(weights) <= 0:
        weights = [1.0 if a else 0.0 for a in active_mask.tolist()]

    monthly_tds = allocate_by_weights(annual_tax_tds, weights, digits=0)
    monthly_df["TDS"] = monthly_tds
    monthly_df["Take Home Before TDS"] = monthly_df["Gross Salary"] - monthly_df["Employee PF"] - monthly_df["Professional Tax"]
    monthly_df["Net Take Home"] = monthly_df["Take Home Before TDS"] - monthly_df["TDS"]

    annual_take_home_before_tds = float(monthly_df["Take Home Before TDS"].sum())
    annual_take_home_after_tds = float(monthly_df["Net Take Home"].sum())
    effective_rate = (annual_tax / gross_salary_fy * 100.0) if gross_salary_fy > 0 else 0.0
    active_months = int((monthly_df["Employment Factor"] > 0).sum())
    monthly_avg = annual_take_home_after_tds / active_months if active_months else 0.0

    return RegimeResult(
        regime_key=regime_key,
        regime_label=REGIMES[regime_key],
        financial_year=inputs.financial_year,
        inputs=inputs,
        monthly_template=monthly_template,
        monthly_df=monthly_df,
        annual_ctc_input=inputs.annual_ctc,
        annual_ctc_paid_in_fy=annual_ctc_paid_fy,
        gross_salary_paid_in_fy=gross_salary_fy,
        employer_pf_paid_in_fy=employer_pf_fy,
        employee_pf_paid_in_fy=employee_pf_fy,
        professional_tax_paid_in_fy=prof_tax_fy,
        active_months=active_months,
        service_days=_service_days(inputs.join_date, fy_start, fy_end),
        salary_exemptions=total_salary_exemptions,
        chapter_via_deductions=chapter_via_deductions,
        standard_deduction=standard_deduction,
        house_property_income=house_property_income,
        other_income=inputs.other_income,
        gross_total_income=gross_total_income,
        taxable_income=taxable_income,
        slab_tax=slab_tax_amt,
        rebate_87a=rebate_amt,
        tax_after_rebate=tax_after_rebate,
        surcharge=surcharge_amt,
        cess=cess,
        annual_tax=annual_tax,
        annual_take_home_before_tds=annual_take_home_before_tds,
        annual_take_home_after_tds=annual_take_home_after_tds,
        effective_tax_rate_on_gross=effective_rate,
        monthly_take_home_avg=monthly_avg,
        employer_nps_deduction=employer_nps_deduction,
        warnings=warnings,
    )


def calculate_both_regimes(inputs: CalculatorInputs) -> Dict[str, RegimeResult]:
    n = inputs.normalized()
    return {"old": calculate_regime(n, "old"), "new": calculate_regime(n, "new")}


def recommended_regime(results: Dict[str, RegimeResult]) -> str:
    diff = abs(results["old"].annual_tax - results["new"].annual_tax)
    if diff < 0.01:
        return "same"
    return "old" if results["old"].annual_tax < results["new"].annual_tax else "new"


def comparison_table(results: Dict[str, RegimeResult]) -> pd.DataFrame:
    rows = []
    for key in ["old", "new"]:
        r = results[key]
        rows.append({
            "Regime": r.regime_label,
            "CTC Paid in FY": r.annual_ctc_paid_in_fy,
            "Gross Salary": r.gross_salary_paid_in_fy,
            "Salary Exemptions": sum(r.salary_exemptions.values()),
            "Standard Deduction": r.standard_deduction,
            "Chapter VIA Deductions": sum(r.chapter_via_deductions.values()),
            "Taxable Income": r.taxable_income,
            "Annual Tax": r.annual_tax,
            "Annual Take Home": r.annual_take_home_after_tds,
            "Avg Monthly Take Home": r.monthly_take_home_avg,
        })
    return pd.DataFrame(rows)


def annual_breakup_frame(result: RegimeResult) -> pd.DataFrame:
    rows = [
        ("Actual CTC paid in FY", result.annual_ctc_paid_in_fy),
        ("Less: Employer PF", result.employer_pf_paid_in_fy),
        ("Gross Salary", result.gross_salary_paid_in_fy),
        ("Less: HRA Exemption", result.salary_exemptions.get("HRA Exemption", 0.0)),
        ("Less: Telephone & Internet Exemption", result.salary_exemptions.get("Telephone & Internet Exemption", 0.0)),
        ("Less: LTA Exemption", result.salary_exemptions.get("LTA Exemption", 0.0)),
        ("Less: Periodicals & Journals Exemption", result.salary_exemptions.get("Periodicals & Journals Exemption", 0.0)),
        ("Less: Standard Deduction", result.standard_deduction),
        ("Less: Professional Tax Deduction", result.professional_tax_paid_in_fy if result.regime_key == "old" else 0.0),
        ("Add: House Property Income / (Loss)", result.house_property_income),
        ("Add: Other Income", result.other_income),
        ("Less: Chapter VIA Deductions (incl. Employer NPS)", sum(result.chapter_via_deductions.values())),
        ("= Taxable Income", result.taxable_income),
        ("Slab Tax", result.slab_tax),
        ("Less: Rebate u/s 87A", result.rebate_87a),
        ("Tax After Rebate", result.tax_after_rebate),
        ("Surcharge", result.surcharge),
        ("Health & Education Cess @ 4%", result.cess),
        ("= Total Annual Tax (TDS)", result.annual_tax),
        ("Less: Employee PF", result.employee_pf_paid_in_fy),
        ("Less: Professional Tax", result.professional_tax_paid_in_fy),
        ("Net Take Home (Before TDS spread)", result.annual_take_home_before_tds),
        ("Net Annual Take Home", result.annual_take_home_after_tds),
    ]
    return pd.DataFrame(rows, columns=["Particulars", "Amount"])


def input_snapshot_frame(inputs: CalculatorInputs) -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Financial Year", inputs.financial_year),
            ("Annualized CTC (₹)", inputs.annual_ctc),
            ("Joining Date", inputs.join_date.isoformat()),
            ("PF Option", PF_OPTIONS[inputs.pf_option]),
            ("Age Category", AGE_CATEGORIES[inputs.age_category]),
            ("Monthly Rent (₹)", inputs.monthly_rent),
            ("Metro City", "Yes" if inputs.metro_city else "No"),
            ("Phone/Internet Claim (₹)", inputs.phone_internet_claim),
            ("LTA Claim (₹)", inputs.lta_claim),
            ("Periodicals Claim (₹)", inputs.periodicals_claim),
            ("Other 80C Investments (₹)", inputs.other_80c_investments),
            ("NPS 80CCD(1B) (₹)", inputs.nps_80ccd_1b),
            ("Employer NPS %", inputs.employer_nps_pct),
            ("Health Insurance Self (₹)", inputs.medical_80d_self),
            ("Health Insurance Parents (₹)", inputs.medical_80d_parents),
            ("Parents Senior Citizen", "Yes" if inputs.parents_senior_citizen else "No"),
            ("Education Loan Interest (₹)", inputs.education_loan_80e),
            ("Home Loan Interest Sec24(b) (₹)", inputs.home_loan_interest_self_occupied),
            ("Home Loan 80EEA (₹)", inputs.home_loan_interest_80eea),
            ("Savings Interest 80TTA/TTB (₹)", inputs.savings_interest_80tta or inputs.savings_interest_80ttb),
            ("Donations 80G (₹)", inputs.eligible_80g),
            ("Other Income (₹)", inputs.other_income),
        ],
        columns=["Input", "Value"],
    )


# ── Tax Optimizer ─────────────────────────────────────────────────────────────

def tax_optimizer(inputs: CalculatorInputs, results: Dict[str, RegimeResult]) -> List[Dict]:
    """Return ranked investment/deduction suggestions to reduce tax in old regime."""
    suggestions = []
    n = inputs.normalized()
    old = results["old"]
    new = results["new"]

    # Check if old regime is recommended at all
    old_is_better = old.annual_tax < new.annual_tax
    regime_gap = abs(old.annual_tax - new.annual_tax)
    if not old_is_better:
        suggestions.append({
            "priority": "high",
            "section": "Regime Choice",
            "action": "Switch to New Tax Regime",
            "potential_saving": regime_gap,
            "description": (
                f"New regime saves ₹{regime_gap:,.0f} over old regime for this income and deduction profile. "
                "Consider opting for new regime."
            ),
        })

    # 80C gap
    employee_pf = old.employee_pf_paid_in_fy
    current_80c = min(employee_pf + n.other_80c_investments, COMPANY_CONFIG.section_80c_cap)
    gap_80c = max(COMPANY_CONFIG.section_80c_cap - current_80c, 0)
    if gap_80c > 0 and old_is_better:
        top_rate = 0.30 if old.taxable_income > 1_000_000 else (0.20 if old.taxable_income > 500_000 else 0.05)
        saving = excel_round(gap_80c * top_rate * 1.04, 0)
        suggestions.append({
            "priority": "high",
            "section": "Section 80C",
            "action": f"Invest ₹{gap_80c:,.0f} more in ELSS / PPF / NSC to maximize 80C",
            "potential_saving": saving,
            "description": f"80C is not fully utilized. Investing ₹{gap_80c:,.0f} can save up to ₹{saving:,.0f} in tax (est.).",
        })

    # 80CCD(1B) — NPS
    nps_gap = max(COMPANY_CONFIG.section_80ccd_1b_cap - n.nps_80ccd_1b, 0)
    if nps_gap > 0 and old_is_better:
        top_rate = 0.30 if old.taxable_income > 1_000_000 else 0.20
        saving = excel_round(nps_gap * top_rate * 1.04, 0)
        suggestions.append({
            "priority": "high",
            "section": "Section 80CCD(1B)",
            "action": f"Contribute ₹{nps_gap:,.0f} more to NPS for additional deduction",
            "potential_saving": saving,
            "description": f"NPS 80CCD(1B) allows ₹50,000 deduction beyond 80C. ₹{saving:,.0f} potential tax savings.",
        })

    # 80D — health insurance
    is_senior = n.age_category in ("senior", "super_senior")
    self_limit = 50_000 if is_senior else 25_000
    parent_limit = 50_000 if n.parents_senior_citizen else 25_000
    d_gap_self = max(self_limit - n.medical_80d_self, 0)
    d_gap_parent = max(parent_limit - n.medical_80d_parents, 0)
    if (d_gap_self > 0 or d_gap_parent > 0) and old_is_better:
        suggestions.append({
            "priority": "medium",
            "section": "Section 80D",
            "action": "Consider health insurance for self/family and parents",
            "potential_saving": None,
            "description": (
                f"Health insurance limit: Self/family ₹{self_limit:,}, Parents ₹{parent_limit:,}. "
                "Premium is a real expense with tax benefit."
            ),
        })

    # Employer NPS suggestion
    if n.employer_nps_pct < (14 if n.is_govt_employer else 10):
        max_rate = 14 if n.is_govt_employer else 10
        suggestions.append({
            "priority": "medium",
            "section": "Section 80CCD(2)",
            "action": f"Ask HR if Employer NPS benefit (up to {max_rate}% of basic) is available",
            "potential_saving": None,
            "description": "Employer NPS contribution is deductible in BOTH old and new regimes. It effectively reduces taxable salary.",
        })

    return sorted(suggestions, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]])


# ── FY comparison helper ───────────────────────────────────────────────────────

def compare_financial_years(inputs: CalculatorInputs, regime_key: str) -> Dict[str, RegimeResult]:
    """Return results for both FY 2025-26 and FY 2026-27 for comparison."""
    results = {}
    for fy in ["FY 2025-26", "FY 2026-27"]:
        fy_inputs = CalculatorInputs(**{**inputs.__dict__, "financial_year": fy, "join_date": date(int(fy[3:7]), 4, 1)})
        results[fy] = calculate_regime(fy_inputs.normalized(), regime_key)
    return results


def summary_cards_payload(result: RegimeResult) -> Dict[str, float]:
    return {
        "Actual CTC Paid in FY": result.annual_ctc_paid_in_fy,
        "Gross Salary Paid in FY": result.gross_salary_paid_in_fy,
        "Annual Tax": result.annual_tax,
        "Annual Net Take Home": result.annual_take_home_after_tds,
    }
