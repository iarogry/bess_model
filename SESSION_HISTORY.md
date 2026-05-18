# Project History & Change Log

## Session: 2026-05-15
**Goal:** Transition to high-volatility modeling, PostgreSQL integration, and dynamic economics.

### 1. User Requests & Feedback
- **Request:** Fix arbitrage logic (V5 wasn't cycling enough).
- **Request:** Use dynamic cost based on 6750 UAH/kWh CAPEX and 6000 cycles.
- **Request:** Compare "Single Cycle" vs "Double Cycle" daily to maximize profit.
- **Request:** Expand SOC limits from 20-80% to 13-97%.
- **Feedback:** "235 cycles is too low; target 500-600 cycles for 5-year ROI."
- **Request:** Enable data viewing in local PostgreSQL (Odoo instance).
- **Request:** Provide CSV templates for manual data updates.

### 2. Implemented Changes
- **Fixed SoC Dynamics:** Corrected sign errors where SoC increased during discharge.
- **Multi-Strategy Wrapper:** Added `optimize_day_multi_strategy` to `Optimizer24hV5SciPy`.
- **Dynamic Costing:** Added `battery_degradation_cost_per_kwh` property to `EnergySourceConfig`.
- **Database Schema Fix:** Changed `prices` table to allow hourly data (removed UNIQUE constraint on date).
- **PostgreSQL Integration:** 
    - Created `migrate_to_postgres.py` using `iaroslav` credentials.
    - Automated sync at the end of `run_simulation.py`.
- **Data Workflow:** 
    - Created `import_csv_data.py`.
    - Generated templates: `data/prices.csv`, `data/pv_gen.csv`, `data/demand.csv`.

### Session 5: Optimization & Deployment (2026-05-18)
- **Economic Logic:** Implemented "Smart Tariff Allocation". Arbitrage transit is now tariff-free, increasing cycles to 730/year.
- **Performance:** Fixed N+1 query issue in `simulator.py` via bulk `executemany` insertion.
- **GitHub:** Deployed project to `https://github.com/iarogry/bess_model`.
- **Security:** Moved credentials to `.env` and added `.gitignore`.
- **Bugfixes:** Fixed `EnergySourceConfig` loading issues and venv dependencies.
