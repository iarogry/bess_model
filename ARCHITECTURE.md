# Battery Simulator for Solar PV + Storage

## Project Overview

**Goal:** Create a Python application that simulates energy storage (battery) behavior for a 2.5 MW solar photovoltaic (PV) power plant in Chervonohrad, Ukraine.
**Key Objective:** Achieve 500-600 cycles per year to reach a 5-year ROI.

---

## Architecture (V5 - Current)

### 1. **Core Components**

#### 1.1 Data Fetching Pipeline
- **Primary Source:** ENTSO-E API. Used for fetching hourly day-ahead prices for the Ukraine bidding zone.
- **Redundancy:** All OREE-based scrapers are deprecated in favor of the official ENTSO-E interface.
- **Units:** API data in MW/MWh is automatically converted to internal kW/kWh during the configuration mapping phase.

#### 1.2 Optimization Engine (`src/optimizer_v5_scipy.py`)
- **Logic:** Multi-Strategy Dual Optimization with Dynamic Config
  - **Dynamic Loading:** Parameters (Capacity, SOC, Tariffs) are loaded from `system_config` table (populated via `data/config.csv`).
  - **Strategy A (Efficiency):** Max 1.0 cycle/day.
  - **Strategy B (Arbitrage):** Max 2.0 cycles/day.
  - **Decision:** Selects strategy with highest `Net Profit = Gross Revenue - Degradation Cost`.
- **Operating Limits:**
  - SOC Range: Dynamic (currently 13% to 97%).
  - Round-Trip Efficiency (RTE): 80%.
- **Algorithm:** Linear Programming (SciPy linprog) with 24-hour global window.

#### 1.2 Data Management & Performance
- **Bulk Insert:** `AnnualSimulator` collects all daily results and uses `executemany` to commit 8,760 records in a single transaction, eliminating N+1 query bottlenecks.
- **Cleanup:** `dispatch_results` and `daily_summary` are truncated before each run.
- **Sync:** Results are synced to PostgreSQL (`battery_sim` DB) after the simulation.

---

### 2. Economic Logic (Smart Tariffs)
- **Arbitrage Transit:** Grid-to-Battery energy is treated as transit. Distribution and transmission tariffs are applied ONLY to local demand and technical battery losses (20%).
- **Degradation Cost:** Based on CAPEX (6,750 UAH/kWh) and expected lifespan.

### 2. **Data Layers**
- **Source:** SQLite (`data.db`) for execution.
- **Import:** `import_csv_data.py` (reads `data/*.csv`).
- **Tables:** `prices`, `pv_profile`, `demand`, `system_config`.

---

### 3. **Tech Stack**

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Scientific computing |
| Optimization | SciPy.optimize.linprog | Fast LP solver |
| Data | pandas, SQLite, PostgreSQL | Time-series and Analysis |

---

## Success Criteria
- ✅ Simulator runs 1-year in < 30 seconds.
- ✅ Automated cleanup and SQL sync.
- 🟡 **Current Performance:** ~344 cycles/year (at 1MWh/2.5MW).
- 🟡 **Target:** 500-600 cycles/year.

**Status:** 🟢 Dynamic Config & SQL Integration complete.
**Updated:** 2026-05-15
