# Battery Simulator - Architecture V2
## Real-time Formula Engine

**Based on Excel Analysis:**
- 33,412 formulas across 13 sheets
- 104 INPUT parameters  
- 40,003 total cells
- Massive dependency graph

---

## 1. Core Architecture

### 1.1 Three-Layer Model

```
┌─────────────────────────────────────────────────────┐
│  FRONTEND (React/Vue)                               │
│  - 104 Input Fields (interactive forms)              │
│  - Real-time chart updates                          │
│  - Export to CSV/PDF                                │
└────────────────┬────────────────────────────────────┘
                 │ WebSocket (live updates)
┌────────────────▼────────────────────────────────────┐
│  BACKEND (FastAPI)                                  │
│  - Formula Engine (Python)                          │
│  - Dependency Graph Resolver                        │
│  - Cache Layer (Redis)                              │
│  - Job Queue (Celery)                               │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│  DATA LAYER                                         │
│  - SQLite (historical data, prices)                 │
│  - In-memory graph (current calculations)           │
│  - JSON state (input parameters)                    │
└─────────────────────────────────────────────────────┘
```

### 1.2 Formula Engine Core

```python
class FormulaEngine:
    def __init__(self, input_sheet, formulas_json):
        self.inputs = {}          # 104 parameters
        self.cells = {}           # All 40,003 cells
        self.dependency_graph = {}  # Cell → [dependencies]
        self.formulas = {}        # Cell → formula string
        
    def set_input(self, field_name, value):
        # Update INPUT, trigger recalculation
        self.inputs[field_name] = value
        self.recalculate()
    
    def recalculate(self):
        # Topological sort on dependency graph
        # Recalculate only affected cells (delta)
        for cell in self.affected_cells:
            self.evaluate(cell)
    
    def evaluate(self, cell_addr):
        # Parse formula, resolve deps, return value
        formula = self.formulas[cell_addr]
        deps = self.dependency_graph[cell_addr]
        dep_values = {d: self.cells[d] for d in deps}
        result = eval_excel_formula(formula, dep_values)
        self.cells[cell_addr] = result
        return result
    
    def get_output(self, sheet_name, cell_range):
        # Return results from Output sheets
        return self.cells.filtered(sheet_name, cell_range)
```

---

## 2. Data Flow

### 2.1 Real-time Recalculation

```
User changes INPUT field (e.g., "Battery Capacity")
                ↓
[Frontend] WebSocket → {"field": "battery_kwh", "value": 5000}
                ↓
[Backend] FormulaEngine.set_input("battery_kwh", 5000)
                ↓
[Dependency Resolution] Find all affected cells
  - CAPEX calculations depend on battery_kwh
  - Output sheets depend on CAPEX
  - Financial model depends on Output
                ↓
[Topological Sort] Recalculate in order:
  1. CAPEX (699 formulas)
  2. Output базова (215 formulas)
  3. Фінмодель (5694 formulas)
  4. Помісячні дані (1030 formulas)
                ↓
[Cache] Store intermediate results
                ↓
[Frontend] WebSocket → Updated charts, tables, KPIs
```

### 2.2 13 Sheets Dependency Chain

```
INPUT (172 formulas, 104 parameters) ← User enters data
    ↓
CAPEX (699 formulas) ← Uses inputs for CapEx calculation
    ↓
Output базова (215 formulas) ← Annual production forecast
    ↓
Output оптимізована (226 formulas) ← Battery-optimized output
    ↓
Фінмодель базова (5694 formulas) ← Revenue, IRR, NPV
    ↓
Фінмодель оптимізована (5967 formulas) ← With battery optimization
    ↓
Помісячні дані (1030 + 2150 formulas) ← Month-by-month breakdown
    ↓
[Auxiliary sheets] ← ФЕС, Ретроспективні ціни, Середньомісячні години, Гарантійні платежи
```

---

## 3. Tech Stack (REVISED)

| Layer | Component | Technology | Rationale |
|-------|-----------|-----------|-----------|
| **Frontend** | UI | React + TypeScript | Interactive, real-time updates |
| | State | Zustand or Redux | Manage 104 input fields |
| | Charts | Recharts or Chart.js | Financial KPI visualization |
| | WebSocket | Socket.IO | Live recalculation updates |
| **Backend** | API | FastAPI + Uvicorn | Async, fast, OpenAPI |
| | Formula Engine | Python native (ast.literal_eval) | Direct formula evaluation |
| | Dependency Resolution | NetworkX | Graph algorithms |
| | Caching | Redis | Cache intermediate results |
| | Job Queue | Celery + Redis | Async formula recalculation |
| **Data** | Historical | SQLite | Price data (8,786 rows) |
| | State | JSON | Input parameters, current values |
| | Backup | Parquet | Archive yearly results |

---

## 4. Key Components

### 4.1 INPUT Sheet Parser
- Extract 104 parameters from "Input" sheet
- Types: number, text, date, percentage
- Default values from Excel
- UI: auto-generate forms from metadata

