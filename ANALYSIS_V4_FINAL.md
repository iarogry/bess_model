# Аналіз V4_FINAL Battery Simulator - Виявлені проблеми та запропоновані рішення

## 1. РЕЗУЛЬТАТИ ТЕСТУВАННЯ

### V4_FINAL з синтетичним спросом (2024 PVsyst + RDN prices):
- **Річний дохід:** 911,789 грн
- **Дневний в середньому:** 2,498 грн
- **Батарея:** SOC падає до 2006.4 kWh (мінімум 20%) кожен вечір

### V4_FINAL з реальним спросом з Excel (2026):
- **Дневний дохід (приклади):**
  - 2026-01-01: 10,692 грн
  - 2026-01-02: 9,249 грн
  - 2026-01-03: 9,415 грн
  - **Потенційна річна:** ~3.6M грн (якщо продовжити)

### Чому різниця така велика?
1. **Синтетичний спрос (170 kWh/день) вищий ніж реальний (155.66 kWh/день)**
2. **Реальний спрос має варіабельність** (0-285 kWh/день), що дозволяє батареї краще циклювати
3. **Ціни РДН (2026) більш сприятливі** для арбітражу

---

## 2. КРИТИЧНІ ПРОБЛЕМИ АРХІТЕКТУРИ

### 🔴 **Проблема 1: Батарея повністю розряджається кожен день**
```
SoC траєкторія за день:
  Ранок:   5000-5100 kWh (після ночі)
  Полудень: 4800-5200 kWh (заряджання PV)
  Вечір:   2006.4 kWh (падіння до мінімуму)
```
**Причина:** Оптимізатор не знає про наступний день, тому розряджає батарею максимально (максимізує дохід сьогодні).

**Наслідок:** 
- Жоден запас енергії на непередбачене
- Батарея не може допомогти в критичні моменти
- Нереалістично для промислової операції

---

### 🔴 **Проблема 2: Дневна оптимізація vs. Динамічна оптимізація**
**Поточний підхід (V4):** Оптимізує кожен день окремо, ігноруючи попередній/наступний дні.

**Недолік:**
- LP розв'язується 365 разів (незалежно)
- Немає пам'яті про енергетичний стан системи
- Невизначена "граничні умови" між днями (rollover SOC)

**Рішення:** 
- Додати 24h lookahead (знати ціни/спрос на завтра)
- Додати Multi-day optimization (48-72h горизонт)

---

### 🔴 **Проблема 3: CHP (когенерація) не враховується**
**Дані в Excel:** 
- Лист "ФЕС" (Solar Frontend)
- Вартість КГУ генерації vs. grid prices

**Недолік:**
- Оптимізатор тільки торгує на РДН
- Не враховує CHP як резервного джерела при високих цінах
- Може втратити дохід від CHP-підтримки дорогих годин

---

### 🟡 **Проблема 4: Попит невизначений у реальній операції**
**Поточний статус:**
- Реальний попит: 155.66 kWh/день (середньо)
- Варіабельність: 0-285 kWh/день (огроменна!)
- Джерело: Лист "Операційна модель (1 рік, базова)" Col 45

**Недолік:**
- Нулі в попиті (0 kWh) = виходні дні?
- Пики до 285 kWh = коли/як?
- Оптимізатор не адаптується до цієї варіабельності

---

## 3. ЗАПРОПОНОВАНІ РІШЕННЯ

### ✅ **Рішення 1: Додати день-to-day rollover SOC**
```python
class Optimizer24hV4_WithRollover:
    def optimize_period(self, start_date, end_date, initial_soc=5016):
        current_soc = initial_soc
        for day in date_range(start_date, end_date):
            result = self.optimize_day(day, initial_soc=current_soc)
            current_soc = result['final_soc']  # Запам'ятати для наступного дня!
            yield result
```

**Вплив:** Батарея буде мати пам'ять між днями.

---

### ✅ **Рішення 2: Додати обмеження мінімального SOC на кінець дня**
```python
# В LP constraints:
soc[23] >= 0.5 * battery_capacity  # Мінімум 50% на кінець дня
```

