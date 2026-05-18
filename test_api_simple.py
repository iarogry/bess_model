#!/usr/bin/env python3
"""
Простой тест API без pytest
Проверяет основные функции валидаторов и обработчиков
"""

import sys
import json
from pathlib import Path

# Добавить src в path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from importers.validators import FormValidator, CSVValidator, JSONValidator
from models.energy_system_db import EnergySystemDB

def test_form_validator():
    """Тест FormValidator"""
    print("\n" + "="*80)
    print("📝 TEST 1: FORM VALIDATOR")
    print("="*80)
    
    form_data = {
        "parameters": [
            {"param_name": "rated_power_mw", "param_value": 2.5, "param_unit": "MW"},
            {"param_name": "efficiency_percent", "param_value": 85, "param_unit": "%"},
            {"param_name": "capacity_mwh", "param_value": 10, "param_unit": "MWh"}
        ]
    }
    
    result = FormValidator.validate(form_data)
    print(f"✅ Valid: {result.is_valid}")
    print(f"📌 Message: {result.message}")
    print(f"📊 Data Count: {result.data_count}")
    
    if result.errors:
        print(f"❌ Errors: {len(result.errors)}")
        for err in result.errors:
            print(f"   - {err.field}: {err.message}")
    
    return result.is_valid

def test_csv_validator():
    """Тест CSVValidator"""
    print("\n" + "="*80)
    print("📄 TEST 2: CSV VALIDATOR")
    print("="*80)
    
    # Создать тестовый CSV
    csv_content = """Parameter Name,Value,Unit,Type,Description,Editable
rated_power_mw,2.5,MW,numeric,Номінальна потужність ФЕС,TRUE
efficiency_percent,88,%,numeric,Ефективність батареї,TRUE
capacity_mwh,10,MWh,numeric,Ємність батареї,FALSE
charge_power_mw,2.5,MW,numeric,Потужність заряду,TRUE
discharge_power_mw,2.2,MW,numeric,Потужність розряду,TRUE
grid_tariff_uah_mwh,784.2,UAH/MWh,numeric,Тариф сітки,FALSE
"""
    
    csv_path = Path(__file__).parent / "test_params.csv"
    csv_path.write_text(csv_content, encoding='utf-8')
    
    result = CSVValidator.validate(str(csv_path))
    print(f"✅ Valid: {result.is_valid}")
    print(f"📌 Message: {result.message}")
    print(f"📊 Data Count: {result.data_count}")
    
    if result.errors:
        print(f"❌ Errors: {len(result.errors)}")
        for err in result.errors:
            print(f"   - Row {err.row}: {err.field}: {err.message}")
    
    csv_path.unlink()
    return result.is_valid

def test_json_validator():
    """Тест JSONValidator"""
    print("\n" + "="*80)
    print("📋 TEST 3: JSON VALIDATOR")
    print("="*80)
    
    json_data = {
        "project": {
            "name": "Chervonohrad Energy Storage",
            "location": "Chervonohrad, Ukraine",
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
    
    json_path = Path(__file__).parent / "test_project.json"
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
    
    result = JSONValidator.validate(str(json_path))
    print(f"✅ Valid: {result.is_valid}")
    print(f"📌 Message: {result.message}")
    print(f"📊 Data Count: {result.data_count}")
    
    if result.errors:
        print(f"❌ Errors: {len(result.errors)}")
        for err in result.errors:
            print(f"   - {err.field}: {err.message}")
    
    json_path.unlink()
    return result.is_valid

def test_database():
    """Тест базы данных"""
    print("\n" + "="*80)
    print("💾 TEST 4: DATABASE INTEGRATION")
    print("="*80)
    
    try:
        from models.energy_system_db import Project
        
        db_path = Path(__file__).parent / "test_energy_system.db"
        db = EnergySystemDB(str(db_path))
        
        # Создать проект как объект
        project = Project(
            name="Test Project",
            location="Kyiv",
            timezone="Europe/Kyiv",
            currency="UAH",
            year=2026
        )
        
        project_id = db.create_project(project)
        print(f"✅ Project created: {project.name} (ID: {project_id})")
        
        # Получить проект
        fetched = db.get_project(project_id)
        print(f"✅ Project fetched: {fetched.name if fetched else 'Not found'}")
        
        # Очистить
        db_path.unlink(missing_ok=True)
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Запустить все тесты"""
    print("\n" + "="*80)
    print("🧪 BATTERY SIMULATOR - API TESTS")
    print("="*80)
    
    results = {
        "Form Validator": test_form_validator(),
        "CSV Validator": test_csv_validator(),
        "JSON Validator": test_json_validator(),
        "Database": test_database(),
    }
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✨ Все тесты пройдены успешно!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} тестов не пройдены")
        return 1

if __name__ == '__main__':
    sys.exit(main())
