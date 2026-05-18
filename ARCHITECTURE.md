# Battery Simulator for Solar PV + Storage

## Project Overview

**Goal:** Create a Python application that simulates energy storage (battery) behavior for a 2.5 MW solar photovoltaic (PV) power plant in Chervonohrad, Ukraine.
**Key Objective:** Achieve 500-600 cycles per year to reach a 5-year ROI.

---

## Architecture (V5 - Current)

### 1. **Core Components**

#### 1.1 Optimization Engine (`src/optimizer_v5_scipy.py`)
- **Logic:** Multi-Strategy Dual Optimization with Dynamic Config
  - **Dynamic Loading:** Parameters (Capacity, SOC, Tariffs) are loaded from `system_config` table (populated via `data/config.csv`).
  - **Strategy A (Efficiency):** Max 1.0 cycle/day.
  - **Strategy B (Arbitrage):** Max 2.0 cycles/day.
  - **Decision:** Selects strategy with highest `Net Profit = Gross Revenue - Degradation Cost`.
- **Operating Limits:**
  - SOC Range: Dynamic (currently 13% to 97%).
  - Round-Trip Efficiency (RTE): 80%.
- **Algorithm:** Linear Programming (SciPy linprog) with 24-hour global window.

#### 1.2 Data Management & Cleanup
- **Cleanup:** `dispatch_results` and `daily_summary` are truncated in both SQLite and PostgreSQL before each run.
- **Sync:** Automated push to PostgreSQL (`battery_sim` DB) after each successful simulation.

---

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
