"""
FastAPI routes for data imports
FastAPI маршруты для імпорту даних
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import tempfile
from pathlib import Path
from typing import Optional
import logging

from handlers import FormImportHandler, CSVImportHandler, JSONImportHandler
from schemas import (
    FormImportRequest, CSVImportRequest, JSONImportRequest,
    ImportResponse, TemplateResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["Import"])

# Database path (можна отримати з конфігу)
DB_PATH = "data.db"


# ============================================================================
# FORM IMPORT (1-5 параметрів)
# ============================================================================

@router.post("/form", response_model=ImportResponse)
async def import_form(request: FormImportRequest) -> ImportResponse:
    """
    Імпортувати параметри з форми (1-5 параметрів)
    
    Приклад:
    ```json
    {
        "parameters": [
            {
                "param_name": "rated_power_mw",
                "param_value": 2.5,
                "param_unit": "MW",
                "param_type": "numeric"
            }
        ]
    }
    ```
    """
    try:
        handler = FormImportHandler(DB_PATH)
        result = handler.handle(request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
    
    except Exception as e:
        logger.error(f"Form import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка імпорту: {str(e)}")


# ============================================================================
# CSV IMPORT (6-20 параметрів)
# ============================================================================

@router.post("/csv", response_model=ImportResponse)
async def import_csv(file: UploadFile = File(...), 
                     project_id: Optional[int] = None,
                     source_id: Optional[int] = None) -> ImportResponse:
    """
    Імпортувати параметри з CSV файлу (6-20 параметрів)
    
    CSV формат:
    ```
    Parameter Name,Value,Unit,Type,Description,Editable
    rated_power_mw,2.5,MW,numeric,Номінальна потужність,TRUE
    efficiency_percent,85,%,numeric,Ефективність,TRUE
    ```
    """
    
    temp_file = None
    try:
        # Зберегти завантажений файл тимчасово
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Імпортувати
        request = CSVImportRequest(
            project_id=project_id,
            source_id=source_id,
            file_path=temp_file.name
        )
        
        handler = CSVImportHandler(DB_PATH)
        result = handler.handle(request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка імпорту CSV: {str(e)}")
    
    finally:
        # Очистити тимчасовий файл
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()


# ============================================================================
# JSON IMPORT (20+ параметрів)
# ============================================================================

@router.post("/json", response_model=ImportResponse)
async def import_json(file: UploadFile = File(...),
                      project_id: Optional[int] = None) -> ImportResponse:
    """
    Імпортувати проект з JSON файлу (20+ параметрів, мультиджерела)
    
    JSON формат:
    ```json
    {
        "project": {
            "name": "Chervonohrad System",
            "location": "Chervonohrad, Ukraine",
            "timezone": "Europe/Kyiv",
            "energy_sources": [
                {
                    "name": "Solar PV",
                    "type": "PV",
                    "category": "generation",
                    "parameters": {
                        "rated_power_mw": {"value": 2.5, "unit": "MW"},
                        "efficiency_percent": {"value": 85, "unit": "%"}
                    }
                }
            ]
        }
    }
    ```
    """
    
    temp_file = None
    try:
        # Зберегти завантажений файл тимчасово
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        
        # Імпортувати
        request = JSONImportRequest(
            project_id=project_id,
            file_path=temp_file.name
        )
        
        handler = JSONImportHandler(DB_PATH)
        result = handler.handle(request)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Помилка імпорту JSON: {str(e)}")
    
    finally:
        # Очистити тимчасовий файл
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()


# ============================================================================
# TEMPLATES (Завантаження шаблонів)
# ============================================================================

@router.get("/templates/csv")
async def get_csv_template() -> TemplateResponse:
    """
    Отримати шаблон CSV для імпорту
    
    Шаблон містить приклади для 6-20 параметрів
    """
    
    csv_content = """Parameter Name,Value,Unit,Type,Description,Editable
rated_power_mw,2.5,MW,numeric,Номінальна потужність сонячної електростанції,TRUE
efficiency_percent,85,%,numeric,Ефективність PV модулів,TRUE
capacity_factor_annual_percent,18,%,numeric,Річний коефіцієнт використання,FALSE
installed_cost_uah_per_kw,45000,UAH/kW,cost,Вартість установки,TRUE
maintenance_cost_annual_percent,2,%,cost,Річні витрати на обслуговування,TRUE
lifetime_years,25,years,time,Розрахунковий період експлуатації,FALSE
degradation_annual_percent,0.5,%,constraint,Річна деградація,FALSE"""
    
    return TemplateResponse(
        format="csv",
        filename="parameters_template.csv",
        description="Шаблон CSV для імпорту 6-20 параметрів",
        content=csv_content,
        mime_type="text/csv"
    )


@router.get("/templates/json")
async def get_json_template() -> TemplateResponse:
    """
    Отримати шаблон JSON для імпорту
    
    Шаблон містить повну структуру проекту з кількома джерелами
    """
    
    json_content = """{
  "project": {
    "name": "Chervonohrad Energy System",
    "location": "Chervonohrad, Ukraine",
    "timezone": "Europe/Kyiv",
    "description": "2.5 MW PV + 10 MWh BESS + Grid Trading System",
    "energy_sources": [
      {
        "name": "Solar PV Array",
        "type": "PV",
        "category": "generation",
        "description": "Фотоелектрична система",
        "parameters": {
          "rated_power_mw": {
            "value": 2.5,
            "unit": "MW",
            "type": "numeric"
          },
          "efficiency_percent": {
            "value": 85,
            "unit": "%",
            "type": "numeric"
          },
          "capacity_factor_annual_percent": {
            "value": 18,
            "unit": "%",
            "type": "numeric"
          }
        }
      },
      {
        "name": "Battery Energy Storage",
        "type": "BESS",
        "category": "storage",
        "description": "Акумулювальна система",
        "parameters": {
          "capacity_mwh": {
            "value": 10,
            "unit": "MWh",
            "type": "numeric"
          },
          "max_charge_rate_mw": {
            "value": 2.5,
            "unit": "MW",
            "type": "numeric"
          },
          "max_discharge_rate_mw": {
            "value": 2.5,
            "unit": "MW",
            "type": "numeric"
          },
          "round_trip_efficiency_percent": {
            "value": 80,
            "unit": "%",
            "type": "numeric"
          }
        }
      },
      {
        "name": "Grid Connection",
        "type": "Grid",
        "category": "generation",
        "description": "Під'єднання до національної мережі",
        "parameters": {
          "max_import_mw": {
            "value": 5,
            "unit": "MW",
            "type": "numeric"
          },
          "max_export_mw": {
            "value": 2.5,
            "unit": "MW",
            "type": "numeric"
          }
        }
      }
    ]
  }
}"""
    
    return TemplateResponse(
        format="json",
        filename="project_template.json",
        description="Шаблон JSON для імпорту повних проектів (20+ параметрів)",
        content=json_content,
        mime_type="application/json"
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Перевірка здоров'я API"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "validators": {
            "form": True,
            "csv": True,
            "json": True
        },
        "database": DB_PATH
    }
