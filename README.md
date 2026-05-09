# Chervonohrad BESS Simulator

**Battery Energy Storage System Modeling for Renewable Integration**

Інструмент для швидкого опрацювання різних моделей батарей, пошуку найкращої схеми роботи з СЕС, КГУ/газом та іншими видами генерації, та видачі звітів моделювання інвесторам для прийняття обгрунтованого рішення.

---

## 🎯 Основні можливості

### 1. **BESS Constructor**
- Ручне додавання моделей батарей (Hithium, CATL, BYD, LG, Samsung)
- Параметри: потужність, ємність, CAPEX, OPEX, ефективність
- Збереження конфігурацій для повторного використання

### 2. **Generation Mix Builder**
- **СЕС (Сонячна):** Усредненная модель на базі Червонограда + коррекція потужності
- **Ветер:** Усредненные данные для України (~30% CF)
- **Газ (КГУ):** Включення/вимкнення на основі ціни газу vs. себестоимість
- **РДН Ціни:** Інтеграція з УКРЕНЕРГО API (24/365 годинні котировки)

### 3. **Fast Simulation**
- Моделювання 1-го року (8760 годин)
- Екстраполяція на 10 років
- **Output:** < 1 секунда
- **Звіти:** до 60 секунд (async)

### 4. **Financial Analysis**
- IRR, NPV, Payback Period розраховуються автоматично
- Облік інфляції (3%/рік)
- CAPEX + OPEX + Revenue для кожного року

### 5. **Sensitivity Analysis**
- Варіування цієї газу (±10%)
- Варіування выработки СЕС/Вітру (±20%)
- Порівняння сценаріїв

### 6. **Reporting**
- **PDF звіти** з графіками, таблицями, висновками
- **Excel звіти** з детальним розбором по місяцях/рокам
- Автоматична генерація для інвестора

---

## 🏗️ Архітектура

```
chervonohrad-bess-sim/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── rdn_api.py           # УКРЕНЕРГО RDN integration
│   ├── simulator.py         # BESS simulation engine
│   └── requirements.txt      # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── BESSConstructor.jsx    # BESS configuration
│   │   │   ├── ScenarioSelector.jsx   # Generation mix
│   │   │   └── OutputDashboard.jsx    # Results visualization
│   │   └── App.jsx          # Main application
│   ├── package.json
│   └── vite.config.js
│
└── docs/
    └── API_SPEC.md          # API documentation
```

### **Tech Stack**

**Backend:**
- FastAPI (Python async framework)
- Pydantic (data validation)
- aiohttp (async HTTP client for RDN API)
- Pandas + NumPy (data processing)
- ReportLab + WeasyPrint (PDF generation)
- openpyxl (Excel generation)

**Frontend:**
- React 18
- Plotly.js (charts & graphs)
- Tailwind CSS (styling)
- Axios (API calls)
- Zustand (state management)

**Database:** PostgreSQL + Redis (when ready)

---

## 🚀 Quick Start

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

App will be available at: `http://localhost:5173`

---

## 📊 API Endpoints

### BESS Configuration
- `POST /bess/create` - Create new BESS config
- `GET /bess` - List all configs
- `GET /bess/{id}` - Get specific config
- `DELETE /bess/{id}` - Delete config

### Gas Scenarios
- `POST /gas/scenarios` - Get predefined scenarios (Low/Mid/High/Custom)

### Simulation
- `POST /simulate` - Run simulation (returns in < 1 sec)
- `GET /simulation/{id}` - Get simulation results
- `POST /simulate/compare` - Compare multiple scenarios

### Reports
- `POST /report/pdf` - Generate PDF report (async)
- `POST /report/excel` - Generate Excel report (async)

---

## 📈 Example Simulation Flow

### Input Stage
1. **Create BESS:** Hithium 5MW/20MWh (€75k CAPEX/MWh)
2. **Set Solar:** 10 MW (усредненная модель Украины)
3. **Set Wind:** 5 MW (30% capacity factor)
4. **Choose Gas:** Mid scenario (€5/MMBtu)

### Simulation
```python
{
  "generation_mix": {
    "bess": {...},
    "solar_mw": 10,
    "wind_mw": 5,
    "gas_enabled": true,
    "gas_scenario": {"type": "mid", "gas_price_per_mmbtu": 5.0}
  },
  "year": 2025,
  "simulation_years": 10
}
```

### Output (< 1 second)
```json
{
  "simulation_id": "abc-123",
  "output": {
    "irr_pct": 12.5,
    "npv_eur": 2500000,
    "payback_years": 7.3,
    "capex_eur": 1250000,
    "annual_results": [
      {
        "year": 1,
        "total_revenue_uah": 125000,
        "total_opex_uah": 25000,
        "cumulative_cashflow_uah": 100000
      },
      ...
    ],
    "sensitivity": [...]
  }
}
```

---

## 🔧 Configuration