**Вплив:** Батарея завжди матиме запас для непередбачених ситуацій.

---

### ✅ **Рішення 3: Додати 24h Lookahead**
```python
# Знати ціни/спрос на завтра
tomorrow_prices = load_rdn_prices(date + 1 day)
tomorrow_demand = load_demand_profile(date + 1 day)

# Врахувати в оптимізації сьогодні
# Якщо завтра дешево - заряджати менше сьогодні
# Якщо завтра дорого - заряджати максимально
```

**Вплив:** Оптимальніші рішення про зарядження батареї.

---

### ✅ **Рішення 4: Добавити CHP в оптимізацію**
```python
# Добавити змінні:
chp_generation[h]  # Генерація КГУ на годину h
chp_export[h]      # Експорт КГУ на РДН

# Логіка:
# Якщо grid_price[h] > chp_cost + tariff:
#     Запустити CHP для експорту
```

**Вплив:** Додатковий дохід від КГУ в дорогі години.

---

### ✅ **Рішення 5: Адаптивна оптимізація на основі попиту**
```python
# Якщо попит = 0 (вихідний):
#     Максимізувати накопичення енергії в батарею
# Якщо попит = max (піковий):
#     Мінімізувати закупівлю на РДН, використовувати батарею
```

**Вплив:** Краще використання батареї для коридорних годин.

---

## 4. АРХІТЕКТУРА V5: RECOMMENDED APPROACH

```
┌─────────────────────────────────────────────────────────────┐
│  V5: Multi-Day Optimizer with CHP & Lookahead              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Data Loader (Real Excel):                              │
│     - PVsyst (8784 hours, cycled)                          │
│     - RDN prices (hourly, 2026)                            │
│     - Demand (hourly, 2026, variable 0-285)               │
│     - CHP generation cost                                  │
│                                                             │
│  2. Optimizer (48-72h rolling window):                      │
│     - Variables: PV→demand/export/charge, battery          │
│                  charge/discharge, grid import/export,     │
│                  CHP generation, SOC                       │
│     - Constraints:                                         │
│        * Energy balance (demand ≥ supply)                  │
│        * PV conservation (pv = demand + export + charge)   │
│        * Battery SOC (min=40%, max=80%, EOD≥50%)          │
│        * CHP (only if price > cost)                       │
│        * Lookahead penalty (know tomorrow's prices)        │
│     - Objective: Maximize revenue - costs                  │
│                                                             │
│  3. Rolling Execution:                                     │
│     - Day N-1: Optimize days N, N+1 (48h)                │
│     - Execute day N, carry over SOC                        │
│     - Day N: Optimize days N+1, N+2                       │
│                                                             │
│  4. Reporting:                                             │
│     - Daily revenue + SOC trajectory                       │
│     - CHP utilization %                                    │
│     - Battery cycle count & degradation                    │
│     - vs. Reference (Excel model)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. NEXT STEPS

### Priority 1 (CRITICAL):
1. ✅ Implement day-to-day rollover SOC (add initial_soc parameter)
2. ✅ Add end-of-day SOC minimum constraint (50%)

### Priority 2 (HIGH):
3. ⏳ Implement 24h lookahead (know tomorrow's prices)
4. ⏳ Add CHP generation logic (generator cost vs. grid price)

### Priority 3 (MEDIUM):
5. ⏳ Multi-day rolling optimization (48-72h window)
6. ⏳ Adaptive demand-based strategy

### Priority 4 (NICE-TO-HAVE):
7. ⏳ Real-time SCADA integration
8. ⏳ Web dashboard (Streamlit)

---

## 6. МЕТРИКИ ДЛЯ ОЦІНКИ

| Метрика | V4_FINAL (поточна) | V5 (очікуване) |
|---|---|---|
| Річний дохід | 911K (2024) / 3.6M (2026) | 3.8M+ (з CHP) |
| Дневне SOC мін | 2006 kWh (0% резерву) | 4000+ kWh (40% резерву) |
| Батарея циклів | 4.9 | 2-3 (менше деградації) |
| CHP утиліз. | 0% | 15-25% |
| Lookahead мінусу | Не враховане | +2-5% дохід |

