# Project Memory - Battery Simulator

## Current State (2025 Simulation Baseline - REAL DATA)
- **Logic:** Multi-Strategy Dynamic LP Optimization (V5 SciPy).
- **Economic Model:** Smart Tariff Allocation (Arbitrage transit is tariff-free).
- **Performance (1MWh / 2.5MW):** ~4,149 cycles/year (High frequency arbitrage).
- **Revenue:** 28,201,331 UAH/year (Based on real 2025 volatility).
- **Degradation:** 12.45% per year (due to high cycle count).
- **Optimization:** Bulk insertion (8,760 records) implemented for PostgreSQL.

## Architecture
- **Primary Database:** Centralized PostgreSQL (`battery_sim` DB).
- **Connectivity:** `src/db_connector.py` with connection pooling.
- **Data Integrity:** Real PV, Demand, and Price profiles fetched via SQL.
- **Units:** Automatic MW/MWh to kW/kWh conversion in mapping layer.

## Project Status
- **GitHub:** Deployed to https://github.com/iarogry/bess_model.
- **Security:** Credentials secured in `.env`.
- **Backend:** Pure PostgreSQL architecture (SQLite fully removed).
