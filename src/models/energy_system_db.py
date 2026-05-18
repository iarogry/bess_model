#!/usr/bin/env python3
"""
Energy System Database Models & ORM
Структура для управління параметрами всіх джерел генерації та зберігання
"""

import sqlite3
import json
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS (Dataclasses)
# ============================================================================

@dataclass
class SourceParameter:
    """Параметр джерела енергії"""
    param_id: Optional[int] = None
    source_id: int = None
    param_name: str = ""
    param_value: float = 0.0
    param_unit: str = ""
    param_type: str = "numeric"  # 'numeric', 'constraint', 'cost', 'time'
    description: str = ""
    is_editable: bool = True
    created_date: Optional[str] = None
    
    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class EnergySource:
    """Джерело енергії (ФЕС, батарея, CHP, мережа)"""
    source_id: Optional[int] = None
    project_id: int = None
    name: str = ""
    source_type: str = ""  # 'PV', 'CHP', 'BESS', 'Grid', 'Wind', 'Hydro'
    category: str = ""  # 'generation', 'storage', 'demand'
    description: str = ""
    is_active: bool = True
    parameters: List[SourceParameter] = field(default_factory=list)
    created_date: Optional[str] = None
    
    def to_dict(self):
        return {
            'source_id': self.source_id,
            'project_id': self.project_id,
            'name': self.name,
            'source_type': self.source_type,
            'category': self.category,
            'description': self.description,
            'is_active': self.is_active,
            'parameters': {p.param_name: p.param_value for p in self.parameters}
        }


@dataclass
class Project:
    """Енергетичний проект"""
    project_id: Optional[int] = None
    name: str = ""
    location: str = ""
    timezone: str = "Europe/Kyiv"
    description: str = ""
    currency: str = "UAH"
    year: int = 2026
    energy_sources: List[EnergySource] = field(default_factory=list)
    created_date: Optional[str] = None
    updated_date: Optional[str] = None
    
    def to_dict(self):
        return {
            'project_id': self.project_id,
            'name': self.name,
            'location': self.location,
            'timezone': self.timezone,
            'currency': self.currency,
            'year': self.year,
            'energy_sources': [s.to_dict() for s in self.energy_sources]
        }


@dataclass
class HourlyData:
    """Почасові дані операцій"""
    data_id: Optional[int] = None
    project_id: int = None
    hour_index: int = 0
    datetime: str = ""
    pv_generation_kwh: float = 0.0
    wind_generation_kwh: float = 0.0
    hydro_generation_kwh: float = 0.0
    chp_availability: bool = True
    grid_price_rdn_uah_per_mwh: float = 0.0
    grid_price_balancing_uah_per_mwh: float = 0.0
    demand_load_kwh: float = 0.0
    grid_frequency_hz: float = 50.0


# ============================================================================
# DATABASE CLASS
# ============================================================================

