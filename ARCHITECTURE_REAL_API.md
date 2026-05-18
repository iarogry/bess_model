# Battery Simulator - Real Architecture with Multi-Source Energy

**Project:** Energy Optimization for 2.5 MW PV + Battery + Grid + CHP + Flywheel  
**Location:** Chervonohrad, Ukraine  
**Data Sources:** OREE.com.ua (РДН) + ENTSO-E API  
**Optimization Model:** 24h rolling window (no lookahead bias)  
**Simulation:** Full year with historical prices  

---

## 1. Energy Sources (4+)

```
┌─────────────────────────────────────────────────────┐
│ ENERGY SOURCES (Chervonohrad Site)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 1. PV (Photovoltaic)                                │
│    - 2.5 MW capacity                                │
│    - Weather-dependent (historical irradiance)      │
│    - Deterministic forecast (±5% accuracy)          │
│                                                     │
│ 2. Battery (Energy Storage)                         │
│    - Capacity: TBD (e.g., 5,000 kWh)                │
│    - SoC: 20-80% (usable range)                     │
│    - Efficiency: 90-95% (round-trip)                │
│    - Degradation: ~0.3%/year                        │
│    - Power rating: ±500 kW (charge/discharge)       │
│                                                     │
│ 3. Grid Connection                                  │
│    - Can buy/sell electricity at РДН prices        │
│    - Unlimited capacity (for now)                   │
│    - Connection fee: included in prices             │
│                                                     │
│ 4. CHP (Cogenerator / Gas Engine)                   │
│    - Gas piston engine (КПГ установка)              │
│    - Capacity: TBD (e.g., 1 MW)                     │
│    - Efficiency: ~40% (electricity) + ~40% (heat)   │
│    - Fuel cost: separate from РДН                   │
│    - Ramp constraints: slow start (30-60 min)       │
│                                                     │
│ 5. Flywheel / Other Storage                         │
│    - Fast response (frequency regulation)           │
│    - Limited capacity (kWh)                         │
│    - High efficiency (95%)                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 2. Real Data Sources

### 2.1 OREE.com.ua (Primary)

**URL:** https://www.oree.com.ua/index.php/pricectr  
**Data:** Hourly РДН prices (Ринок «на добу наперед»)

```
GET https://www.oree.com.ua/index.php/control/results_mo/DAM
Response: 
{
  "date": "2026-05-10",
  "prices": [
    {"hour": 1, "price_hrn_per_mwh": 2500},  // 1:00-2:00
    {"hour": 2, "price_hrn_per_mwh": 2450},  // 2:00-3:00
    ...
    {"hour": 24, "price_hrn_per_mwh": 3100}  // 24:00 (25:00)
  ]
}
```

**Historical Archive:**
- Back to 2015 (8,000+ days)
- Format: HTML tables or CSV export
- Update frequency: Daily (published ~11 AM CET for next day)

**Script: `scripts/fetch_oree_daily.py`**
```python
# Fetch tomorrow's prices at 11 AM daily
# Store in SQLite: prices(date, hour, price_hrn_per_mwh)
```

### 2.2 ENTSO-E Transparency API (Backup)

**URL:** https://transparency.entsoe.eu/  
**API:** https://web-api.tp.entsoe.eu/api

**Ukraine Codes:**
- `10YUA-WEPS-----0` = UA-BEI (main bidding zone)
- `10Y1001A1001A869` = UA-DobTPP (alternative)

**Query Example:**
```bash
curl -X GET "https://web-api.tp.entsoe.eu/api" \
  -d "securityToken=YOUR_TOKEN" \
  -d "documentType=A44" \
  -d "in_domain=10YUA-WEPS-----0" \
  -d "out_domain=10YUA-WEPS-----0" \
  -d "periodStart=202605100000" \
  -d "periodEnd=202605102300" \
  -d "contractMarketAgreementType=A01"
```

**Response:** XML with hourly prices (same as OREE)

**Setup:** Register at https://transparency.entsoe.eu/ → Request API token

---

## 3. 24h Rolling Window Optimization

### 3.1 Core Idea (No Lookahead Bias)

```
DAY 1 (May 10):
  - At 00:00 UTC, we have:
    ✅ RDN prices for May 10 (published ~11 AM May 9)
    ❌ NO prices for May 11 (not available yet)
  - Optimize dispatch for 24 hours (May 10, 00:00 - 23:59)
    using ONLY May 10 prices
  - Execute the optimization

DAY 2 (May 11):
  - At 00:00 UTC, we have:
    ✅ RDN prices for May 11 (published ~11 AM May 10)
  - Optimize dispatch for 24 hours (May 11, 00:00 - 23:59)
    using ONLY May 11 prices
  - Execute the optimization

