# Dependency Graph - Battery Simulator

**Generated from:** FORMULAS_ANALYSIS.json  
**Total Formulas:** 33,412  
**Total Cells:** 40,003  
**Input Parameters:** 104

---

## 1. High-Level Sheet Dependencies

```
INPUT SHEET (172 formulas, 104 parameters)
│
├─→ CAPEX (699 formulas)
│   │
│   ├─→ Output базова (215 formulas)
│   │   │
│   │   ├─→ Фінмодель базова (5,694 formulas)
│   │   │   │
│   │   │   └─→ Помісячні дані базова (1,030 formulas)
│   │   │       │
│   │   │       └─→ [Reports & Summaries]
│   │   │
│   │   └─→ Output оптимізована (226 formulas)
│   │       │
│   │       ├─→ Фінмодель оптимізована (5,967 formulas)
│   │       │   │
│   │       │   └─→ Помісячні дані оптимізована (2,150 formulas)
│   │       │
│   │       └─→ [Battery Optimization Results]
│   │
│   └─→ Операційна модель базова (9,892 formulas, 8,771 rows!)
│       │
│       ├─→ ФЕС (1,003 formulas, 8,769 rows)
│       ├─→ Ретроспективні ціни (3,975 formulas, 8,786 rows)
│       └─→ Середньомісячні години (1,416 formulas, 285 rows)
│
└─→ Гарантійні платежі (973 formulas, 41 rows)
```

---

## 2. Data Flow Through Sheets

### Phase 1: INPUT Parameters → CAPEX Calculations
```
INPUT!A1:Z50 (Parameters)
  ├─ PV Power (kW)
  ├─ Battery Capacity (kWh)
  ├─ Efficiency (%)
  ├─ Degradation Rate (%/year)
  └─ 100 other parameters
    ↓
CAPEX!A1:BW66 (Calculations)
  ├─ Equipment costs (CapEx breakdown)
  ├─ Installation costs
  ├─ Total CapEx
  ├─ CapEx per kW
  └─ 695 dependent cells
    ↓
[Ready for Output sheet]
```

### Phase 2: CAPEX → OUTPUT (базова & оптимізована)
```
OUTPUT базова!A1:V25
  ├─ Annual production (kWh)
  ├─ Peak generation (kW)
  ├─ Average generation (kW)
  └─ 212 other KPIs
    ↓
[Splits into two paths]
    ├─→ Базова (without battery optimization)
    └─→ Оптимізована (with battery charge/discharge cycles)
```

### Phase 3: OUTPUT → Financial Model (Фінмодель)
```
Фінмодель базова (227 rows × 306 cols, 5,694 formulas)
  │
  ├─ Year 1-25 projections
  ├─ Revenue = Generation × Market Price
  ├─ Operating costs
  ├─ Maintenance costs
  ├─ CapEx depreciation
  ├─ Tax calculations
  ├─ Free Cash Flow
  ├─ NPV (IRR calculations)
  └─ 5,686 dependent formulas
    ↓
Фінмодель оптимізована (similar, 5,967 formulas)
  │
  ├─ Same structure but:
  ├─ Revenue includes battery discharge premium pricing
  ├─ Battery degradation costs
  ├─ Optimized charging/discharging scenarios
  └─ 5,959 dependent formulas
```

### Phase 4: Financial Model → Monthly Breakdown
```
Помісячні дані базова (38 rows × 124 cols, 1,030 formulas)
  ├─ 12 months × 10 metrics per month
  ├─ Production, Revenue, Costs
  └─ Rolling aggregations from Фінмодель

Помісячні дані оптимізована (76 rows × 124 cols, 2,150 formulas)
  ├─ Monthly scenarios (baseline vs optimized)
  ├─ Battery SoC trajectories
  ├─ Charge/discharge cycles
  └─ Revenue differential (optimized - baseline)
```

### Phase 5: Operational Data
```
Операційна модель базова (8,771 rows × 27 cols, 9,892 formulas!)
  ├─ Hourly data for 1 year
  ├─ PV generation (W, kW, %)
  ├─ Battery SoC (%)
  ├─ Grid exchange (kW)
  ├─ Prices (грн/MWh)
  └─ 9,884 hourly calculations

ФЕС (8,769 rows, 1,003 formulas)
  ├─ Hourly solar irradiance
  ├─ Temperature effects
  └─ PV degradation factors

Ретроспективні ціни (8,786 rows, 3,975 formulas)
  ├─ Historical РДН prices (2022-2023?)
  ├─ Hourly market prices
  └─ Price statistics (min, max, avg)

Середньомісячні години (285 rows, 1,416 formulas)
  ├─ Average price by month & hour
  ├─ Peak/off-peak hours
  └─ Seasonal patterns
```