class EnergySystemDB:
    """Головна база даних для енергетичної системи"""
    
    def __init__(self, db_path: str = "data/energy_system.db"):
        """Ініціалізація БД"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_schema()
        logger.info(f"Initialized database at {self.db_path}")
    
    def _init_schema(self):
        """Ініціалізувати схему БД"""
        
        # Таблиця проектів
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                timezone TEXT DEFAULT 'Europe/Kyiv',
                description TEXT,
                currency TEXT DEFAULT 'UAH',
                year INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблиця типів джерел
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_types (
                type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # Таблиця джерел енергії
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS energy_sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                UNIQUE(project_id, name)
            )
        """)
        
        # Таблиця параметрів джерел
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_parameters (
                param_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                param_name TEXT NOT NULL,
                param_value REAL NOT NULL,
                param_unit TEXT,
                param_type TEXT DEFAULT 'numeric',
                description TEXT,
                is_editable BOOLEAN DEFAULT 1,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES energy_sources(source_id),
                UNIQUE(source_id, param_name)
            )
        """)
        
        # Таблиця почасових даних
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS operational_data (
                data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                hour_index INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                pv_generation_kwh REAL DEFAULT 0,
                wind_generation_kwh REAL DEFAULT 0,
                hydro_generation_kwh REAL DEFAULT 0,
                chp_availability BOOLEAN DEFAULT 1,
                grid_price_rdn_uah_per_mwh REAL DEFAULT 0,
                grid_price_balancing_uah_per_mwh REAL DEFAULT 0,
                demand_load_kwh REAL DEFAULT 0,
                grid_frequency_hz REAL DEFAULT 50.0,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                UNIQUE(project_id, hour_index)
            )
        """)
        
        # Таблиця результатів оптимізації
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                optimization_date TIMESTAMP,
                day INTEGER,
                shift INTEGER,
                hour_index INTEGER,
                source_id INTEGER,
                action TEXT,
                energy_kwh REAL,
                revenue_uah REAL,
                cost_uah REAL,
                soc_kwh REAL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id),
                FOREIGN KEY(source_id) REFERENCES energy_sources(source_id)
            )
        """)
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    # ========================================================================
    # PROJECT OPERATIONS
    # ========================================================================
    
    def create_project(self, project: Project) -> int:
        """Створити новий проект"""
        self.cursor.execute("""
            INSERT INTO projects (name, location, timezone, description, currency, year)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project.name, project.location, project.timezone, 
              project.description, project.currency, project.year))
        
        self.conn.commit()
        project_id = self.cursor.lastrowid
        logger.info(f"Created project: {project.name} (ID: {project_id})")
        return project_id
    
    def get_project(self, project_id: int) -> Project:
        """Отримати проект з усіма джерелами"""
        self.cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        project = Project(
            project_id=row['project_id'],
            name=row['name'],
            location=row['location'],
            timezone=row['timezone'],
            description=row['description'],
            currency=row['currency'],
            year=row['year'],
            created_date=row['created_date'],
            updated_date=row['updated_date']
        )
        
        # Завантажити джерела
        project.energy_sources = self.get_energy_sources(project_id)
        return project
    
    # ========================================================================
    # ENERGY SOURCE OPERATIONS
    # ========================================================================
    
    def create_energy_source(self, source: EnergySource) -> int:
        """Створити нове джерело енергії"""
        self.cursor.execute("""
            INSERT INTO energy_sources 
            (project_id, name, source_type, category, description, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source.project_id, source.name, source.source_type, 
              source.category, source.description, source.is_active))
        
        self.conn.commit()
        source_id = self.cursor.lastrowid
        logger.info(f"Created energy source: {source.name} (ID: {source_id})")
        
        # Додати параметри
        for param in source.parameters:
            param.source_id = source_id
            self.create_parameter(param)
        
        return source_id
    
    def get_energy_sources(self, project_id: int) -> List[EnergySource]:
        """Отримати всі джерела проекту"""
        self.cursor.execute(
            "SELECT * FROM energy_sources WHERE project_id = ?", 
            (project_id,)
        )
        
        sources = []
        for row in self.cursor.fetchall():
            source = EnergySource(
                source_id=row['source_id'],
                project_id=row['project_id'],
                name=row['name'],
                source_type=row['source_type'],
                category=row['category'],
                description=row['description'],
                is_active=bool(row['is_active']),
                created_date=row['created_date']
            )
            
            # Завантажити параметри
            source.parameters = self.get_parameters(row['source_id'])
            sources.append(source)
        
        return sources
    
    # ========================================================================
    # PARAMETER OPERATIONS
    # ========================================================================
    
    def create_parameter(self, param: SourceParameter) -> int:
        """Додати параметр до джерела"""
        self.cursor.execute("""
            INSERT INTO source_parameters 
            (source_id, param_name, param_value, param_unit, param_type, description, is_editable)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (param.source_id, param.param_name, param.param_value, 
              param.param_unit, param.param_type, param.description, param.is_editable))
        
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_parameters(self, source_id: int) -> List[SourceParameter]:
        """Отримати всі параметри джерела"""
        self.cursor.execute(
            "SELECT * FROM source_parameters WHERE source_id = ?",
            (source_id,)
        )
        
        params = []
        for row in self.cursor.fetchall():
            param = SourceParameter(
                param_id=row['param_id'],
                source_id=row['source_id'],
                param_name=row['param_name'],
                param_value=row['param_value'],
                param_unit=row['param_unit'],
                param_type=row['param_type'],
                description=row['description'],
                is_editable=bool(row['is_editable']),
                created_date=row['created_date']
            )
            params.append(param)
        
        return params
    
    def update_parameter(self, param_id: int, new_value: float):
        """Оновити значення параметра"""
        self.cursor.execute(
            "UPDATE source_parameters SET param_value = ? WHERE param_id = ?",
            (new_value, param_id)
        )
        self.conn.commit()
        logger.info(f"Updated parameter ID {param_id} to {new_value}")
    
    # ========================================================================
    # OPERATIONAL DATA OPERATIONS
    # ========================================================================
    
    def insert_hourly_data(self, project_id: int, hourly_list: List[HourlyData]):
        """Вставити почасові дані"""
        for data in hourly_list:
            self.cursor.execute("""
                INSERT OR REPLACE INTO operational_data 
                (project_id, hour_index, datetime, pv_generation_kwh, 
                 wind_generation_kwh, hydro_generation_kwh, chp_availability,
                 grid_price_rdn_uah_per_mwh, grid_price_balancing_uah_per_mwh,
                 demand_load_kwh, grid_frequency_hz)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, data.hour_index, data.datetime, 
                  data.pv_generation_kwh, data.wind_generation_kwh,
                  data.hydro_generation_kwh, data.chp_availability,
                  data.grid_price_rdn_uah_per_mwh,
                  data.grid_price_balancing_uah_per_mwh,
                  data.demand_load_kwh, data.grid_frequency_hz))
        
        self.conn.commit()
        logger.info(f"Inserted {len(hourly_list)} hourly records")
    
    def get_hourly_data(self, project_id: int, start_hour: int = 0, 
                       end_hour: int = 8760) -> List[HourlyData]:
        """Отримати почасові дані діапазону"""
        self.cursor.execute("""
            SELECT * FROM operational_data 
            WHERE project_id = ? AND hour_index >= ? AND hour_index < ?
            ORDER BY hour_index
        """, (project_id, start_hour, end_hour))
        
        data_list = []
        for row in self.cursor.fetchall():
            data = HourlyData(
                data_id=row['data_id'],
                project_id=row['project_id'],
                hour_index=row['hour_index'],
                datetime=row['datetime'],
                pv_generation_kwh=row['pv_generation_kwh'],
                wind_generation_kwh=row['wind_generation_kwh'],
                hydro_generation_kwh=row['hydro_generation_kwh'],
                chp_availability=bool(row['chp_availability']),
                grid_price_rdn_uah_per_mwh=row['grid_price_rdn_uah_per_mwh'],
                grid_price_balancing_uah_per_mwh=row['grid_price_balancing_uah_per_mwh'],
                demand_load_kwh=row['demand_load_kwh'],
                grid_frequency_hz=row['grid_frequency_hz']
            )
            data_list.append(data)
        
        return data_list
    
    # ========================================================================
    # JSON IMPORT/EXPORT
    # ========================================================================
    
    def load_project_from_json(self, json_file: str) -> Project:
        """Завантажити проект з JSON файлу"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        project_data = data['project']
        
        # Створити проект
        project = Project(
            name=project_data['name'],
            location=project_data.get('location', ''),
            timezone=project_data.get('timezone', 'Europe/Kyiv'),
            description=project_data.get('description', ''),
            currency=project_data.get('currency', 'UAH'),
            year=project_data.get('year', 2026)
        )
        
        project_id = self.create_project(project)
        project.project_id = project_id
        
        # Додати джерела
        for src_data in project_data.get('energy_sources', []):
            source = EnergySource(
                project_id=project_id,
                name=src_data['name'],
                source_type=src_data['type'],
                category=src_data.get('category', 'generation'),
                description=src_data.get('description', '')
            )
            
            # Додати параметри
            for param_name, param_value in src_data.get('parameters', {}).items():
                param = SourceParameter(
                    param_name=param_name,
                    param_value=float(param_value) if isinstance(param_value, (int, float)) else param_value,
                    param_type='numeric'
                )
                source.parameters.append(param)
            
            source_id = self.create_energy_source(source)
            source.source_id = source_id
            project.energy_sources.append(source)
        
        logger.info(f"Loaded project from {json_file}")
        return project
    
    def load_hourly_data_from_json(self, json_file: str, project_id: int):
        """Завантажити почасові дані з JSON"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        hourly_list = []
        for hour_data in data['hourly_data']:
            h_data = HourlyData(
                project_id=project_id,
                hour_index=hour_data['hour_index'],
                datetime=hour_data['datetime'],
                pv_generation_kwh=hour_data.get('pv_generation_kwh', 0),
                wind_generation_kwh=hour_data.get('wind_generation_kwh', 0),
                hydro_generation_kwh=hour_data.get('hydro_generation_kwh', 0),
                chp_availability=hour_data.get('chp_availability', True),
                grid_price_rdn_uah_per_mwh=hour_data.get('grid_price_rdn_uah_per_mwh', 0),
                grid_price_balancing_uah_per_mwh=hour_data.get('grid_price_balancing_uah_per_mwh', 0),
                demand_load_kwh=hour_data.get('demand_load_kwh', 0),
                grid_frequency_hz=hour_data.get('grid_frequency_hz', 50.0)
            )
            hourly_list.append(h_data)
        
        self.insert_hourly_data(project_id, hourly_list)
        logger.info(f"Loaded {len(hourly_list)} hourly records from {json_file}")
    
    def export_project_to_json(self, project_id: int, output_file: str):
        """Експортувати проект в JSON"""
        project = self.get_project(project_id)
        
        project_dict = {
            'project': {
                'name': project.name,
                'location': project.location,
                'timezone': project.timezone,
                'currency': project.currency,
                'year': project.year,
                'energy_sources': [
                    {
                        'name': src.name,
                        'type': src.source_type,
                        'category': src.category,
                        'parameters': {
                            p.param_name: p.param_value for p in src.parameters
                        }
                    }
                    for src in project.energy_sources
                ]
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(project_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported project to {output_file}")
    
    def close(self):
        """Закрити БД"""
        self.conn.close()
        logger.info("Database connection closed")


# ============================================================================
# MAIN - ТЕСТУВАННЯ
# ============================================================================

if __name__ == '__main__':
    import os
    
    # Видалити старий файл БД для тесту
    db_path = "data/energy_system_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Створити БД
    db = EnergySystemDB(db_path)
    
    # Тест: Завантажити проект з JSON
    print("\n" + "="*80)
    print("🔋 ENERGY SYSTEM DATABASE - TEST")
    print("="*80)
    
    # Створити тестовий проект JSON
    test_project = {
        "project": {
            "name": "Chervonohrad Test",
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
                        "rated_power_mw": 2.5,
                        "efficiency_percent": 85,
                        "capacity_factor_annual_percent": 18
                    }
                },
                {
                    "name": "Battery Storage",
                    "type": "BESS",
                    "category": "storage",
                    "parameters": {
                        "rated_power_mw": 2.5,
                        "energy_capacity_mwh": 10.0,
                        "round_trip_efficiency_percent": 88,
                        "cycle_time_hours": 4.0
                    }
                }
            ]
        }
    }
    
    # Записати JSON файл
    with open("test_project.json", "w", encoding="utf-8") as f:
        json.dump(test_project, f, indent=2, ensure_ascii=False)
    
    # Завантажити проект
    project = db.load_project_from_json("test_project.json")
    
    print(f"\n✅ Project loaded: {project.name}")
    print(f"   Location: {project.location}")
    print(f"   Energy sources: {len(project.energy_sources)}")
    
    for source in project.energy_sources:
        print(f"\n   📌 {source.name} ({source.source_type})")
        print(f"      Parameters:")
        for param in source.parameters:
            print(f"        - {param.param_name}: {param.param_value} {param.param_unit}")
    
    # Отримати проект з БД
    retrieved_project = db.get_project(project.project_id)
    print(f"\n✅ Retrieved from DB: {retrieved_project.name}")
    print(f"   Total parameters: {sum(len(s.parameters) for s in retrieved_project.energy_sources)}")
    
    # Експортувати в JSON
    db.export_project_to_json(project.project_id, "exported_project.json")
    print("\n✅ Exported to exported_project.json")
    
    db.close()
    print("\n" + "="*80 + "\n")

