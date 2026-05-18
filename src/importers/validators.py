#!/usr/bin/env python3
"""
Data Validators for Form, CSV, and JSON imports
Валідація параметрів перед імпортом в БД
"""

import csv
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class ParameterType(str, Enum):
    """Типи параметрів"""
    NUMERIC = "numeric"
    CONSTRAINT = "constraint"
    COST = "cost"
    TIME = "time"
    DATE = "date"


class SourceType(str, Enum):
    """Типи джерел енергії"""
    PV = "PV"
    BESS = "BESS"
    CHP = "CHP"
    GRID = "Grid"
    WIND = "Wind"
    HYDRO = "Hydro"


class SourceCategory(str, Enum):
    """Категорії джерел"""
    GENERATION = "generation"
    STORAGE = "storage"
    DEMAND = "demand"


# ============================================================================
# VALIDATION RESULTS
# ============================================================================

@dataclass
class ValidationError:
    """Помилка валідації"""
    field: str
    message: str
    value: Any = None
    row: int = None
    severity: str = "error"  # "error", "warning"
    
    def to_dict(self):
        return {
            'field': self.field,
            'message': self.message,
            'value': str(self.value) if self.value is not None else None,
            'row': self.row,
            'severity': self.severity
        }


@dataclass
class ValidationResult:
    """Результат валідації"""
    is_valid: bool
    message: str
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    data_count: int = 0
    
    def to_dict(self):
        return {
            'is_valid': self.is_valid,
            'message': self.message,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'data_count': self.data_count,
            'total_issues': len(self.errors) + len(self.warnings)
        }
    
    def add_error(self, field: str, message: str, value: Any = None, row: int = None):
        """Додати помилку"""
        self.errors.append(ValidationError(field, message, value, row, "error"))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, value: Any = None, row: int = None):
        """Додати попередження"""
        self.warnings.append(ValidationError(field, message, value, row, "warning"))


# ============================================================================
# PARAMETER VALIDATOR
# ============================================================================

class ParameterValidator:
    """Валідатор окремих параметрів"""
    
    # Діапазони для числових параметрів
    VALID_RANGES = {
        'power_mw': (0.1, 1000),           # Потужність: 0.1 - 1000 MW
        'capacity_mwh': (0.1, 10000),      # Ємність: 0.1 - 10000 MWh
        'efficiency_percent': (0.1, 100),  # Ефективність: 0.1 - 100%
        'cost': (0, 100000),               # Вартість: 0 - 100,000 UAH/MWh
        'time_hours': (0, 168),            # Час: 0 - 168 годин (тиждень)
        'time_minutes': (0, 1440),         # Час: 0 - 1440 хвилин (день)
    }
    
    @staticmethod
    def validate_parameter(param_name: str, param_value: Any, 
                          param_type: str = "numeric", 
                          param_unit: str = "") -> Tuple[bool, Optional[str]]:
        """
        Валідувати один параметр
        
        Returns: (is_valid, error_message)
        """
        
        # Перевірити тип параметра
        if param_type not in [pt.value for pt in ParameterType]:
            return False, f"Невідомий тип: {param_type}"
        
        # Числові параметри
        if param_type == ParameterType.NUMERIC:
            try:
                value = float(param_value)
                
                # Перевірити діапазон за назвою параметра
                if 'power' in param_name.lower() and 'mw' in param_unit.lower():
                    min_val, max_val = ParameterValidator.VALID_RANGES['power_mw']
                    if not (min_val <= value <= max_val):
                        return False, f"Потужність {value} MW поза діапазоном [{min_val}, {max_val}]"
                
                elif 'capacity' in param_name.lower() and 'mwh' in param_unit.lower():
                    min_val, max_val = ParameterValidator.VALID_RANGES['capacity_mwh']
                    if not (min_val <= value <= max_val):
                        return False, f"Ємність {value} MWh поза діапазоном [{min_val}, {max_val}]"
                
                elif 'efficiency' in param_name.lower() or '%' in param_unit:
                    min_val, max_val = ParameterValidator.VALID_RANGES['efficiency_percent']
                    if not (min_val <= value <= max_val):
                        return False, f"Ефективність {value}% поза діапазоном [{min_val}, {max_val}]"
                
                elif 'cost' in param_name.lower() or 'uah' in param_unit.lower():
                    min_val, max_val = ParameterValidator.VALID_RANGES['cost']
                    if not (min_val <= value <= max_val):
                        return False, f"Вартість {value} поза діапазоном [{min_val}, {max_val}]"
                
                # Базова перевірка: не негативне
                if value < 0:
                    return False, f"Від'ємне значення: {value}"
                
                return True, None
            
            except (ValueError, TypeError):
                return False, f"Не число: {param_value}"
        
        # Обмеження
        elif param_type == ParameterType.CONSTRAINT:
            try:
                value = float(param_value)
                if not (0 <= value <= 100):
                    return False, f"Обмеження {value}% поза діапазоном [0, 100]"
                return True, None
            except (ValueError, TypeError):
                return False, f"Не число: {param_value}"
        
        # Вартість
        elif param_type == ParameterType.COST:
            try:
                value = float(param_value)
                if value < 0:
                    return False, f"Від'ємна вартість: {value}"
                return True, None
            except (ValueError, TypeError):
                return False, f"Не число: {param_value}"
        
        # Час (у хвилинах)
        elif param_type == ParameterType.TIME:
            try:
                value = float(param_value)
                if not (0 <= value <= 1440):
                    return False, f"Час {value} хв поза діапазоном [0, 1440]"
                return True, None
            except (ValueError, TypeError):
                return False, f"Не число: {param_value}"
        
        # Дата
        elif param_type == ParameterType.DATE:
            if isinstance(param_value, str):
                # Простий формат: YYYY-MM-DD
                if re.match(r'^\d{4}-\d{2}-\d{2}$', param_value):
                    return True, None
                return False, f"Неправильний формат дати: {param_value} (очікується YYYY-MM-DD)"
            return True, None
        
        return True, None


