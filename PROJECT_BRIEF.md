# Battery Simulator - Project Brief

**Заказчик:** Ярослав  
**Проект:** Web-додаток для симуляції енергонакопичувача (батареї) сонячної станції  
**Локація:** Червоноград, Україна  
**Потужність:** 2.5 МВт сонячна станція + батарея для оптимізації доходу  
**Дата:** 2026-05-08

---

## 📊 Аналіз Вхідних Даних

### Excel Файл: `Червоноград_2.5_на_10_МВт_год.xlsx`

**Масштаб:**
- 📄 **13 листів** з різними функціями
- 📈 **33,412 формул** всього!
- 📋 **40,003 клітинок**
- 🎯 **104 INPUT параметра** (які користувач може змінювати)

**Структура листів:**
1. **Input** (172 формули) — параметри проекту (PV мощность, батарея, ставки дисконтування)
2. **CAPEX** (699 формул) — капітальні видатки
3. **Output базова/оптимізована** (215+226) — річна генерація
4. **Фінмодель базова/оптимізована** (5,694+5,967) — 25-річна фінмодель
5. **Помісячні дані** (1,030+2,150) — помісячні розрахунки
6. **Операційна модель базова** (9,892) — **8,771 рядків!** (погодинні дані на рік)
7. **Допоміжні листи:** ФЕС, ретроспективні ціни, середньомісячні години, гарантійні платежі

---

## 🏗️ Архітектура Системи

### High-Level Design

```
┌─────────────────────────────────────────────────┐
│ FRONTEND (React/TypeScript)                     │
│ - 104 Input Fields (інтерактивні форми)         │
│ - Real-time Charts & KPIs                       │
│ - Export (CSV, PDF)                             │
└────────────────┬────────────────────────────────┘
                 │ WebSocket (live updates)
┌────────────────▼────────────────────────────────┐
│ BACKEND (FastAPI)                               │
│ - Formula Engine (воспроизводит 33,412 формул)  │
│ - Dependency Graph (Networkx)                   │
│ - Redis Cache (для швидких пересчунків)         │
│ - Celery (async job queue)                      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│ DATA LAYER                                      │
│ - SQLite (histrorical prices, PV data)          │
│ - JSON (input parameters, current state)        │
│ - Excel export (FORMULAS_ANALYSIS.json)         │
└─────────────────────────────────────────────────┘
```

### Workflow: User Input → Real-time Recalculation

```
1. Користувач змінює INPUT (наприклад, "Батарея = 5000 kWh")
   ↓
2. Frontend → WebSocket → Backend
   ↓
3. FormulaEngine отримує зміну
   ↓
4. Dependency Graph визначає залежні клітинки
   ↓
5. Topological Sort → Порядок пересчуну
   ├─ CAPEX (5 ms)
   ├─ Output (2 ms)
   ├─ Фінмодель (100 ms) 🔥
   ├─ Помісячні дані (50 ms)
   └─ Операційна модель (300 ms) 🔥 8,771 рядків!
   ↓
6. Усі 33,412 формул пересчитуються
   ↓
7. WebSocket pushes results → Frontend
   ↓
8. Charts, tables, KPIs обновляются LIVE
```

**Час пересчуну:** ~700ms (без кеша), ~200ms (з Redis кешем)

---

## 🔗 Граф Залежностей

### Sheet-Level Dependencies
```
INPUT SHEET
    ↓
CAPEX (699 formulas)
    ├─→ Output базова (215)
    │   ├─→ Фінмодель базова (5,694)
    │   │   └─→ Помісячні дані базова (1,030)
    │   │
    │   └─→ Output оптимізована (226)
    │       ├─→ Фінмодель оптимізована (5,967)
    │       │   └─→ Помісячні дані оптимізована (2,150)
    │       │
    │       └─→ Результати батареї
    │
    └─→ Операційна модель базова (9,892 formulas!)
        ├─→ ФЕС (1,003)
        ├─→ Ретроспективні ціни (3,975)
        └─→ Середньомісячні години (1,416)
```

