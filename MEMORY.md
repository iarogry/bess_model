# Project Memory - Battery Simulator

## Current State (2025 Simulation Baseline)
- **Logic:** Multi-Strategy Dynamic LP Optimization (V5 SciPy).
- **Economic Model:** Smart Tariff Allocation. Transit charging for arbitrage does NOT pay distribution/transmission tariffs (only demand and losses are taxed).
- **Performance:** ~730 cycles/year (Exactly 2.0 cycles/day) with 1MWh/2.5MW setup.
- **Revenue:** 4.08M UAH/year.
- **ROI:** Estimated 1.6 years (6.75M CAPEX / 4.08M Revenue).
- **Optimization:** Bulk insertion implemented (8,760 hourly records committed in one transaction).

## Data Fetching Architecture
- **Primary Source:** ENTSO-E Transparency Platform (via `ENTSOEFetcher`).
- **Deprecated:** OREE fetchers (fetch_oree.py, fetch_oree_real.py) are no longer used.
- **Integration:** Automated refresh in `run_simulation.py` if `ENTSOE_TOKEN` is present in `.env`.

## Project Status
- **GitHub:** Deployed to https://github.com/iarogry/bess_model.
- **Security:** Credentials secured in `.env`, `.gitignore` in place.
- **Database:** SQLite local staging + PostgreSQL analytics sync.
- **Units:** Fixed MW to kW inconsistency. All internal optimizer values are in kW/kWh.
