# Battery Simulator - TaskFlow

**Project:** Battery Simulator for Solar PV + Storage  
**Owner:** Cyber (agent: main)  
**Start Date:** 2026-05-08  
**Status:** 🔵 Architecture Review Phase

---

## TaskFlow Structure

```
FLOW ID: battery-simulator-v1
GOAL: Develop production-ready battery simulation engine
PHASES: 8 (Architecture → Deployment)
```

---

## Current Phase: Architecture Review

### 📋 Deliverables Created

- ✅ `ARCHITECTURE.md` — Full system design (9.4 KB)
- ✅ `README.md` — Quick start & overview (2.1 KB)  
- ✅ Project folder structure created
- ⏳ **Awaiting Юрий's approval** before proceeding to Phase 1

### 📝 Files in Place

```
battery-simulator/
├── ARCHITECTURE.md  ✅
├── README.md        ✅
├── ACTIVE-TASK.md   ✅ (this file)
├── src/             (ready for code)
├── tests/           (ready for tests)
├── scripts/         (ready for CLIs)
└── docs/            (ready for docs)
```

---

## Phase 1: Core Battery & PV Models

**Status:** 🔵 Pending architecture approval  
**Duration:** 3-5 days  
**Deliverables:**
- `src/battery_simulator/battery/core.py` — Battery model with SoC, efficiency, degradation
- `src/battery_simulator/pv/core.py` — PV generation model
- `tests/test_battery.py`, `tests/test_pv.py` — Unit tests
- `docs/models.md` — Model equations & assumptions

**Acceptance Criteria:**
- Battery model passes 10 unit tests
- PV model matches Excel generation (±2%)
- Degradation curves realistic
- Code documented

---

## Phase 2: Data Import (Excel → SQLite)

**Status:** 🔵 Pending Phase 1  
**Duration:** 2-3 days  
**Deliverables:**
- `src/battery_simulator/utils/excel_parser.py` — Parse Червоноград file
- `src/battery_simulator/database/models.py` — SQLAlchemy ORM
- `scripts/load_excel.py` — CLI to import data
- Database schema documentation

**Data to import:**
- Retrospective prices (8,786 rows from "Ретроспективні ціни")
- Site parameters (from "Проєкція")
- Historical generation (from "Операційна модель")

---

## Phase 3: Greedy Optimizer

**Status:** 🔵 Pending Phase 2  
**Duration:** 2 days  
**Deliverables:**
- `src/battery_simulator/optimizer/heuristic.py` — Simple greedy algorithm
- `tests/test_optimizer.py` — Integration tests
- `scripts/run_simulation.py` — CLI entry point

**Algorithm:**
- Each hour: if price high → discharge; if price low → charge
- Respects SoC bounds and power constraints
- Fast baseline for comparison

---

## Phase 4: Linear Programming Optimizer

**Status:** 🔵 Pending Phase 3  
**Duration:** 5-7 days  
**Deliverables:**
- `src/battery_simulator/optimizer/linear_program.py` — pyomo + solver
- Full 24-hour or 7-day optimization window
- Revenue maximization with constraints

**Technology:**
- Pyomo (modeling)
- Gurobi or CBC solver (open-source option)
- Handles uncertainty via rolling window

---

## Phase 5: REST API (FastAPI)

**Status:** 🔵 Pending Phase 4  
**Duration:** 3-4 days  
**Deliverables:**
- `src/battery_simulator/api/main.py` — FastAPI app
- `/simulate` — POST to run simulation
- `/jobs/{id}` — GET job status
- `/results/{id}/timeseries` — CSV export
- OpenAPI docs (auto-generated)

---

## Phase 6: Odoo Module Integration

**Status:** 🔵 Pending Phase 5  
**Duration:** 4-5 days  
**Deliverables:**
- `hd_battery_simulator/` module in Odoo (hlibodar repo)
- Model: `battery.simulation`
- Views: form, tree, pivot
- Reports: annual revenue, wear analysis
- Action: "Run Simulation" button → calls REST API

---

## Phase 7: Testing & Documentation

**Status:** 🔵 Pending Phase 6  
**Duration:** 3-4 days  
**Goals:**
- 90%+ code coverage
- Sphinx documentation with examples
- Jupyter notebook walkthrough
- Deployment guide

---

## Phase 8: Deployment & Monitoring

**Status:** 🔵 Pending Phase 7  
**Duration:** 2-3 days  
**Deliverables:**
- Docker image (`battery-simulator:v1.0`)
- CI/CD pipeline (GitLab)
- Monitoring & logging (ELK or similar)
- Production checklist

---

## Checkpoints & Reviews

| Checkpoint | Date | Reviewer | Status |
|-----------|------|----------|--------|
| Architecture Review | 2026-05-08 | Юрій | 🔵 Pending |
| Phase 1 Demo | TBD | Юрій | 🔵 Pending |
| Phase 3 Demo | TBD | Юрій | 🔵 Pending |
| Phase 5 Demo (API) | TBD | Юрій | 🔵 Pending |
| Phase 6 Demo (Odoo) | TBD | Юрій | 🔵 Pending |
| Final Release | TBD | Юрій | 🔵 Pending |

---

## Questions for Юрій

1. ✅ Architecture OK?
2. ⏳ Battery capacity (kWh)? (Default: 5,000)
3. ⏳ Optimization window: 24h rolling or full-year? (Default: 24h)
4. ⏳ Solver preference: Gurobi (commercial) or CBC (open-source)?
5. ⏳ Odoo integration: Same database or separate API?
6. ⏳ Timeline: All 8 phases, or MVP (phases 1-5)?

---

## Notes

- Excel file analyzed: 6,862 formulas across 6 sheets
- Prices from РДН market (8,786 hourly records)
- Site: Chervonohrad, Ukraine | 2.5 MW PV + Battery
- Language: Python 3.11+
- Tech Stack: FastAPI, pandas, pyomo, SQLite

---

**Last Updated:** 2026-05-08 16:15 UTC+2  
**Next Action:** Юрій reviews architecture → approval → Phase 1 starts