### Critical Chains
- **Input PV Power** → CAPEX → Output → Financial Model → Revenue projection
- **Input Battery Capacity** → Output optimized → Revenue premium (差額дохід від батареї)
- **Historical Prices** (8,786 rows) → Monthly aggregates → Revenue calculation

---

## 🎯 Ключові INPUT Параметри (104 штук)

**Проект:**
- Потужність ФЕС (кВ)
- Тип батареї (Li-ion, Lead-acid)
- Ємність батареї (кВт*год)
- КПД батареї (%)
- Деградація батареї (%/рік)

**Фінансові:**
- Ставка дисконтування (%)
- Тариф на електроенергію (грн/кВт*год)
-維утримання (% від CapEx)
- Період аналізу (років)
- Інфляція (%)

**Ринкові:**
- Вхідні дані з РДН (ринок добової мережі)
- Сезонні ціни
- Peak/off-peak години

---

## 🔧 Tech Stack

| Компонент | Технологія | Причина |
|-----------|-----------|---------|
| Frontend | React + TypeScript | Real-time UI, interactive |
| Backend API | FastAPI | Async, fast, OpenAPI docs |
| Formula Engine | Python native | Direct evaluation |
| Dependency Graph | NetworkX | Graph algorithms |
| Caching | Redis | Fast intermediate results |
| Async Jobs | Celery + Redis | Parallel sheet recalculation |
| Database | SQLite | Historical prices |
| Deployment | Docker | Containerized |

---

## 📋 Development Phases

| Phase | Task | Status | Duration |
|-------|------|--------|----------|
| 1 | ✅ Excel Analysis | **DONE** | - |
| 2 | Build Dependency Graph | Pending | 2-3 days |
| 3 | Implement Formula Evaluator | Pending | 3-5 days |
| 4 | FastAPI Backend | Pending | 3-4 days |
| 5 | React Frontend | Pending | 3-4 days |
| 6 | WebSocket Live Updates | Pending | 2 days |
| 7 | Testing & Optimization | Pending | 3-4 days |
| 8 | Deployment | Pending | 2 days |

**Загальна тривалість:** ~3-4 тижні (залежить від паралелізму)

---

## 🚀 What's Ready for Review

✅ **ARCHITECTURE_V2.md** — Full 3-layer design  
✅ **DEPENDENCY_GRAPH.md** — Complete dependency chains & recalculation order  
✅ **FORMULAS_ANALYSIS.json** — Parsed formulas & cell mapping  
✅ **PROJECT_BRIEF.md** — This document

---

## 🎓 Quality Assurance

**Pipeline:**
1. Cyber (Диспетчер) → обговорює вимоги з Ярославом
2. Codex Agent (Контроллер) → перевіряє спеціфікацію
3. Backend Agent → реалізує API
4. Frontend Agent → реалізує UI
5. QA Agent → тестування

**Принципи:**
- Детальні специфікації перед кодуванням
- Перевірка якості на кожному етапі
- Ітеративне покращення за фідбеком Ярослава

---

## ❓ Для Обговорення з Ярославом

1. **Ціль проекту:** Максимізація доходу? Оптимізація батареї? Обидва?
2. **Батарея:** Які технічні характеристики батареї?
3. **Ринок:** РДН або оптовий ринок (ДМЕК)? Прогноз цін?
4. **Період:** 1 рік? 25 років?
5. **Сценарії:** Базовий + оптимізований, або ще інші?
6. **Пріоритети:** Speed to market? Точність? Scalability?
7. **Экспорт:** Формати звітів? Інтеграція з іншими системами?
8. **Deployment:** Cloud (AWS/Azure)? On-premise? Обидва?

---

**Готово для детального обговорення!** 🚀

Status: **Architecture Review Phase**  
Next: Обговорення вимог з Ярославом