...and so on for 365 days
```

**Key constraint:** Each day's optimization uses ONLY that day's prices, not future prices.

### 3.2 Optimization Problem (LP)

For each 24-hour window:

```
VARIABLES:
  p_pv[h]         = PV generation at hour h (0-2500 kW)
  p_grid[h]       = Grid power (>0 = buy, <0 = sell)
  p_chp[h]        = CHP output (0 or 1000 kW)
  soc[h]          = Battery state of charge at end of hour h (kWh)
  p_charge[h]     = Battery charge power (kW, >0)
  p_discharge[h]  = Battery discharge power (kW, >0)

OBJECTIVE:
  Maximize: Σ(h=1 to 24) price[h] * (-p_grid[h])
    = revenue from selling to grid - cost of buying from grid

CONSTRAINTS:
  1. Energy balance (for each hour h):
     p_pv[h] + p_chp[h] - p_grid[h] - demand[h] 
       = (p_charge[h] - p_discharge[h]) / efficiency

  2. Battery SoC bounds:
     soc_min (e.g., 1000) ≤ soc[h] ≤ soc_max (e.g., 4000)

  3. Battery power bounds:
     0 ≤ p_charge[h] ≤ 500 kW
     0 ≤ p_discharge[h] ≤ 500 kW

  4. CHP ramp constraints:
     if p_chp[h] = 1000 and p_chp[h-1] = 0:
       requires at least 30 minutes startup

  5. Flywheel (if used):
     Fast response to fill minute-level gaps

  6. Grid connection constraints:
     p_grid[h] ≤ grid_max_capacity
```

---

## 4. Data Pipeline

### 4.1 Daily Price Fetching

```
┌─────────────────┐
│ 11:00 AM CET    │
│ (May 9, 11:00)  │
│                 │
│ OREE publishes  │
│ prices for      │
│ May 10          │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│ Cron Job (daily)         │
│ fetch_oree_daily.py      │
│ Runs at 11:30 AM CET     │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Parse HTML / CSV         │
│ Extract 24 hours         │
│ Store in SQLite          │
│                          │
│ prices(                  │
│   date TEXT,             │
│   hour INTEGER,          │
│   price REAL             │
│ )                        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Ready for next day's     │
│ optimization at 00:00    │
└──────────────────────────┘
```

### 4.2 Historical Data Loading

```python
# scripts/load_historical_prices.py

# Scrape OREE archive or ENTSO-E API
# Load all historical prices into SQLite
# Build index: date → 24 hourly prices

# Result: prices table with ~3,000 days of history
```

### 4.3 Database Schema

```sql
CREATE TABLE prices (
  id INTEGER PRIMARY KEY,
  date TEXT UNIQUE,                -- YYYY-MM-DD
  hour INTEGER,                     -- 1-24
  price_hrn_per_mwh REAL,          -- грн/МВт*год
  source TEXT,                      -- 'oree' or 'entsoe'
  created_at TIMESTAMP DEFAULT NOW
);

CREATE TABLE dispatch (
  id INTEGER PRIMARY KEY,
  date TEXT,
  hour INTEGER,
  p_pv REAL,                       -- PV generation (kW)
  p_grid REAL,                     -- Grid buy/sell (kW)
  p_chp REAL,                      -- CHP output (kW)
  soc REAL,                        -- Battery SoC (kWh)
  p_charge REAL,                   -- Battery charge (kW)
  p_discharge REAL,                -- Battery discharge (kW)
  revenue REAL,                    -- Revenue this hour (грн)
  created_at TIMESTAMP
);

CREATE TABLE annual_results (
  id INTEGER PRIMARY KEY,
  simulation_date TEXT,
  total_revenue REAL,              -- Annual (грн)
  pv_generation REAL,              -- Annual (kWh)
  grid_purchased REAL,             -- Annual (kWh)
  grid_sold REAL,                  -- Annual (kWh)
  chp_output REAL,                 -- Annual (kWh)
  battery_cycles INTEGER,          -- Number of full cycles
  battery_degradation REAL         -- % degradation
);
```

---

## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                            │
│ - Load & Price Charts                                       │
│ - Dispatch Schedule (24h view)                              │
│ - Annual Summary (revenue, KPIs)                            │
│ - Scenario builder (tweak capacity, efficiency, etc)        │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
    ┌─────────────┐   ┌──────────────┐
    │ API Server  │   │ Price Fetcher│
    │ (FastAPI)   │   │ (Cron daily) │
    └──────┬──────┘   └──────┬───────┘
           │                 │
           │ /optimize       │ fetch_oree_daily.py
           │ /simulate       │ (11:30 AM CET)
           │                 │
           └────────┬────────┘
                    │
         ┌──────────▼──────────┐
         │ Optimization Engine │
         │ (Pyomo + COIN-OR)   │
         │                     │
         │ - Read prices       │
         │ - Build LP model    │
         │ - Solve 24h window  │
         │ - Store dispatch    │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │ SQLite Database     │
         │                     │
         │ prices (historical) │
         │ dispatch (results)  │
         │ annual_results      │
         └─────────────────────┘
```

---

## 6. Simulation: Full Year

### 6.1 Annual Loop

