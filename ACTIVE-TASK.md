# Battery Simulator - TaskFlow

**Project:** Battery Simulator for Solar PV + Storage  
**Status:** 🟢 Refactored & Deployed

---

## Recent Milestones (DONE)
- [x] **Smart Tariff Logic:** Transit energy for arbitrage is tariff-free. Cycles increased to 730/year.
- [x] **Database Optimization:** Bulk insert (N+1 fix) for 1-year simulations.
- [x] **GitHub Deployment:** Repo initialized and pushed to `iarogry/bess_model`.
- [x] **Unit Conversion:** Fixed MW to kW mismatch in config mapping.
- [x] **Architecture Refactor:** ENTSO-E is now the sole market data source. OREE fetchers deprecated.

---

## Session History (2026-05-18)
- User requested fix for unit inconsistency (MW -> kW).
- Refactored `EnergyConfig` and `_load_from_db` to handle 1000x multiplication.
- Created `fetch_market_data.py` (Resilient Fetcher) but then moved to a leaner ENTSO-E only architecture as per final request.
- Refactored `run_simulation.py` to use `ENTSOEFetcher`.
- Documented all changes in `ARCHITECTURE.md` and `MEMORY.md`.

---

## Active Tasks (IN PROGRESS)
- [ ] **ROI Validation:** Run 10 MWh simulation scenarios.
- [ ] **Final GitHub Push:** Sync all refactored code.

---

## Future Phases
- [ ] **Phase 5: REST API (FastAPI):** Expose simulation as a service.
- [ ] **Phase 6: Odoo Integration:** Connect to Hlibodar management system.
