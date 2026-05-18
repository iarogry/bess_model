"""
Import handlers for Form, CSV, and JSON imports
Обработчики интеграции валидаторов с БД
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

from importers.validators import FormValidator, CSVValidator, JSONValidator
from models.energy_system_db import EnergySystemDB, EnergySource, SourceParameter
from schemas import (
    FormImportRequest, CSVImportRequest, JSONImportRequest,
    ImportResponse, ValidationErrorResponse
)

logger = logging.getLogger(__name__)


class ImportHandler:
    """Базовый класс для обработки импорта"""
    
    def __init__(self, db_path: str = "data.db"):
        self.db = EnergySystemDB(db_path)
    
    def _format_error_response(self, validation_result) -> Tuple[bool, List[ValidationErrorResponse]]:
        """Преобразовать ошибки валидации в API формат"""
        errors = []
        
        for error in validation_result.errors:
            errors.append(ValidationErrorResponse(
                field=error.field,
                message=error.message,
                value=error.value,
                row=error.row,
                severity="error"
            ))
        
        for warning in validation_result.warnings:
            errors.append(ValidationErrorResponse(
                field=warning.field,
                message=warning.message,
                value=warning.value,
                row=warning.row,
                severity="warning"
            ))
        
        return validation_result.is_valid, errors


class FormImportHandler(ImportHandler):
    """Обработчик импорта из форм (1-5 параметров)"""
    
    def handle(self, request: FormImportRequest) -> ImportResponse:
        """
        Обработать импорт из формы
        
        Args:
            request: FormImportRequest с параметрами
            
        Returns:
            ImportResponse с результатом
        """
        
        try:
            # Конвертировать Pydantic модель в dict для валидатора
            form_data = {
                "parameters": [
                    {
                        "param_name": param.param_name,
                        "param_value": param.param_value,
                        "param_unit": param.param_unit,
                        "param_type": param.param_type.value
                    }
                    for param in request.parameters
                ]
            }
            
            # Валидировать
            validation_result = FormValidator.validate(form_data)
            
            if not validation_result.is_valid:
                _, errors = self._format_error_response(validation_result)
                return ImportResponse(
                    success=False,
                    message=validation_result.message,
                    validation_errors=errors
                )
            
            # Сохранить в БД
            project_id = request.project_id
            source_id = request.source_id
            
            # Если нет project_id, создать новый проект
            if not project_id:
                project = self.db.create_project(
                    name=f"Project {datetime.now().isoformat()}",
                    location="TBD",
                    timezone="Europe/Kyiv"
                )
                project_id = project['id']
            
            # Если нет source_id, создать новый источник
            if not source_id:
                source = self.db.create_energy_source(
                    project_id=project_id,
                    name=f"Source {datetime.now().isoformat()}",
                    type="Unknown",
                    category="generation"
                )
                source_id = source['id']
            
            # Сохранить параметры
            for param in request.parameters:
                self.db.create_parameter(
                    source_id=source_id,
                    param_name=param.param_name,
                    param_value=param.param_value,
                    param_unit=param.param_unit,
                    param_type=param.param_type.value,
                    editable=True
                )
            
            return ImportResponse(
                success=True,
                message=f"Форма успешно импортирована ({len(request.parameters)} параметров)",
                project_id=project_id,
                source_id=source_id,
                parameters_imported=len(request.parameters)
            )
        
        except Exception as e:
            logger.error(f"Form import error: {str(e)}")
            return ImportResponse(
                success=False,
                message=f"Ошибка импорта: {str(e)}"
            )


class CSVImportHandler(ImportHandler):
    """Обработчик импорта из CSV (6-20 параметров)"""
    
    def handle(self, request: CSVImportRequest) -> ImportResponse:
        """
        Обработать импорт из CSV
        
        Args:
            request: CSVImportRequest с путем к файлу
            
        Returns:
            ImportResponse с результатом
        """
        
        try:
            # Проверить существование файла
            csv_path = Path(request.file_path)
            if not csv_path.exists():
                return ImportResponse(
                    success=False,
                    message=f"CSV файл не найден: {request.file_path}"
                )
            
            # Валидировать
            validation_result = CSVValidator.validate(str(csv_path))
            
            if not validation_result.is_valid:
                _, errors = self._format_error_response(validation_result)
                return ImportResponse(
                    success=False,
                    message=validation_result.message,
                    validation_errors=errors
                )
            
            # Сохранить в БД
            project_id = request.project_id
            source_id = request.source_id
            
            # Если нет project_id, создать новый проект
            if not project_id:
                project = self.db.create_project(
                    name=csv_path.stem,
                    location="TBD",
                    timezone="Europe/Kyiv"
                )
                project_id = project['id']
            
            # Если нет source_id, создать новый источник
            if not source_id:
                source = self.db.create_energy_source(
                    project_id=project_id,
                    name=f"CSV Import {datetime.now().isoformat()}",
                    type="Unknown",
                    category="generation"
                )
                source_id = source['id']
            
            # Прочитать CSV и сохранить параметры
            import csv
            params_count = 0
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    param_name = row.get('Parameter Name', '').strip()
                    value = row.get('Value', '').strip()
                    unit = row.get('Unit', '').strip()
                    param_type = row.get('Type', 'numeric').strip()
                    editable = row.get('Editable', 'TRUE').upper() == 'TRUE'
                    
                    if param_name and value:
                        try:
                            self.db.create_parameter(
                                source_id=source_id,
                                param_name=param_name,
                                param_value=float(value),
                                param_unit=unit,
                                param_type=param_type,
                                editable=editable
                            )
                            params_count += 1
                        except Exception as e:
                            logger.warning(f"Параметр {param_name} не сохранен: {str(e)}")
            
            return ImportResponse(
                success=True,
                message=f"CSV успешно импортирован ({params_count} параметров)",
                project_id=project_id,
                source_id=source_id,
                parameters_imported=params_count
            )
        
        except Exception as e:
            logger.error(f"CSV import error: {str(e)}")
            return ImportResponse(
                success=False,
                message=f"Ошибка импорта CSV: {str(e)}"
            )


class JSONImportHandler(ImportHandler):
    """Обработчик импорта из JSON (20+ параметров)"""
    
    def handle(self, request: JSONImportRequest) -> ImportResponse:
        """
        Обработать импорт из JSON
        
        Args:
            request: JSONImportRequest с путем к файлу
            
        Returns:
            ImportResponse с результатом
        """
        
        try:
            # Проверить существование файла
            json_path = Path(request.file_path)
            if not json_path.exists():
                return ImportResponse(
                    success=False,
                    message=f"JSON файл не найден: {request.file_path}"
                )
            
            # Валидировать
            validation_result = JSONValidator.validate(str(json_path))
            
            if not validation_result.is_valid:
                _, errors = self._format_error_response(validation_result)
                return ImportResponse(
                    success=False,
                    message=validation_result.message,
                    validation_errors=errors
                )
            
            # Прочитать JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            project_data = data.get('project', {})
            
            # Получить или создать проект
            project_id = request.project_id
            if not project_id:
                project = self.db.create_project(
                    name=project_data.get('name', json_path.stem),
                    location=project_data.get('location', 'TBD'),
                    timezone=project_data.get('timezone', 'Europe/Kyiv')
                )
                project_id = project['id']
            
            # Обработать источники энергии
            total_params = 0
            energy_sources = project_data.get('energy_sources', [])
            
            for source_data in energy_sources:
                # Создать источник
                source = self.db.create_energy_source(
                    project_id=project_id,
                    name=source_data.get('name', f'Source {datetime.now().isoformat()}'),
                    type=source_data.get('type', 'Unknown'),
                    category=source_data.get('category', 'generation')
                )
                source_id = source['id']
                
                # Сохранить параметры
                parameters = source_data.get('parameters', {})
                
                for param_name, param_data in parameters.items():
                    try:
                        # Поддерживать оба формата: простой (значение) и сложный (объект)
                        if isinstance(param_data, dict):
                            param_value = param_data.get('value')
                            param_unit = param_data.get('unit', '')
                            param_type = param_data.get('type', 'numeric')
                        else:
                            param_value = param_data
                            param_unit = ''
                            param_type = 'numeric'
                        
                        if param_value is not None:
                            self.db.create_parameter(
                                source_id=source_id,
                                param_name=param_name,
                                param_value=float(param_value),
                                param_unit=param_unit,
                                param_type=param_type,
                                editable=True
                            )
                            total_params += 1
                    except Exception as e:
                        logger.warning(f"Параметр {param_name} не сохранен: {str(e)}")
            
            return ImportResponse(
                success=True,
                message=f"JSON успешно импортирован ({total_params} параметров, {len(energy_sources)} источников)",
                project_id=project_id,
                parameters_imported=total_params
            )
        
        except Exception as e:
            logger.error(f"JSON import error: {str(e)}")
            return ImportResponse(
                success=False,
                message=f"Ошибка импорта JSON: {str(e)}"
            )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_handler(format_type: str, db_path: str = "data.db") -> ImportHandler:
    """
    Получить обработчик для конкретного формата
    
    Args:
        format_type: "form", "csv", или "json"
        db_path: Путь к БД
        
    Returns:
        Подходящий обработчик импорта
    """
    
    handlers = {
        'form': FormImportHandler,
        'csv': CSVImportHandler,
        'json': JSONImportHandler
    }
    
    handler_class = handlers.get(format_type.lower())
    if not handler_class:
        raise ValueError(f"Неизвестный формат: {format_type}")
    
    return handler_class(db_path)
