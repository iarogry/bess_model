# ENTSO-E API Setup для Ukraine (РДН)

**Дата:** 2026-05-10  
**Источник:** https://transparency.entsoe.eu/

---

## 🔗 Что это?

**ENTSO-E Transparency Platform** - европейская платформа с реальными ценами день-вперед для всех стран включая Украину.

**Ukraine bidding zones:**
- `10YUA-WEPS-----0` - UA-BEI (основная зона)
- `10Y1001C--000182` - UA-IPS (альтернативна)

---

## 📋 Шаг 1: Получить Security Token

### 1.1 Зарегистрироваться
1. Перейти: https://transparency.entsoe.eu/
2. Нажать "Register" (бесплатно)
3. Заполнить форму
4. Подтвердить email

### 1.2 Получить API Token
1. Логин на https://transparency.entsoe.eu/
2. Перейти: https://transparency.entsoe.eu/usermgmt/User/ManageAPITokens
3. Нажать "Create API Token"
4. Скопировать token (длинная строка вроде `abc123xyz...`)

**Пример token:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🚀 Шаг 2: Запустить загрузку

### 2.1 Установить зависимость
```bash
cd battery-simulator
pip install entsoe-py --break-system-packages
```

### 2.2 Способ 1: Через переменную окружения (Рекомендуется)
```bash
export ENTSOE_TOKEN="your_token_here"
python3 src/data/fetch_entsoe.py
```

### 2.2 Способ 2: Отредактировать скрипт
```python
# src/data/fetch_entsoe.py, строка 122
TOKEN = "your_token_here"  # Вставить свой token
```

Потом запустить:
```bash
python3 src/data/fetch_entsoe.py
```

---

## 📊 Результаты

```
INFO: Loading 30 days from ENTSO-E...
INFO: ✅ 2026-04-10
INFO: ✅ 2026-04-11
...
INFO: ✅ Loaded 30/30 days from ENTSO-E
```

**Данные загружены в:** `data.db`

---

## 🎯 Как использовать в коде

### Вариант 1: Автоматический (в скрипте)
```python
from src.data.fetch_entsoe import ENTSOEFetcher

fetcher = ENTSOEFetcher(security_token="your_token")
fetcher.load_historical_range("2025-05-10", "2026-05-09")
```

### Вариант 2: За год (заняло времени)
```bash
# Загружает 365 дней (может быть долгим!)
python3 -c "
from src.data.fetch_entsoe import ENTSOEFetcher
import os

token = os.getenv('ENTSOE_TOKEN')
fetcher = ENTSOEFetcher(security_token=token)
fetcher.load_historical_range('2025-05-10', '2026-05-09')
"
```

---

## 💡 Особенности

### Валюта
- ENTSO-E данные в **EUR/MWh**
- Скрипт конвертирует в **UAH/MWh** (1 EUR ≈ 40 UAH)
- Можно изменить коэффициент в коде

### Часовая зона
- ENTSO-E использует UTC
- Скрипт конвертирует в локальное время автоматически

### Лимиты
- Один запрос = один день (24 часа)
- Maximum: 1 год за раз
- API rate limit: приблизительно 1 запрос/секунду

---

## 🚨 Проблемы & Решения

### Проблема 1: "Invalid security token"
```
Решение: Проверить token
        Заново создать в: https://transparency.entsoe.eu/usermgmt/User/ManageAPITokens
        Скопировать точно (без пробелов)
```

### Проблема 2: "No prices returned"
```
Решение: День может быть выходной или нет данных
        Попробовать другой день
        Проверить дату (должна быть после 2015)
```

### Проблема 3: "Connection timeout"
```
Решение: ENTSO-E сервер перегружен
        Повторить позже
        Увеличить timeout в коде
```

### Проблема 4: entsoe-py not installed
```bash
Решение:
pip install entsoe-py --break-system-packages
```

---

## 📈 После загрузки

### Проверить данные
```bash
cd battery-simulator
sqlite3 data.db
> SELECT date, COUNT(*) as hours, AVG(price_hrn_per_mwh) as avg_price 
  FROM prices WHERE source='entsoe' 
  GROUP BY date LIMIT 5;
```

Пример вывода:
```
2026-04-10|24|105.50
2026-04-11|24|102.30
2026-04-12|24|108.75
```

### Запустить симуляцию с реальными ценами
```bash
python3 run_simulation.py
```

**Результат:** Симуляция с реальными ценами из ENTSO-E 🚀

---

## 🔗 Полезные ссылки

- **ENTSO-E Transparency:** https://transparency.entsoe.eu/
- **API Documentation:** https://entsoe-apy.berrisch.biz/
- **Ukraine prices page:** https://transparency.entsoe.eu/market/prices/show

---

## ✅ Чек-лист

- [ ] Зарегистрирован на ENTSO-E
- [ ] Получен Security Token
- [ ] entsoe-py установлен
- [ ] Token вставлен в скрипт или окружение
- [ ] Запущена загрузка
- [ ] Данные загружены в data.db
- [ ] Запущена симуляция

---

**Готово! Теперь у тебя реальные украинские цены РДН! 📊**
