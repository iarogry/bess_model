# Project Memory - Battery Simulator

## Current State (2025 Simulation Baseline - BUG FIXED)
- **Logic:** Multi-Strategy Dynamic LP Optimization (V5 SciPy).
- **Bug Fix:** Simultaneous charge/discharge loophole closed. Enforced strict energy partitioning (AC Bus Balance).
- **Economic Model:** Smart Tariff Allocation (Arbitrage transit is tariff-free).
- **Performance (1MWh / 2.5MW):** ~3,809.5 cycles/year (High frequency arbitrage).
- **Financial Balance:** -5,926,018 UAH/year (Includes total plant energy costs).
- **Degradation:** 11.43% per year.
- **Optimization:** Bulk insertion (8,760 records) implemented for PostgreSQL.

## Architecture
- **Primary Database:** Centralized PostgreSQL (`battery_sim` DB).
- **AC Bus Balance:** Added Constraint 7 to prevent double-counting of battery discharge and grid imports.
- **Data Integrity:** Real PV, Demand, and Price profiles fetched via SQL.
- **Units:** Automatic MW/MWh to kW/kWh conversion.

## Project Status
- **GitHub:** Deployed to https://github.com/iarogry/bess_model.
- **Security:** Credentials secured in `.env`.
- **Integrity:** Mathematical model verified to prevent energy creation/double-counting.
