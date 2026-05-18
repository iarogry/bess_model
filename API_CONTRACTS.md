# Battery Simulator - API Contracts

**Phase 1 MVP:** Frontend sends parameters → Backend optimizes 24h → Returns dispatch schedule

---

## 1. Request: User Inputs Simulation Parameters

### Endpoint: `POST /api/simulate`

**Frontend sends:** User-configured system parameters

```json
{
  "simulation_config": {
    "start_date": "2025-05-10",
    "end_date": "2026-05-09",
    "description": "Full year simulation 2025-2026"
  },
  "energy_sources": {
    "pv": {
      "capacity_kw": 2500,
      "efficiency": 0.95,
      "enabled": true,
      "notes": "2.5 MW array, Chervonohrad"
    },
    "battery": {
      "capacity_kwh": 5000,
      "soc_min_percent": 20,
      "soc_max_percent": 80,
      "efficiency_round_trip": 0.95,
      "degradation_percent_per_year": 0.3,
      "max_charge_kw": 500,
      "max_discharge_kw": 500,
      "enabled": true
    },
    "chp": {
      "capacity_kw": 1000,
      "efficiency_electricity": 0.40,
      "efficiency_heat": 0.40,
      "fuel_cost_hrn_per_mwh": 3500,
      "startup_time_minutes": 5,
      "min_load_percent": 30,
      "enabled": true,
      "notes": "Gas piston engine"
    },
    "grid": {
      "max_import_kw": 5000,
      "max_export_kw": 5000,
      "enabled": true
    }
  },
  "demand": {
    "type": "historical",
    "data_source": "site_meters",
    "average_daily_kwh": 8000,
    "peak_hour_kw": 500,
    "notes": "Will use historical load profile"
  },
  "optimization": {
    "algorithm": "rolling_window_24h",
    "objective": "maximize_revenue",
    "price_source": "oree",
    "price_currency": "UAH_per_MWh"
  }
}
```

---

## 2. Response: Optimization Results

### HTTP 202 (Accepted - Long-running task)

```json
{
  "job_id": "sim-2025-2026-uuid-12345",
  "status": "processing",
  "progress": 0,
  "message": "Starting full-year simulation (365 days)",
  "eta_seconds": 3600,
  "check_status_url": "/api/simulate/sim-2025-2026-uuid-12345/status"
}
```

**Frontend polls:** `GET /api/simulate/{job_id}/status`

```json
{
  "job_id": "sim-2025-2026-uuid-12345",
  "status": "processing",
  "progress": 125,
  "progress_percent": 34.2,
  "current_day": "2025-08-12",
  "message": "Day 125/365 complete"
}
```

**When done:** HTTP 200

```json
{
  "job_id": "sim-2025-2026-uuid-12345",
  "status": "completed",
  "progress": 365,
  "progress_percent": 100.0,
  "results_url": "/api/simulate/sim-2025-2026-uuid-12345/results"
}
```

---

## 3. Results: Full Year Summary

### Endpoint: `GET /api/simulate/{job_id}/results`

```json
{
  "job_id": "sim-2025-2026-uuid-12345",
  "simulation_period": {
    "start_date": "2025-05-10",
    "end_date": "2026-05-09",
    "days": 365
  },
  "annual_summary": {
    "total_revenue_hrn": 1456320.50,
    "avg_daily_revenue_hrn": 3988.57,
    "avg_hourly_revenue_hrn": 166.19,
    "pv_generation_mwh": 5200.50,
    "grid_purchased_mwh": 1800.25,
    "grid_sold_mwh": 2150.75,
    "chp_output_mwh": 1250.00,
    "battery_cycles": 156,
    "battery_final_capacity_kwh": 4765,
    "battery_degradation_percent": 4.7
  },
  "monthly_breakdown": [
    {
      "month": "2025-05",
      "revenue_hrn": 134500,
      "days": 21,
      "avg_daily_revenue": 6404.76,
      "pv_mwh": 450,
      "grid_sold_mwh": 200
    },
    {
      "month": "2025-06",
      "revenue_hrn": 89200,
      "days": 30,
      "avg_daily_revenue": 2973.33,
      "pv_mwh": 520,
      "grid_sold_mwh": 120
    }
    // ... 10 more months
  ],
  "download_urls": {
    "csv_dispatch": "/api/simulate/sim-2025-2026-uuid-12345/export/dispatch.csv",
    "csv_daily": "/api/simulate/sim-2025-2026-uuid-12345/export/daily_summary.csv",
    "json_full": "/api/simulate/sim-2025-2026-uuid-12345/export/full_results.json"
  }
}
```

