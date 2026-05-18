# Battery Simulator for Solar PV + Storage 🔋⚡

A Python application for simulating energy storage (battery) behavior in a 2.5 MW solar PV power plant in Chervonohrad, Ukraine.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run a simulation
python scripts/run_simulation.py \
  --site chervonohrad_2.5mw \
  --start 2025-01-01 \
  --end 2025-12-31 \
  --battery-capacity 5000
```

## What This Does

1. **Models PV Generation** — Converts hourly solar irradiance → kW (2,500 MW site)
2. **Simulates Battery** — Tracks charge/discharge cycles, efficiency loss, degradation
3. **Optimizes Revenue** — Uses market prices to decide when to charge/discharge
4. **Calculates Economics** — Total revenue, battery wear, ROI

## Key Features

- 📊 Hourly simulation (based on РДН market data from Excel)
- 🔋 Realistic battery model (SoC, efficiency, degradation curves)
- 💰 Revenue optimization via Linear Programming
- 📈 Time-series output (CSV, JSON)
- 🌐 REST API (FastAPI) for integration
- 🔌 Odoo module for monitoring & reporting

## Architecture Overview

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full design.

**Core modules:**
- `battery_simulator.battery` — Battery model
- `battery_simulator.pv` — PV generation model
- `battery_simulator.market` — Price/market data
- `battery_simulator.optimizer` — Revenue optimization
- `battery_simulator.api` — FastAPI endpoints

## Data Sources

- **Prices:** `Ретроспективні ціни` sheet (РДН market, 8,786 hourly records)
- **Site params:** `Проєкція` sheet
- **Irradiance:** From operational model or external weather data

## Project Status

🚧 **In Development** (Phase 1-2)

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Core models | 🔵 Pending | Battery, PV models |
| 2. Data import | 🔵 Pending | Parse Excel → SQLite |
| 3. Greedy optimizer | 🟢 Ready | Simple algorithm |
| 4. LP optimizer | 🔵 Pending | pyomo + Gurobi |
| 5. REST API | 🔵 Pending | FastAPI |
| 6. Odoo module | 🔵 Pending | Integration |
| 7-8. Tests & Docs | 🔵 Pending | Full coverage |

---

**See ARCHITECTURE.md for detailed design & next steps.**
