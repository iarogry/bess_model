"""
Pydantic schemas for FastAPI endpoints
Pydantic моделі для валідації вхідних даних API
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ParameterTypeEnum(str, Enum):
    """Типи параметрів"""
    NUMERIC = "numeric"
    CONSTRAINT = "constraint"
    COST = "cost"
    TIME = "time"
    DATE = "date"


class SourceTypeEnum(str, Enum):
    """Типи джерел енергії"""
    PV = "PV"
    BESS = "BESS"
    CHP = "CHP"
    GRID = "Grid"
    WIND = "Wind"
    HYDRO = "Hydro"


class SourceCategoryEnum(str, Enum):
    """Категорії джерел"""
    GENERATION = "generation"
    STORAGE = "storage"
    DEMAND = "demand"


# ============================================================================
# FORM IMPORT SCHEMAS (1-5 параметрів)
# ============================================================================

class FormParameterInput(BaseModel):
    """Один параметр з форми"""
    param_name: str = Field(..., description="Назва параметра", min_length=1, max_length=100)
    param_value: float = Field(..., description="Значення параметра")
    param_unit: str = Field(default="", description="Одиниця виміру", max_length=50)
    param_type: ParameterTypeEnum = Field(default=ParameterTypeEnum.NUMERIC, description="Тип параметра")
    
    class Config:
        schema_extra = {
            "example": {
                "param_name": "rated_power_mw",
                "param_value": 2.5,
                "param_unit": "MW",
                "param_type": "numeric"
            }
        }


class FormImportRequest(BaseModel):
    """Запит на імпорт з форми"""
    project_id: Optional[int] = Field(None, description="ID проекту (якщо оновлення)")
    source_id: Optional[int] = Field(None, description="ID джерела (якщо оновлення)")
    parameters: List[FormParameterInput] = Field(..., description="Список параметрів", min_items=1, max_items=5)
    
    @validator('parameters')
    def check_param_count(cls, v):
        if len(v) > 5:
            raise ValueError("Форма підтримує максимум 5 параметрів. Використайте CSV для більшої кількості.")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": None,
                "source_id": None,
                "parameters": [
                    {
                        "param_name": "rated_power_mw",
                        "param_value": 2.5,
                        "param_unit": "MW",
                        "param_type": "numeric"
                    }
                ]
            }
        }


# ============================================================================
# CSV IMPORT SCHEMAS (6-20 параметрів)
# ============================================================================

class CSVImportRequest(BaseModel):
    """Запит на імпорт з CSV"""
    project_id: Optional[int] = Field(None, description="ID проекту")
    source_id: Optional[int] = Field(None, description="ID джерела")
    file_path: str = Field(..., description="Шлях до CSV файлу", min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": None,
                "source_id": None,
                "file_path": "/path/to/parameters.csv"
            }
        }


# ============================================================================
# JSON IMPORT SCHEMAS (20+ параметрів)
# ============================================================================

class JSONParameterInput(BaseModel):
    """Параметр у JSON форматі"""
    value: Any = Field(..., description="Значення параметра")
    unit: Optional[str] = Field(None, description="Одиниця виміру")
    type: ParameterTypeEnum = Field(default=ParameterTypeEnum.NUMERIC, description="Тип параметра")


class JSONEnergySourceInput(BaseModel):
    """Джерело енергії у JSON форматі"""
    name: str = Field(..., description="Назва джерела", min_length=1)
    type: SourceTypeEnum = Field(..., description="Тип джерела")
    category: SourceCategoryEnum = Field(..., description="Категорія джерела")
    parameters: Dict[str, Any] = Field(..., description="Параметри джерела")
    description: Optional[str] = Field(None, description="Опис джерела")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Solar PV",
                "type": "PV",
                "category": "generation",
                "parameters": {
                    "rated_power_mw": {"value": 2.5, "unit": "MW"},
                    "efficiency_percent": {"value": 85, "unit": "%"}
                }
            }
        }


class JSONProjectInput(BaseModel):
    """Проект у JSON форматі"""
    name: str = Field(..., description="Назва проекту", min_length=1)
    location: str = Field(..., description="Локація проекту", min_length=1)
    timezone: Optional[str] = Field(default="Europe/Kyiv", description="Часова зона")
    energy_sources: List[JSONEnergySourceInput] = Field(..., description="Список джерел енергії", min_items=1)
    description: Optional[str] = Field(None, description="Опис проекту")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Chervonohrad Energy System",
                "location": "Chervonohrad, Ukraine",
                "timezone": "Europe/Kyiv",
                "energy_sources": [
                    {
                        "name": "Solar PV",
                        "type": "PV",
                        "category": "generation",
                        "parameters": {
                            "rated_power_mw": {"value": 2.5, "unit": "MW"}
                        }
                    }
                ]
            }
        }


class JSONImportRequest(BaseModel):
    """Запит на імпорт з JSON"""
    file_path: str = Field(..., description="Шлях до JSON файлу", min_length=1)
    project_id: Optional[int] = Field(None, description="ID проекту (якщо оновлення)")
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "/path/to/project.json",
                "project_id": None
            }
        }


# ============================================================================
# VALIDATION RESPONSE SCHEMAS
# ============================================================================

class ValidationErrorResponse(BaseModel):
    """Помилка валідації"""
    field: str
    message: str
    value: Optional[str] = None
    row: Optional[int] = None
    severity: str


class ValidationResultResponse(BaseModel):
    """Результат валідації"""
    is_valid: bool
    message: str
    errors: List[ValidationErrorResponse] = []
    warnings: List[ValidationErrorResponse] = []
    data_count: int = 0
    total_issues: int = 0


# ============================================================================
# IMPORT RESPONSE SCHEMAS
# ============================================================================

class ImportSuccessResponse(BaseModel):
    """Успішний результат імпорту"""
    success: True
    message: str
    project_id: int
    source_id: Optional[int] = None
    parameters_imported: int
    data: Dict[str, Any] = {}
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Параметри успішно імпортовані",
                "project_id": 1,
                "source_id": 2,
                "parameters_imported": 5,
                "data": {}
            }
        }


class ImportErrorResponse(BaseModel):
    """Помилка при імпорті"""
    success: False
    message: str
    errors: List[ValidationErrorResponse] = []
    validation_result: Optional[ValidationResultResponse] = None


class ImportResponse(BaseModel):
    """Універсальний результат імпорту"""
    success: bool
    message: str
    project_id: Optional[int] = None
    source_id: Optional[int] = None
    parameters_imported: int = 0
    validation_errors: List[ValidationErrorResponse] = []
    validation_warnings: List[ValidationErrorResponse] = []


# ============================================================================
# TEMPLATE RESPONSE SCHEMAS
# ============================================================================

class TemplateResponse(BaseModel):
    """Шаблон для завантаження"""
    format: str = Field(..., description="Формат (csv, json)")
    filename: str = Field(..., description="Рекомендована назва файлу")
    description: str = Field(..., description="Опис шаблону")
    content: str = Field(..., description="Вміст шаблону")
    mime_type: str = Field(..., description="MIME тип")


# ============================================================================
# HEALTH CHECK
# ============================================================================

class HealthResponse(BaseModel):
    """Відповідь перевірки здоров'я API"""
    status: str = "healthy"
    version: str = "1.0.0"
    validators: Dict[str, bool] = {
        "form": True,
        "csv": True,
        "json": True
    }
