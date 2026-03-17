# Income Tax & Take-Home Salary Calculator

A Streamlit app for employees to estimate:
- annual income tax
- monthly TDS
- monthly take-home salary
- old vs new regime comparison
- PF option impact
- joining-date-based proration for the selected financial year

This project is built around the salary structure in your workbook:
- Basic = 50% of (CTC less employer PF)
- HRA = 40% of Basic
- PF option 1 = 12% on Basic Salary
- PF option 2 = 12% on ₹15,000 statutory ceiling
- LTA and Periodicals & Journals are included only under the Old Tax Regime structure
- Telephone & Internet is included as a monthly component and treated as a claim-based reimbursement input

## Financial years supported
- FY 2025-26
- FY 2026-27

## Tech stack
- Python
- Streamlit
- Plotly
- Pandas
- OpenPyXL

No OpenAI key or any other API key is required.

## Project files
- `app.py` - Streamlit user interface
- `tax_engine.py` - salary, tax, TDS, and take-home logic
- `company_config.py` - company salary structure constants and tax/source metadata
- `export_utils.py` - Excel export builder
- `.streamlit/config.toml` - theme settings
- `requirements.txt` - Python dependencies

## How to run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to deploy from GitHub without API keys
### Option 1: Streamlit Community Cloud
1. Create a new GitHub repository.
2. Upload all files from this folder.
3. Go to Streamlit Community Cloud.
4. Connect your GitHub account.
5. Choose the repo and set the app entry point to `app.py`.
6. Deploy.

### Option 2: Render
1. Create a new Web Service from your GitHub repo.
2. Runtime: Python
3. Build command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start command:
   ```bash
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

## Important assumptions
1. The app assumes resident individual tax treatment.
2. The app uses normal slab-rate income only; it does not separately model special-rate capital gains.
3. Professional tax is modeled as ₹200 per eligible month and ₹300 in February, following the workbook pattern.
4. First month salary is prorated by calendar days from joining date to month-end.
5. Telephone & Internet exemption is treated as claim-based and capped to the component actually paid in the financial year.
6. Periodicals & Journals is kept as an optional old-regime claim because company payroll treatment can vary.
7. Final payroll values can differ slightly if finance uses a different proration, proof cut-off, or rounding method.

## Tax law references used
These URLs are also shown in the app:
- https://incometaxindia.gov.in/budgets%20and%20bills/2025/budget_speech-2025.pdf
- https://incometaxindia.gov.in/Acts/Finance%20Acts/2025/102520000000148617.htm
- https://incometaxindia.gov.in/Charts%20%20Tables/Tax%20rates.htm
- https://incometaxindia.gov.in/charts%2520%2520tables/deductions.htm
- https://incometaxindia.gov.in/Charts%2520%2520Tables/Benefits_available_only_to_Resident_Persons.htm
- https://incometaxindia.gov.in/Budgets%2520and%2520Bills/2026/memo-2026.pdf
- https://incometaxindia.gov.in/Documents/Budget2026/FAQs-Budget-2026.pdf

## Suggested next step for your HR team
If you want to make this even closer to payroll, the next enhancement should be:
- actual month-wise payroll cut-off dates
- reimbursement proof status workflow
- salary revision / increment month
- employee master upload via Excel
- PDF salary summary download