---

## 4. Dispatch Schedule (Hourly Detail)

### Endpoint: `GET /api/simulate/{job_id}/dispatch?date=2025-08-12`

```json
{
  "date": "2025-08-12",
  "dispatch_schedule": [
    {
      "hour": 1,
      "time": "2025-08-12T00:00:00Z",
      "price_hrn_per_mwh": 2500,
      "pv_output_kw": 0,
      "grid_buy_kw": 450,
      "grid_sell_kw": 0,
      "chp_output_kw": 0,
      "battery_charge_kw": 100,
      "battery_discharge_kw": 0,
      "battery_soc_kwh": 2100,
      "total_revenue_hrn": -1125
    },
    {
      "hour": 2,
      "time": "2025-08-12T01:00:00Z",
      "price_hrn_per_mwh": 2450,
      "pv_output_kw": 0,
      "grid_buy_kw": 450,
      "grid_sell_kw": 0,
      "chp_output_kw": 0,
      "battery_charge_kw": 50,
      "battery_discharge_kw": 0,
      "battery_soc_kwh": 2150,
      "total_revenue_hrn": -1102.5
    },
    // ... continue for hours 3-12 (low price period)
    {
      "hour": 13,
      "time": "2025-08-12T12:00:00Z",
      "price_hrn_per_mwh": 4200,
      "pv_output_kw": 2200,
      "grid_buy_kw": 0,
      "grid_sell_kw": 1500,
      "chp_output_kw": 0,
      "battery_charge_kw": 0,
      "battery_discharge_kw": 700,
      "battery_soc_kwh": 1450,
      "total_revenue_hrn": 6300
    },
    // ... continue for hours 14-24 (peak prices)
    {
      "hour": 24,
      "time": "2025-08-12T23:00:00Z",
      "price_hrn_per_mwh": 3800,
      "pv_output_kw": 50,
      "grid_buy_kw": 0,
      "grid_sell_kw": 400,
      "chp_output_kw": 1000,
      "battery_charge_kw": 0,
      "battery_discharge_kw": 650,
      "battery_soc_kwh": 800,
      "total_revenue_hrn": 2920
    }
  ],
  "day_summary": {
    "date": "2025-08-12",
    "total_revenue_hrn": 12450.75,
    "pv_total_mwh": 14.2,
    "grid_sold_total_mwh": 8.5,
    "grid_bought_total_mwh": 2.1,
    "chp_total_mwh": 5.0,
    "battery_cycles": 0.33
  }
}
```

---

## 5. Frontend Data Flow Example

### User Input → Simulation → Results Visualization

```
FRONTEND (React)
├── Step 1: User fills form
│   ├── Battery capacity: 5000 kWh
│   ├── PV capacity: 2500 kW
│   ├── CHP capacity: 1000 kW
│   └── [Submit]
│
├── Step 2: POST /api/simulate
│   {
│     "energy_sources": { ... },
│     "simulation": { "start_date": "2025-05-10", ... }
│   }
│
├── Step 3: Get job_id (HTTP 202)
│   job_id = "sim-2025-2026-uuid-12345"
│
├── Step 4: Poll /api/simulate/{job_id}/status
│   Progress bar: 34% (Day 125/365)
│
├── Step 5: When done (HTTP 200)
│   Fetch /api/simulate/{job_id}/results
│
├── Step 6: Display Results
│   ├── Annual Revenue: 1,456,320 грн
│   ├── Monthly chart
│   ├── Daily chart (pick date to see hourly dispatch)
│   └── Export buttons (CSV, JSON)
│
└── Step 7: Click day in calendar
    GET /api/simulate/{job_id}/dispatch?date=2025-08-12
    Show hourly dispatch + prices
```

