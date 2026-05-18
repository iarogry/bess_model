# Как загружать реальные данные с OREE.com.ua

**Дата:** 2026-05-10  
**Статус:** Готово к использованию

---

## 🔗 Источники Данных OREE

### Основной сайт
- **URL:** https://www.oree.com.ua
- **Цены РДН:** https://www.oree.com.ua/index.php/pricectr
- **День-вперед (DAM):** https://www.oree.com.ua/index.php/control/results_mo/DAM

### Формат данных
```
Дата: DD.MM.YYYY
Часы: 1-24 (или 1-25, где 25:00 = последний час)
Цена: грн/MWh (без ПДВ)
```

---

## 📥 Способ 1: Автоматический Парсинг (Рекомендуется)

### Установить зависимости
```bash
cd battery-simulator
pip install beautifulsoup4 requests
```

### Запустить загрузку
```bash
python3 src/data/fetch_oree_real.py
```

**Что произойдет:**
1. Парсит HTML таблицы с OREE
2. Извлекает цены за каждый час
3. Загружает в SQLite (data.db)
4. Логирует прогресс + ошибки

### Пример вывода
```
INFO: Loading 30 days from OREE (polite rate: 2.0s)
INFO: ✅ 2026-05-10 - 24 prices
INFO: ✅ 2026-05-09 - 24 prices
...
INFO: Completed: 28/30 days loaded, 2 failed
```

---

## 📊 Способ 2: Вручную с CSV/XLS

### Шаг 1: Скачать с OREE
1. Перейти на https://www.oree.com.ua/index.php/pricectr
2. Найти "Download XLS" (если доступно)
3. Скачать файл (Excel, CSV)

### Шаг 2: Загрузить в БД
```python
import pandas as pd
import sqlite3

# Читаем Excel
df = pd.read_excel('prices.xlsx', sheet_name='DAM')

# Преобразуем в формат (date, hour, price)
# Формат Excel обычно: даты в столбцах, часы в строках

conn = sqlite3.connect('data.db')
for idx, row in df.iterrows():
    date = row['date']  # или parse from column
    hour = row['hour']
    price = row['price_hrn_per_mwh']
    
    conn.execute("""
        INSERT OR REPLACE INTO prices
        (date, hour, price_hrn_per_mwh, source)
        VALUES (?, ?, ?, 'oree_manual')
    """, (date, hour, price))

conn.commit()
```

---

## 🔍 Структура Данных OREE

### Типичный формат HTML таблицы

```html
<table>
  <tr>
    <th>Hour</th>
    <th>Price (грн/MWh)</th>
  </tr>
  <tr>
    <td>1</td>
    <td>2500.00</td>
  </tr>
  <tr>
    <td>2</td>
    <td>2450.50</td>
  </tr>
  ...
  <tr>
    <td>24</td>
    <td>3100.00</td>
  </tr>
</table>
```

### Наша БД структура
```sql
CREATE TABLE prices (
  date TEXT,      -- "2025-05-10"
  hour INTEGER,   -- 1-24
  price_hrn_per_mwh REAL,  -- 2500.00
  source TEXT     -- 'oree', 'entsoe', 'oree_manual'
);
```

---

## ⚙️ Опции Загрузки

### Вариант 1: Только последний день
```bash
python3 -c "
from src.data.fetch_oree_real import OREERealFetcher
from datetime import datetime

fetcher = OREERealFetcher()
today = datetime.now().strftime('%Y-%m-%d')
result = fetcher.fetch_daily_prices(today)
print(f'Loaded: {result}')
"
```

### Вариант 2: Последние 30 дней
```bash
python3 src/data/fetch_oree_real.py
# (автоматически загружает 30 дней)
```

### Вариант 3: Полный год
```python
from src.data.fetch_oree_real import OREERealFetcher

fetcher = OREERealFetcher()
fetcher.load_historical_range_real(
    start_date="2025-05-10",
    end_date="2026-05-09",
    rate_limit_sec=2.0  # Вежливое ограничение скорости
)
```

---

## 🚨 Проблемы & Решения

### Проблема 1: "Connection timeout"
```
Решение: Увеличить timeout или повторить позже
```

### Проблема 2: "Could not parse prices"
```
Решение: HTML структура могла измениться
        Проверить вручную на сайте OREE
        Обновить парсер в fetch_oree_real.py
```

### Проблема 3: "HTTP 403 (Forbidden)"
```
Решение: OREE блокирует автоматический доступ
        Скачать вручную с сайта (способ 2)
        Использовать VPN если нужно
```

---

## 📈 После Загрузки

### Проверить данные
```bash
sqlite3 data.db
> SELECT date, COUNT(*) as hours FROM prices GROUP BY date LIMIT 5;
2025-05-10|24
2025-05-11|24
2025-05-12|24
...
```

### Запустить симуляцию с реальными данными
```bash
python3 run_simulation.py
```

### Результаты
```
======================================================================
 BATTERY SIMULATOR - FULL YEAR RUN (WITH REAL OREE PRICES)
======================================================================

[1/3] Preparing price data...
[2/3] Generating demand profile...
[3/3] Running full-year simulation...

Annual Revenue: ??? грн  (зависит от цен!)
```

---

## 🔗 Альтернатива: ENTSO-E API

Если OREE парсинг не работает:

```bash
# Установить
pip install entsoe-py

# Использовать
from entsoe import Client
import pandas as pd

client = Client(security_token='YOUR_TOKEN')

# UA bidding zone
power = client.query_day_ahead_prices(
    country_code='UA',  # или '10YUA-WEPS-----0'
    start=pd.Timestamp('2025-05-10', tz='UTC'),
    end=pd.Timestamp('2026-05-09', tz='UTC')
)

# Загрузить в БД...
```

**Регистрация:** https://transparency.entsoe.eu/

---

## 📊 Данные для Тестирования

Если нужны тестовые данные:

```python
# Используй симулированные цены (уже в коде)
from src.data.fetch_oree import OREEPriceFetcher

fetcher = OREEPriceFetcher()
fetcher.load_historical_range("2025-05-10", "2026-05-09")

# Это создаст реалистичные цены (не идеальные, но достаточно для тестирования)
```

---

## ✅ Чек-лист

- [ ] Установлены зависимости (beautifulsoup4, requests)
- [ ] Скрипт fetch_oree_real.py доступен
- [ ] Проверен доступ к OREE.com.ua
- [ ] Загружены данные (автоматично или вручную)
- [ ] Проверены данные в SQLite
- [ ] Запущена симуляция с реальными ценами

---

**Готово! Теперь симуляция будет использовать реальные РДН цены с OREE. 📈**