---

## 3. Critical Dependency Chains

### Chain 1: INPUT → Financial Result
```
INPUT!E2 (PV Power = 2500 kW)
  ↓
CAPEX!D5:D20 (25 CapEx cells)
  ├─ Equipment cost = f(power, type)
  ├─ Installation = f(power, complexity)
  └─ Total CapEx = sum of 25 components
    ↓
OUTPUT базова!C1 (Annual production)
  ├─ = Input power × capacity factor × 8760 hours
  └─ Depends on CAPEX total via efficiency
    ↓
Фінмодель базова!B2 (Year 1 revenue)
  ├─ = Annual production × average price
  ├─ Adjusted for degradation over years
  └─ Spreads to 25-year projection
    ↓
Фінмодель базова!C25 (Project NPV)
  ├─ = sum of discounted cash flows
  ├─ Depends on 500+ intermediate cells
  └─ Final financial metric
```

### Chain 2: Historical Prices → Monthly Revenue
```
Ретроспективні ціни!F3:F8786 (8,784 hourly prices)
  ↓
Середньомісячні години!B4:L13 (Average by month × hour)
  ├─ = AVERAGEIFS(prices, month, hour)
  ├─ 12 months × 24 hours = 288 averages
  └─ Plus statistics (min, max, quartiles)
    ↓
Помісячні дані!B4:L15 (Monthly revenue projection)
  ├─ = Production[month,hour] × Price[month,hour]
  ├─ Sums across all hours
  └─ Annual total = sum(12 months)
```

### Chain 3: Battery Optimization Impact
```
INPUT!E44 (Battery Capacity = 5000 kWh)
  ↓
Output оптимізована!D5 (Optimized annual production)
  ├─ = baseline + battery discharge premium
  ├─ Premium based on peak/off-peak pricing
  └─ Depends on Середньомісячні години (price patterns)
    ↓
Фінмодель оптимізована!B2 (Year 1 revenue with battery)
  ├─ = base revenue + battery premium - battery costs
  ├─ Battery costs = degradation × cycles
  └─ ROI improvement vs baseline
    ↓
Помісячні дані оптимізована!M4:M15 (Revenue delta)
  ├─ = Optimized monthly - Baseline monthly
  ├─ Shows where battery adds most value
  └─ Informs operation strategy
```

---

## 4. Cell-Level Dependency Examples

### From Input Sheet
```
Input!E2 → PV Power (2500 kW)
  Dependencies: NONE (user input)
  
Input!E3 → Battery Capacity (5000 kWh)
  Dependencies: NONE (user input)

Input!E44 → Project Lifetime (25 years)
  Dependencies: NONE (user input)
```

### From CAPEX Sheet
```
CAPEX!E9 → Equipment Cost Total
  Depends on: CAPEX!E6 (unit cost), CAPEX!E8 (quantity)
  Formula: = E6 * E8
  
CAPEX!E13 → Total CapEx
  Depends on: CAPEX!E2 (equipment), CAPEX!E9 (installation), CAPEX!E7 (permits)
  Formula: = E2 + E9 + E7 + ... (sum of all cost components)
  
CAPEX!F21 → CapEx per kW
  Depends on: CAPEX!E13 (Total), Input!E2 (PV Power)
  Formula: = E13 / Input!E2
```

### From Financial Model (Фінмодель базова)
```
Фінмодель!B2 → Year 1 Revenue
  Depends on: Output!C1 (annual production), Середньомісячні!B1 (avg price)
  Formula: = Output!C1 * Середньомісячні!B1

Фінмодель!C2 → Year 2 Revenue
  Depends on: Фінмодель!B2 (Year 1), degradation rate
  Formula: = B2 * (1 - degradation_rate)

Фінмодель!D25 → NPV (25 years)
  Depends on: ALL B2:C26 (25 years of cashflows), discount rate
  Formula: = NPV(rate, B2:C26) - CAPEX
```

### From Operational Model (8,771 hourly rows!)
```
Операційна!H12 → Hour 1 PV Generation
  Depends on: ФЕС!H12 (irradiance), efficiency
  Formula: = ФЕС!H12 * efficiency * pv_power

Операційна!I12 → Hour 1 Battery SoC
  Depends on: Операційна!I11 (prev hour SoC), H12 (generation), charging logic
  Formula: = I11 + (H12 * charge_efficiency) - discharge_power

Операційна!J12 → Hour 1 Grid Exchange
  Depends on: H12 (generation), I12 (battery), load demand
  Formula: = H12 + battery_discharge - load
```