### Gas Scenarios (Predefined)

| Scenario | Price | Cost | Profitability |
|----------|-------|------|----------------|
| **Low** | $3/MMBtu | Low | High margins |
| **Mid** | $5/MMBtu | Medium | Medium margins |
| **High** | $8/MMBtu | High | Low margins |
| **Custom** | User input | Variable | Custom |

### BESS Parameters

| Parameter | Range | Notes |
|-----------|-------|-------|
| Power (MW) | 0.1-100 | Inverter rating |
| Capacity (MWh) | 1-500 | Battery pack size |
| CAPEX/MWh | €500-2500 | Depends on chemistry |
| CAPEX/MW | €200-1000 | Power electronics |
| OPEX (%/yr) | 0.5-5% | Of CAPEX |
| Efficiency | 80-99% | Round-trip |

### RDN Prices

- **Source:** УКРЕНЕРГО Public API
- **Format:** 24 hourly prices per day (UAH/MWh)
- **Caching:** Daily (updated at midnight)
- **Fallback:** Synthetic realistic prices if API unavailable

---

## 📝 Simulation Logic

### 1. Solar Generation
```
Усредненная модель Украины:
- Gaussian curve centered at 12:00 (noon)
- Peak capacity factor: 80%
- Annual CF: 25-30%
```

### 2. Wind Generation
```
Усредненные данные для Украины:
- Base capacity factor: 30%
- Hourly variation: ±10%
- Annual CF: 25-35%
```

### 3. Gas Generation
```
if (RDN_price > gas_cost * 1.1) then
  output = min(min_load % * capacity, max_power)
else
  output = 0
```

### 4. Battery Dispatch
```
Simple rule-based:
- Charge when RDN < 2000 UAH/MWh
- Discharge when RDN > 3000 UAH/MWh
- Respect SOC limits (0-100%)
```

### 5. Financial Calculation
```
Revenue = (Solar + Wind + Gas) × RDN_price × hours
OPEX = (Solar + Wind + Gas) × €50/MWh + fixed costs
CAPEX = initial investment
NPV = ∑(CF / (1+r)^t) where r = 8%
IRR = rate where NPV = 0
```

---

## 🔄 Workflow for Investors

1. **Define Scenarios**
   - Create BESS configs (battery type, size, cost)
   - Select generation mix (solar, wind, gas)
   - Choose gas price scenario

2. **Run Simulation**
   - Click "Run Simulation"
   - Results available in < 1 second
   - View IRR, NPV, Payback, Annual Cashflow

3. **Analyze Sensitivity**
   - See how changes in gas price affect IRR
   - Understand risks with ±20% wind/solar variations
   - Make informed decisions

4. **Generate Reports**
   - PDF: Executive summary + charts + recommendations
   - Excel: Detailed monthly/yearly breakdown for modeling

---

## 📚 Example Scenarios

### Scenario 1: BESS-Only (No Generation)
```
Configuration: Hithium 5MW/20MWh
Solar: 0 MW, Wind: 0 MW, Gas: No
→ IRR: 8-12% (arbitrage on RDN prices)
→ Payback: 10-12 years
→ Low risk, lower returns
```

### Scenario 2: Solar + BESS (Balanced)
```
Configuration: Hithium 5MW/20MWh
Solar: 10 MW, Wind: 0 MW, Gas: No
→ IRR: 14-18% (renewable + storage synergy)
→ Payback: 6-8 years
→ Medium risk, good returns
```

### Scenario 3: Hybrid (Solar + Wind + Gas + BESS)
```
Configuration: Hithium 5MW/20MWh
Solar: 10 MW, Wind: 5 MW, Gas: Yes (Mid)
→ IRR: 18-25% (diversified, gas backup)
→ Payback: 5-6 years
→ Higher complexity, excellent returns
```

---

## 🐛 Known Limitations

1. **Synthetic RDN Prices:** When API unavailable, uses realistic but synthetic data
2. **Hourly Dispatch:** Simple rule-based (could be optimized with ML)
3. **Weather Data:** Averaged for region (not real-time)
4. **Tax:** Not included in current model (configurable for investor)
5. **Grid Constraints:** Not modeled (assumes unlimited export)

---

## 🔮 Future Enhancements

- [ ] Real-time RDН API integration validation
- [ ] Machine learning optimization for battery dispatch
- [ ] Multi-year weather scenarios (dry/wet years)
- [ ] Grid services revenue (frequency regulation, reserve)
- [ ] CO2 credit revenue modeling
- [ ] Degradation modeling for battery lifespan
- [ ] Tax & incentives scenarios (NEC, green bonds)
- [ ] Dashboard export to PowerPoint for presentations

---

## 📞 Support

For questions, issues, or feature requests:
- Email: support@example.com
- Docs: `/docs/API_SPEC.md`
- Issues: GitHub Issues (coming soon)

---

**Built with ⚡ for Chervonohrad Project**