# ============================================================================
# FORM VALIDATOR (1-5 параметрів)
# ============================================================================

class FormValidator:
    """Валідатор для веб-форми (JSON)"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> ValidationResult:
        """
        Валідувати дані з форми
        
        Очікуємо формат:
        {
            "parameters": [
                {"param_name": "...", "param_value": 2.5, "param_unit": "MW"}
            ]
        }
        """
        
        result = ValidationResult(is_valid=True, message="")
        
        # Перевірити структуру
        if 'parameters' not in data:
            result.add_error('parameters', "Відсутнє поле 'parameters'")
            result.message = "Невірна структура форми"
            return result
        
        if not isinstance(data['parameters'], list):
            result.add_error('parameters', "Поле 'parameters' має бути масив")
            result.message = "Невірний формат параметрів"
            return result
        
        if len(data['parameters']) == 0:
            result.add_error('parameters', "Масив параметрів порожній")
            result.message = "Не передано параметрів"
            return result
        
        if len(data['parameters']) > 5:
            result.add_warning('parameters', f"Багато параметрів ({len(data['parameters'])}), рекомендується CSV")
        
        # Валідувати кожен параметр
        for idx, param in enumerate(data['parameters']):
            param_idx = f"параметр #{idx + 1}"
            
            # Обов'язкові поля
            if 'param_name' not in param or not param['param_name']:
                result.add_error('param_name', f"{param_idx}: param_name пусто", None, idx + 1)
                continue
            
            if 'param_value' not in param:
                result.add_error('param_value', f"{param_idx}: param_value відсутнє", None, idx + 1)
                continue
            
            param_name = param['param_name']
            param_value = param['param_value']
            param_unit = param.get('param_unit', '')
            param_type = param.get('param_type', 'numeric')
            
            # Валідувати значення
            is_valid, error_msg = ParameterValidator.validate_parameter(
                param_name, param_value, param_type, param_unit
            )
            
            if not is_valid:
                result.add_error(param_name, error_msg, param_value, idx + 1)
            
            result.data_count += 1
        
        if result.errors:
            result.message = f"{len(result.errors)} помилок валідації"
        else:
            result.message = f"Форма валідна ({result.data_count} параметрів)"
        
        return result


# ============================================================================
# CSV VALIDATOR (6-20 параметрів)
# ============================================================================

class CSVValidator:
    """Валідатор для CSV файлів"""
    
    REQUIRED_COLUMNS = {'Parameter Name', 'Value', 'Unit', 'Type'}
    OPTIONAL_COLUMNS = {'Description', 'Editable'}
    
    @staticmethod
    def validate(csv_file: str) -> ValidationResult:
        """Валідувати CSV файл"""
        
        result = ValidationResult(is_valid=True, message="")
        
        # Перевірити існування файлу
        if not Path(csv_file).exists():
            result.add_error('file', f"Файл не знайдено: {csv_file}")
            result.message = "Файл не існує"
            return result
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Перевірити заголовки
                if reader.fieldnames is None:
                    result.add_error('header', "CSV файл порожній")
                    result.message = "Файл не містить даних"
                    return result
                
                fieldnames_set = set(reader.fieldnames)
                
                # Перевірити обов'язкові стовпці
                missing = CSVValidator.REQUIRED_COLUMNS - fieldnames_set
                if missing:
                    result.add_error('columns', f"Відсутні стовпці: {missing}")
                
                # Попередження про невідомі стовпці
                unknown = fieldnames_set - CSVValidator.REQUIRED_COLUMNS - CSVValidator.OPTIONAL_COLUMNS
                if unknown:
                    result.add_warning('columns', f"Невідомі стовпці (будуть ігнороватися): {unknown}")
                
                # Валідувати рядки
                for row_num, row in enumerate(reader, start=2):
                    # Перевірити обов'язкові поля
                    param_name = row.get('Parameter Name', '').strip()
                    value = row.get('Value', '').strip()
                    unit = row.get('Unit', '').strip()
                    param_type = row.get('Type', 'numeric').strip()
                    
                    # Param Name
                    if not param_name:
                        result.add_error('Parameter Name', "Parameter Name пусто", None, row_num)
                        continue
                    
                    # Перевірити від'ємні імена
                    if len(param_name) > 100:
                        result.add_warning('Parameter Name', f"Довге ім'я ({len(param_name)} символів)", param_name, row_num)
                    
                    # Value
                    if not value:
                        result.add_error('Value', "Value пусто", None, row_num)
                        continue
                    
                    # Type
                    if param_type not in [pt.value for pt in ParameterType]:
                        result.add_error('Type', f"Невідомий тип: {param_type}", param_type, row_num)
                    
                    # Валідувати значення
                    is_valid, error_msg = ParameterValidator.validate_parameter(
                        param_name, value, param_type, unit
                    )
                    
                    if not is_valid:
                        result.add_error('Value', error_msg, value, row_num)
                    
                    # Editable
                    if 'Editable' in fieldnames_set:
                        editable = row.get('Editable', 'TRUE').upper()
                        if editable not in ['TRUE', 'FALSE']:
                            result.add_warning('Editable', f"Значення мав бути TRUE/FALSE, отримано: {editable}", editable, row_num)
                    
                    result.data_count += 1
                
                if result.data_count == 0:
                    result.add_error('data', "CSV не містить рядків з даними")
                    result.message = "Файл порожній (крім заголовків)"
                elif result.errors:
                    result.message = f"{len(result.errors)} помилок у {result.data_count} рядках"
                else:
                    result.message = f"CSV валідний ({result.data_count} параметрів)"
        
        except Exception as e:
            result.add_error('file', f"Помилка читання CSV: {str(e)}")
            result.message = f"Помилка обробки файлу: {str(e)}"
        
        return result


# ============================================================================
# JSON VALIDATOR (20+ параметрів)
# ============================================================================

class JSONValidator:
    """Валідатор для JSON файлів"""
    
    REQUIRED_PROJECT_FIELDS = {'name', 'location', 'energy_sources'}
    REQUIRED_SOURCE_FIELDS = {'name', 'type', 'category', 'parameters'}
    
    @staticmethod
    def validate(json_file: str) -> ValidationResult:
        """Валідувати JSON файл"""
        
        result = ValidationResult(is_valid=True, message="")
        
        # Перевірити існування файлу
        if not Path(json_file).exists():
            result.add_error('file', f"Файл не знайдено: {json_file}")
            result.message = "Файл не існує"
            return result
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        except json.JSONDecodeError as e:
            result.add_error('json', f"Помилка парсингу JSON: {str(e)}")
            result.message = f"Невірний JSON: {str(e)}"
            return result
        
        except Exception as e:
            result.add_error('file', f"Помилка читання файлу: {str(e)}")
            result.message = f"Помилка обробки: {str(e)}"
            return result
        
        # Перевірити структуру
        if 'project' not in data:
            result.add_error('project', "Поле 'project' відсутнє")
            result.message = "Невірна структура JSON"
            return result
        
        project = data.get('project', {})
        
        # Перевірити обов'язкові поля проекту
        missing_fields = JSONValidator.REQUIRED_PROJECT_FIELDS - set(project.keys())
        if missing_fields:
            result.add_error('project', f"Відсутні поля: {missing_fields}")
        
        # Перевірити джерела
        sources = project.get('energy_sources', [])
        if not sources:
            result.add_error('energy_sources', "Список energy_sources порожній")
            result.message = "Проект не містить джерел енергії"
            return result
        
        if len(sources) > 20:
            result.add_warning('energy_sources', f"Багато джерел ({len(sources)}), це може бути повільним")
        
        for src_idx, source in enumerate(sources):
            src_name = source.get('name', f'source_{src_idx}')
            
            # Перевірити обов'язкові поля джерела
            missing_src_fields = JSONValidator.REQUIRED_SOURCE_FIELDS - set(source.keys())
            if missing_src_fields:
                result.add_error('source', f"{src_name}: відсутні поля {missing_src_fields}", None, src_idx + 1)
                continue
            
            # Перевірити тип джерела
            source_type = source.get('type', '')
            if source_type not in [st.value for st in SourceType]:
                result.add_warning('type', f"{src_name}: невідомий тип {source_type}", source_type, src_idx + 1)
            
            # Перевірити категорію
            category = source.get('category', '')
            if category not in [sc.value for sc in SourceCategory]:
                result.add_warning('category', f"{src_name}: невідома категорія {category}", category, src_idx + 1)
            
            # Валідувати параметри джерела
            parameters = source.get('parameters', {})
            if not parameters:
                result.add_warning('parameters', f"{src_name}: немає параметрів", None, src_idx + 1)
            
            for param_name, param_data in parameters.items():
                if isinstance(param_data, dict):
                    param_value = param_data.get('value')
                    param_unit = param_data.get('unit', '')
                    param_type = param_data.get('type', 'numeric')
                else:
                    # Простий формат: тільки значення
                    param_value = param_data
                    param_unit = ''
                    param_type = 'numeric'
                
                # Валідувати значення
                is_valid, error_msg = ParameterValidator.validate_parameter(
                    param_name, param_value, param_type, param_unit
                )
                
                if not is_valid:
                    result.add_error(param_name, f"{src_name}: {error_msg}", param_value, src_idx + 1)
                
                result.data_count += 1
        
        if result.errors:
            result.message = f"{len(result.errors)} помилок у {len(sources)} джерелах"
        else:
            result.message = f"JSON валідний ({len(sources)} джерел, {result.data_count} параметрів)"
        
        return result


# ============================================================================
# MAIN - ТЕСТУВАННЯ
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("✅ DATA VALIDATORS - TEST")
    print("="*80)
    
    # Тест 1: Form Validator
    print("\n📝 TEST 1: FORM VALIDATOR")
    print("-" * 80)
    
    form_data = {
        "parameters": [
            {"param_name": "rated_power_mw", "param_value": 2.5, "param_unit": "MW"},
            {"param_name": "efficiency_percent", "param_value": 85, "param_unit": "%"}
        ]
    }
    
    form_result = FormValidator.validate(form_data)
    print(f"Valid: {form_result.is_valid}")
    print(f"Message: {form_result.message}")
    print(f"Data Count: {form_result.data_count}")
    
    # Тест 2: CSV Validator
    print("\n📄 TEST 2: CSV VALIDATOR")
    print("-" * 80)
    
    # Створити тестовий CSV
    csv_content = """Parameter Name,Value,Unit,Type,Description,Editable
