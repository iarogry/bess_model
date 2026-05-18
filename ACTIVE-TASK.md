# Battery Simulator - TaskFlow

**Project:** Battery Simulator for Solar PV + Storage  
**Status:** 🟢 Final Refactor Complete & Stable

---

## Recent Milestones (DONE)
- [x] **PostgreSQL Centralization:** Entire system migrated to PostgreSQL via `db_connector.py`.
- [x] **Real Data Integration:** Synthetic formulas replaced with SQL queries for PV, Demand, and Prices.
- [x] **Bulk Insert Fix:** Type-safe `executemany` for PostgreSQL verified.
- [x] **Unit Consistency:** Automatic MW -> kW conversion implemented.
- [x] **Financial Logic:** Smart Tariff Allocation for high-ROI arbitrage.

---

## Session History (2026-05-18)
- Refactored core modules to use PostgreSQL exclusively.
- Fixed `np.float64` error in bulk inserts.
- Added `export_monthly_csv` method to `AnnualSimulator`.
- Verified 2025 simulation with real data (28.2M UAH revenue).
- Finalized GitHub deployment and secured credentials.

---

## Future Phases
- [ ] **Phase 5: REST API (FastAPI):** Expose simulation as a service.
- [ ] **Phase 6: Odoo Integration:** Connect to Hlibodar management system.
- [ ] **Threshold Tuning:** Add arbitrage price spread thresholds to manage battery lifespan (cycles).
