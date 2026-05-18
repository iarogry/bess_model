# Battery Simulator - TaskFlow

**Project:** Battery Simulator for Solar PV + Storage  
**Status:** 🟢 Refactored, Bug-fixed & Stable

---

## Recent Milestones (DONE)
- [x] **Smart Tariff Logic:** Transit energy for arbitrage is tariff-free.
- [x] **Database Optimization:** Bulk insert for 1-year simulations.
- [x] **GitHub Deployment:** Repo initialized and pushed to `iarogry/bess_model`.
- [x] **PostgreSQL Integration:** Core modules migrated to centralized PostgreSQL.
- [x] **Energy Balance Fix:** Closed simultaneous charge/discharge loophole via Global AC Bus Balance constraint. Fixed double-counting of imports and discharges.

---

## Session History (2026-05-18)
- Refactored database architecture to PostgreSQL.
- Fixed unit inconsistency MW -> kW.
- **Fixed energy double-counting bug:** Updated LP constraints to prevent energy serving demand and export/charging simultaneously.
- Results confirmed that previous "super profits" were due to this mathematical loophole.

---

## Future Phases
- [ ] **ROI Validation:** Run simulation with 0 capacity to establish a cost baseline.
- [ ] **Threshold Tuning:** Add arbitrage price spread thresholds to manage battery lifespan.
- [ ] **REST API:** Expose simulation as a service.