---

## 6. Export Formats

### CSV: Daily Summary

```csv
date,revenue_hrn,pv_mwh,grid_sold_mwh,grid_bought_mwh,chp_mwh,battery_soc_final_kwh,battery_cycles
2025-05-10,6204.50,18.5,12.3,2.1,0.0,4500,0.2
2025-05-11,5890.25,19.2,11.8,3.0,0.5,4200,0.3
2025-05-12,6450.75,17.8,13.5,1.8,2.0,3950,0.4
...
2026-05-09,5630.00,20.1,10.2,4.5,1.2,4100,0.25
```

### CSV: Hourly Dispatch (One Day)

```csv
date,hour,price_hrn_per_mwh,pv_kw,grid_buy_kw,grid_sell_kw,chp_kw,battery_charge_kw,battery_discharge_kw,battery_soc_kwh,revenue_hrn
2025-08-12,1,2500,0,450,0,0,100,0,2100,-1125
2025-08-12,2,2450,0,450,0,0,50,0,2150,-1102.5
2025-08-12,3,2400,0,450,0,0,0,0,2150,-1080
...
2025-08-12,24,3800,50,0,400,1000,0,650,800,2920
```

### JSON: Full Results

```json
{
  "simulation": { ... },
  "annual_summary": { ... },
  "monthly_breakdown": [ ... ],
  "daily_results": [
    {
      "date": "2025-05-10",
      "revenue": 6204.50,
      "dispatch": [ ... 24 hours ... ]
    },
    // ... 364 more days
  ]
}
```

---

## 7. Error Handling

### Invalid Parameters

```json
{
  "error": "validation_error",
  "message": "Invalid simulation parameters",
  "details": [
    {
      "field": "battery.capacity_kwh",
      "error": "Must be > 0"
    },
    {
      "field": "simulation.start_date",
      "error": "Cannot be in the future"
    }
  ]
}
```

### Price Data Missing

```json
{
  "error": "missing_data",
  "message": "No price data available for date range",
  "missing_dates": ["2025-05-10", "2025-05-11"],
  "suggestion": "Run fetch_oree_prices first"
}
```

---

## 8. Backend Implementation Plan

```
Phase 2: Data Collection
├── fetch_oree_historical.py
│   └── Scrape OREE for 2025-05-10 to 2026-05-09
│   └── Store in SQLite prices table
│
└── load_demand_profile.py
    └── Historical site load data (your meters)
    └── Store in SQLite demand table

Phase 3: Optimization Engine
├── optimizer.py
│   ├── FormulaLP (Pyomo + CBC)
│   ├── 24h rolling window
│   └── Multi-source dispatch
│
└── simulator.py
    ├── Loop 365 days
    ├── Daily optimization
    └── Store dispatch results

Phase 4: FastAPI Backend
├── main.py
│   ├── POST /api/simulate (start job)
│   ├── GET /api/simulate/{id}/status (progress)
│   ├── GET /api/simulate/{id}/results (summary)
│   ├── GET /api/simulate/{id}/dispatch (hourly detail)
│   └── GET /api/simulate/{id}/export/* (CSV/JSON)
│
└── models.py (Pydantic schemas)

Phase 5: React Frontend
├── App.tsx
├── components/
│   ├── SimulationForm.tsx (user inputs)
│   ├── ProgressBar.tsx (status polling)
│   ├── Results.tsx (charts + tables)
│   └── DayDetail.tsx (hourly dispatch)
└── hooks/
    └── useSimulation.ts (API calls)
```

---

**Status:** Ready for Phase 2 - Historical Price Data Collection  
**Next:** Fetch OREE prices for 2025-05-10 to 2026-05-09