---

## 5. Topological Recalculation Order

When user changes INPUT!E2 (PV Power):

```
1️⃣  INPUT Sheet (0 ms)
    └─ Only E2 changes

2️⃣  CAPEX Sheet (5 ms)
    ├─ D5:D20 recalculate (equipment, installation)
    ├─ E2:E20 recalculate (subtotals)
    └─ E13 recalculate (Total CapEx)

3️⃣  OUTPUT Sheet (2 ms)
    ├─ C1:V25 recalculate (all KPIs)
    └─ Depends on CAPEX!E13 via efficiency factor

4️⃣  Фінмодель базова (100 ms) 🔥 LARGE
    ├─ B2:B26 recalculate (25-year revenue)
    ├─ C2:C26 recalculate (costs)
    ├─ D2:D26 recalculate (profit)
    └─ E2:E26 recalculate (all other 5,650+ cells)

5️⃣  Фінмодель оптимізована (120 ms) 🔥 LARGE
    └─ All 5,967 formulas recalculate

6️⃣  Помісячні дані базова (50 ms)
    ├─ 12 months × metrics
    └─ 1,030 cells update

7️⃣  Помісячні дані оптимізована (100 ms)
    └─ 2,150 cells update

8️⃣  Операційна модель (300 ms) 🔥 MASSIVE
    ├─ 8,771 hourly rows
    ├─ Recalculate generation, battery SoC, grid exchange
    └─ 9,892 formulas execute

═════════════════════════════════════════════════════
⏱️  TOTAL: ~700 ms (if no caching)
✅ With Redis cache: ~200 ms (skip unchanged cells)
```

---

## 6. Smart Recalculation Strategy

### Dependency Tracking
```python
# When INPUT!E2 changes:
affected_cells = graph.bfs_forward(INPUT!E2)
# Returns: [CAPEX!D5, CAPEX!E2, ..., Фінмодель!E26, ...]

# Only recalculate affected cells
for cell in affected_cells:
    if has_circular_dependency(cell):
        raise CircularReferenceError
    if in_cache(cell) and deps_unchanged:
        continue  # Skip unchanged cells
    else:
        evaluate(cell)
```

### Caching Strategy
```
Level 1: Cell-level cache
  ├─ Key: "CAPEX!E13"
  ├─ Value: 1,500,000 (Total CapEx)
  └─ Invalidate when dependencies change

Level 2: Sheet-level cache
  ├─ Key: "Фінмодель базова"
  ├─ Value: {B2: 1000000, C2: 50000, ...}
  └─ Invalidate when any cell in sheet changes

Level 3: Results cache
  ├─ Key: "results_v1"
  ├─ Value: {output: {...}, financial: {...}, monthly: {...}}
  └─ Valid for 10 minutes (user may not change inputs)
```

---

## 7. Circular Reference Detection

✅ **GOOD** (Linear chain):
```
INPUT!E2 → CAPEX!E13 → OUTPUT!C1 → Фінмодель!B2 → ✓ Valid
```

🔴 **BAD** (Circular):
```
CAPEX!E13 → CAPEX!E2 → CAPEX!E13 → ❌ ERROR
"Cell E13 depends on E2, but E2 depends on E13"
```

**Detection Method:**
- Build dependency graph at startup
- Run cycle detection algorithm (Tarjan's SCC)
- Flag any strongly connected components (cycles)
- Excel should have none, but good to validate

---

## 8. Performance Bottlenecks

| Sheet | Cells | Formulas | Est. Time | Issue |
|-------|-------|----------|-----------|-------|
| INPUT | - | 172 | 0 ms | User input only |
| CAPEX | 5,247 | 699 | 5 ms | Manageable |
| OUTPUT | 506 | 215 + 226 | 2 ms | Fast |
| Фінмодель | ~20,000 | 11,661 | 150 ms | **Large** |
| Помісячні дані | ~2,300 | 3,180 | 100 ms | **Large** |
| Операційна модель | ~236,517 | 9,892 | 300 ms | **MASSIVE** (8,771 rows!) |
| Others | ~4,000 | 2,392 | 50 ms | - |

**Optimizations:**
1. **Vectorize Операційна модель** — Use NumPy for 8,771-row calculations
2. **Cache hierarchy** — Cell → Sheet → Results
3. **Lazy evaluation** — Only compute visible cells initially
4. **Parallel execution** — Independent sheets in Celery workers

---

**Generated:** 2026-05-08  
**Status:** Ready for implementation  
**Next:** Build dependency graph resolver (Phase 2)