### 4.2 Formula Evaluator
- Parse & execute 33,412 Excel formulas
- Support: +, -, *, /, SUM, AVERAGE, IF, VLOOKUP, etc.
- Handle cross-sheet references (Input!E2, CAPEX!C5)
- Cache results per cell

### 4.3 Dependency Graph
- Build at startup from FORMULAS_ANALYSIS.json
- Node = cell (e.g., "CAPEX!C5")
- Edge = dependency (C5 depends on C4, D4)
- Use for:
  - **Smart recalculation** (only update affected cells)
  - **Progress tracking** (show which sheet is being calculated)
  - **Validation** (detect circular references)

### 4.4 Real-time API
```
POST /api/recalculate
  { "field": "pv_power_kw", "value": 2500 }
  → { "status": "calculating", "progress": 0.3 }
  → { "status": "done", "results": {...} }

WebSocket /ws/live
  - Real-time progress updates
  - Cell-by-cell recalculation status
  - Final results pushed to frontend

GET /api/results
  → { "output_sheet": {...}, "financial": {...}, "monthly": {...} }

GET /api/export
  → CSV/PDF export of all results
```

### 4.5 Frontend Form Generation
```tsx
// Auto-generate from INPUT sheet metadata
const inputs = [
  { name: "pv_power_kw", label: "PV Power (kW)", type: "number", default: 2500 },
  { name: "battery_capacity_kwh", label: "Battery Capacity (kWh)", type: "number", default: 5000 },
  { name: "efficiency", label: "Efficiency (%)", type: "percentage", default: 90 },
  // ... 101 more fields
];

// When user changes input:
const handleChange = (field, value) => {
  socket.emit('recalculate', { field, value });
  // Results stream back via WebSocket
};
```

---

## 5. Project Structure (REVISED)

```
battery-simulator/
├── ARCHITECTURE_V2.md          ← This file
├── FORMULAS_ANALYSIS.json      ← 33,412 formulas analyzed
├── DEPENDENCY_GRAPH.json       ← Cell dependencies
│
├── backend/
│   ├── main.py                 (FastAPI app)
│   ├── formula_engine/
│   │   ├── evaluator.py        (Excel formula → Python)
│   │   ├── dependency_graph.py  (NetworkX graph)
│   │   └── cache.py            (Redis caching)
│   ├── api/
│   │   ├── routes.py           (/api/recalculate, /ws/live)
│   │   └── schemas.py          (Pydantic models)
│   └── data/
│       ├── load_excel.py       (Parse .xlsx)
│       └── models.py           (SQLAlchemy for prices)
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── InputForm.tsx    (104 fields)
│   │   │   ├── Results.tsx      (Charts & tables)
│   │   │   └── ProgressBar.tsx  (Live progress)
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts  (Live updates)
│   │   └── styles/
│   │       └── index.css
│   └── package.json
│
├── docker-compose.yml          (FastAPI + Redis)
├── requirements.txt            (Python deps)
└── .env                        (Config)
```

---

## 6. Development Phases (REVISED)

| Phase | Task | Priority |
|-------|------|----------|
| **1** | Load Excel → FORMULAS_ANALYSIS.json | ✅ DONE |
| **2** | Build dependency graph (NetworkX) | 🔴 HIGH |
| **3** | Implement formula evaluator (50+ Excel functions) | 🔴 HIGH |
| **4** | FastAPI backend with /recalculate endpoint | 🔴 HIGH |
| **5** | React frontend with 104 input fields | 🔴 HIGH |
| **6** | WebSocket live updates | 🟡 MEDIUM |
| **7** | Caching layer (Redis) | 🟡 MEDIUM |
| **8** | Export results (CSV, PDF) | 🟡 MEDIUM |
| **9** | Testing & optimization | 🟡 MEDIUM |
| **10** | Deployment (Docker, AWS) | 🟢 LOW |

---

## 7. Success Metrics

- ✅ Recalculation time: < 500ms for input change
- ✅ All 33,412 formulas execute correctly
- ✅ Results match Excel (±0.01%)
- ✅ Frontend responsive with 104 inputs
- ✅ WebSocket streams updates live
- ✅ Can export results to CSV/PDF

---

## 8. Critical Success Factors

1. **Accurate Formula Translation** — Excel → Python
   - SUMIF, AVERAGEIFS, IF (nested)
   - Cross-sheet references (Sheet!Cell)
   - Date/time functions
   - Financial functions (NPV, IRR if needed)

2. **Dependency Graph Correctness** — Ensure all 33,412 cells mapped
   - Topological sort for recalculation order
   - Detect circular references early
   - Cache only valid states

3. **Performance** — 40,003 cells recalculated in < 500ms
   - Smart delta updates (only affected cells)
   - Redis cache for intermediate results
   - Parallel evaluation where possible (Celery)

4. **User Experience** — Make 104 inputs accessible
   - Group inputs by category (Project, Battery, Financial)
   - Show input constraints (min/max/units)
   - Real-time validation (red/green checks)

---

**Status:** 🔵 Ready for Phase 2 (Dependency Graph)  
**Owner:** Cyber  
**Updated:** 2026-05-08 16:30 UTC+2
