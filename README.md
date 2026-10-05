# GridNest Energy MVP

## Features
- Half-hourly load, PV and flexible-load data
- TOU tariff cost calculation
- Baseline vs optimised flexible-load schedule
- Peak demand and grid import comparison
- Interactive Plotly charts
- CSV export

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Required CSV columns
- timestamp
- household_load_kw
- pv_kw
- flexible_load_kw

## Deploy online
1. Create a GitHub repository.
2. Upload `app.py`, `requirements.txt`, and `sample_energy_data.csv`.
3. Deploy the repository on Streamlit Community Cloud.
4. Put the resulting public app link in the final report.

This is a proof-of-concept MVP, not automatic appliance control.
