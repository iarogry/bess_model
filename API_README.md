# Battery Simulator API

## Обзор

REST API для управления энергетическими проектами, импорта параметров и запуска оптимизации батареи.

Архитектура поддерживает **трёхуровневый импорт данных**:
1. **Веб-форма** (1-5 параметров)
2. **CSV файл** (6-20 параметров)
3. **JSON файл** (20+ параметров или полный проект)

---

## Установка

```bash
cd battery-simulator

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости (исправленные требования)
pip install fastapi uvicorn python-multipart aiofiles python-dateutil
```

## Запуск сервера

```bash
# Запустить API сервер на http://localhost:8000
python3 src/api/app.py

# или с uvicorn напрямую
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

## Структура API

```
/api/
├── /projects/
│   ├── GET /projects              # Список всех проектов
│   ├── POST /projects             # Создать новый проект
│   ├── GET /projects/{id}         # Получить проект
│   └── POST /projects/{id}/import # Импортировать данные
│
├── /import/
│   ├── POST /import/form          # Импорт через веб-форму (1-5 параметров)
│   ├── POST /import/csv           # Импорт CSV (6-20 параметров)
│   └── POST /import/json          # Импорт JSON (20+ параметров)
│
└── /optimize/
    ├── POST /optimize/daily       # Запустить однодневную оптимизацию
    └── GET /optimize/results/{id} # Получить результаты
```

---

## Примеры использования

### 1. Веб-форма (1-5 параметров)

**Endpoint:** `POST /api/import/form`

**Request:**
```json
{
  "project_id": 1,
  "source_id": 1,
  "parameters": [
    {
      "param_name": "rated_power_mw",
      "param_value": 2.5,
      "param_unit": "MW",
      "param_type": "numeric"
    },
    {
      "param_name": "efficiency_percent",
      "param_value": 88,
      "param_unit": "%",
      "param_type": "numeric"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Форма валідна (2 параметрів)",
  "project_id": 1,
  "source_id": 1,
  "data_count": 2
}
```

---

### 2. CSV Файл (6-20 параметров)

**Endpoint:** `POST /api/import/csv`

**Формат CSV:**
```csv
Parameter Name,Value,Unit,Type,Description,Editable
rated_power_mw,2.5,MW,numeric,Номінальна потужність ФЕС,TRUE
efficiency_percent,88,%,numeric,Ефективність батареї,TRUE
capacity_mwh,10,MWh,numeric,Ємність батареї,FALSE
charge_power_mw,2.5,MW,numeric,Потужність заряду,TRUE
discharge_power_mw,2.2,MW,numeric,Потужність розряду,TRUE
grid_tariff_uah_mwh,784.2,UAH/MWh,numeric,Тариф сітки,FALSE
```

**Request (multipart/form-data):**
```
POST /api/import/csv
Content-Type: multipart/form-data

project_id=1
source_id=1
csv_file=<file: parameters.csv>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "CSV валідний (6 параметрів)",
  "project_id": 1,
  "source_id": 1,
  "data_count": 6
}
```

---

### 3. JSON Файл (20+ параметрів)

**Endpoint:** `POST /api/import/json`

**Формат JSON:**
```json
{
  "project": {
    "name": "Chervonohrad Energy Storage",
    "location": "Chervonohrad, Ukraine",
    "timezone": "Europe/Kyiv",
    "currency": "UAH",
    "year": 2026,
    "energy_sources": [
      {
        "name": "Solar Farm",
        "type": "PV",
        "category": "generation",
        "parameters": {
          "rated_power_mw": {"value": 2.5, "unit": "MW"},
          "efficiency_percent": {"value": 85, "unit": "%"}
        }
      },
      {
        "name": "Battery Storage",
        "type": "BESS",
        "category": "storage",
        "parameters": {
          "capacity_mwh": {"value": 10, "unit": "MWh"},
          "efficiency_percent": {"value": 88, "unit": "%"},
          "charge_power_mw": {"value": 2.5, "unit": "MW"},
          "discharge_power_mw": {"value": 2.2, "unit": "MW"}
        }
      }
    ]
  }
}
```

**Request (multipart/form-data):**
```
POST /api/import/json
Content-Type: multipart/form-data

json_file=<file: project.json>
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "JSON валідний (2 джерел, 6 параметрів)",
  "project_id": 1,
  "energy_sources": 2,
  "data_count": 6
}
```

---

## Коды ошибок

| Код | Значение | Пример |
|-----|----------|--------|
| 200 | OK | Валидация пройдена, данные обработаны |
| 400 | Bad Request | Неверный формат входных данных |
| 404 | Not Found | Проект не найден |
| 422 | Validation Error | Ошибка валидации параметров |
| 500 | Server Error | Внутренняя ошибка сервера |

---

## Типы параметров

```python
ParameterType = {
    "numeric": "Числовое значение (int, float)",
    "constraint": "Ограничение (0-100%)",
    "cost": "Стоимость (UAH/MWh)",
    "time": "Время (часы, минуты)",
    "date": "Дата (YYYY-MM-DD)"
}
```

---

## Диапазоны значений

| Параметр | Мин | Макс | Примеры |
|----------|-----|------|---------|
| Потужність (MW) | 0.1 | 1000 | 2.5, 5.0, 100 |
| Ємність (MWh) | 0.1 | 10000 | 10, 50, 1000 |
| Ефективність (%) | 0.1 | 100 | 85, 88, 95 |
| Вартість (UAH/MWh) | 0 | 100000 | 784.2, 5000, 9000 |
| Час (хв) | 0 | 1440 | 60, 240, 480 |

---

## Шаблоны для скачивания

```
/templates/
├── parameters_template.csv  # CSV шаблон (6-20 параметров)
└── project_template.json    # JSON шаблон (полный проект)
```

Скачайте, отредактируйте, загрузите обратно.

---

## Интеграция с оптимизатором

После успешного импорта параметры сохраняются в БД и автоматически используются оптимизатором **V4-RDN-SHIFT**.

```bash
# Запустить однодневную оптимизацию
POST /api/optimize/daily
{
  "project_id": 1,
  "date": "2026-05-11",
  "use_real_data": true
}
```

---

## Логирование

Все операции логируются в `logs/api.log`:

```
[2026-05-11 14:32:15] INFO: Project 1 created
[2026-05-11 14:33:22] INFO: CSV import for source 1: 6 parameters
[2026-05-11 14:34:10] INFO: Optimization started for project 1
```

---

## Troubleshooting

**Q: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate
pip install fastapi uvicorn python-multipart
```

**Q: "Port 8000 already in use"**
```bash
# Используйте другой порт
uvicorn src.api.app:app --port 8001
```

**Q: "ValidationError: Energy source not found"**
```bash
# Убедитесь, что источник существует перед импортом параметров
POST /api/projects/{id}/sources (создать источник сначала)
```

---

## Развитие

**Фаза 1 (Текущая):** ✅ Валидаторы + API endpoints  
**Фаза 2 (Планы):** Интеграция с V4-RDN-SHIFT оптимизатором  
**Фаза 3 (Будущее):** Streamlit UI + результаты экспорт  

---

## Лицензия

Для Hlibodar Holdings, Chervonohrad, Ukraine  
Разработчик: Cyber ⚙️