rated_power_mw,2.5,MW,numeric,Номінальна потужність ФЕС,TRUE
efficiency_percent,85,%,numeric,Ефективність модулів,TRUE
capacity_factor_annual_percent,18,%,numeric,Річний коефіцієнт використання,FALSE
"""
    
    with open("test_params.csv", "w", encoding='utf-8') as f:
        f.write(csv_content)
    
    csv_result = CSVValidator.validate("test_params.csv")
    print(f"Valid: {csv_result.is_valid}")
    print(f"Message: {csv_result.message}")
    print(f"Data Count: {csv_result.data_count}")
    
    # Тест 3: JSON Validator
    print("\n📋 TEST 3: JSON VALIDATOR")
    print("-" * 80)
    
    json_data = {
        "project": {
            "name": "Test Project",
            "location": "Kyiv",
            "energy_sources": [
                {
                    "name": "Solar",
                    "type": "PV",
                    "category": "generation",
                    "parameters": {
                        "rated_power_mw": {"value": 2.5, "unit": "MW"}
                    }
                }
            ]
        }
    }
    
    with open("test_project.json", "w", encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    json_result = JSONValidator.validate("test_project.json")
    print(f"Valid: {json_result.is_valid}")
    print(f"Message: {json_result.message}")
    print(f"Data Count: {json_result.data_count}")
    
    print("\n" + "="*80 + "\n")