```python
def simulate_year(year=2026):
    """
    Simulate full year (365 days) with 24h rolling windows.
    """
    
    total_revenue = 0
    daily_results = []
    
    for day in range(1, 366):  # Jan 1 - Dec 31
        current_date = datetime(2026, 1, 1) + timedelta(days=day-1)
        
        # Step 1: Load RDN prices for this day
        prices = db.query_prices(current_date)  # 24 prices
        
        # Step 2: Load current battery SoC from previous day
        prev_soc = daily_results[-1]['final_soc'] if daily_results else 2000
        
        # Step 3: Optimize dispatch for next 24 hours
        optimization = optimize_24h(
            prices=prices,
            initial_soc=prev_soc,
            pv_forecast=get_pv_forecast(current_date),
            demand=get_demand_forecast(current_date),
            constraints={
                'battery_capacity': 5000,
                'battery_efficiency': 0.95,
                'chp_capacity': 1000,
                'grid_max': 10000
            }
        )
        
        # Step 4: Store results
        day_revenue = sum(optimization['revenue'])
        total_revenue += day_revenue
        daily_results.append({
            'date': current_date,
            'revenue': day_revenue,
            'final_soc': optimization['soc'][-1],
            'dispatch': optimization
        })
        
        # Step 5: Log progress
        if day % 30 == 0:
            print(f"Day {day}: Revenue = {day_revenue:.0f} грн, "
                  f"Total YTD = {total_revenue:.0f} грн")
    
    return {
        'total_revenue': total_revenue,
        'daily_results': daily_results,
        'avg_daily_revenue': total_revenue / 365
    }
```

### 6.2 Example Output

```
Simulating year 2026 with historical РДН prices...

Day 30: Revenue = 4,230 грн, Total YTD = 127,450 грн
Day 60: Revenue = 3,890 грн, Total YTD = 265,320 грн
Day 90: Revenue = 2,150 грн, Total YTD = 378,900 грн  (spring, lower prices)
Day 120: Revenue = 1,890 грн, Total YTD = 468,450 грн (summer, dips)
Day 150: Revenue = 3,100 грн, Total YTD = 584,200 грн
...
Day 365: Total Annual Revenue = 1,456,320 грн

Annual Statistics:
- PV Generation: 5,200 MWh
- Grid Purchased: 1,800 MWh (low demand hours)
- Grid Sold: 2,150 MWh (arbitrage profit)
- CHP Output: 1,250 MWh (strategic dispatch)
- Battery Cycles: 156 full cycles
- Battery Degradation: 4.7% (from 5,000 kWh → 4,765 kWh usable)
- Average Daily Revenue: 3,988 грн
```

---

## 7. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Price Source** | OREE.com.ua + ENTSO-E API | Real market data, daily updates |
| **Optimization** | Pyomo + CBC/Gurobi | LP solver, handles 24×4 variables easily |
| **Database** | SQLite + pandas | Historical prices, dispatch results |
| **API** | FastAPI | Fast async, WebSocket support |
| **Frontend** | React + Chart.js | Interactive charts, daily updates |
| **Deployment** | Docker | Portable, easy CI/CD |

---

## 8. Development Phases

| Phase | Task | Duration | Dependencies |
|-------|------|----------|---|
| **1** | ✅ Research real APIs (OREE, ENTSO-E) | DONE | - |
| **2** | Design multi-source optimizer | 1-2 days | Phase 1 ✅ |
| **3** | Fetch & store historical prices | 2-3 days | Phase 2 |
| **4** | Implement 24h rolling window LP | 3-4 days | Phase 3 |
| **5** | Build annual simulation loop | 2 days | Phase 4 |
| **6** | FastAPI + results export | 2-3 days | Phase 5 |
| **7** | React frontend | 3-4 days | Phase 6 |
| **8** | Testing & optimization | 2-3 days | Phase 7 |

**Total: ~2-3 weeks** (depending on parallelism)

---

## 9. Critical Success Factors

1. ✅ **Real price data** — OREE prices, not made-up API
2. ✅ **No lookahead bias** — Each day uses only that day's prices
3. ✅ **Multi-source dispatch** — PV + Battery + CHP + Grid optimized together
4. ✅ **Rolling window** — 24h optimization per day, 365 days/year
5. ✅ **Realistic constraints** — SoC bounds, ramp rates, startup times

---

## 10. Questions for Юрій

1. **Battery Capacity?** (I assumed 5,000 kWh)
2. **CHP Capacity & Fuel Cost?** (I assumed 1 MW, need €/MWh cost)
3. **Flywheel?** (Capacity & use case?)
4. **Demand Profile?** (Load curve for site)
5. **Simulation Start Date?** (2026 or historical year?)
6. **Export Format?** (CSV, Excel, JSON?)
7. **Timeline?** (MVP by end of May?)

---

**Status:** 🔵 Ready for Phase 2 (Historical Price Fetching)  
**Owner:** Cyber  
**Updated:** 2026-05-10 20:52 UTC+2
