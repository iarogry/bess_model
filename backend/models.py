"""
Data models for Chervonohrad BESS Simulator
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class GasScenarioType(str, Enum):
    LOW = "low"        # $3/MMBtu
    MID = "mid"        # $5/MMBtu
    HIGH = "high"      # $8/MMBtu
    CUSTOM = "custom"


class BESSConfig(BaseModel):
    """Battery Energy Storage System configuration"""
    id: Optional[str] = None
    name: str = Field(..., description="e.g., 'Hithium 5MW/20MWh'")
    manufacturer: str = Field(..., description="e.g., 'Hithium', 'CATL', 'BYD'")
    power_mw: float = Field(..., gt=0, description="Power rating in MW")
    capacity_mwh: float = Field(..., gt=0, description="Energy capacity in MWh")
    capex_per_mwh: float = Field(..., gt=0, description="€/MWh")
    capex_per_mw: float = Field(..., gt=0, description="€/MW")
    opex_per_year_pct: float = Field(..., gt=0, le=100, description="% of CAPEX/year")
    efficiency: float = Field(default=0.92, ge=0.8, le=0.99, description="Round-trip efficiency")
    lifespan_years: int = Field(default=10, description="System lifespan in years")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Hithium 5MW/20MWh",
                "manufacturer": "Hithium",
                "power_mw": 5.0,
                "capacity_mwh": 20.0,
                "capex_per_mwh": 1500,
                "capex_per_mw": 500,
                "opex_per_year_pct": 2.5,
                "efficiency": 0.92
            }
        }


class GasScenario(BaseModel):
    """Gas generation scenario"""
    type: GasScenarioType
    gas_price_per_mmbtu: float = Field(..., gt=0, description="Gas price $/MMBtu")
    plant_efficiency: float = Field(default=0.45, ge=0.35, le=0.60, description="Gas plant efficiency")
    min_load_pct: float = Field(default=0.3, ge=0, le=1, description="Minimum load %")
    ramp_rate_mw_per_min: float = Field(default=10, gt=0, description="Ramp rate MW/min")
    co2_price_per_ton: float = Field(default=80, ge=0, description="€/ton CO2")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "mid",
                "gas_price_per_mmbtu": 5.0,
                "plant_efficiency": 0.45,
                "min_load_pct": 0.3
            }
        }


class GenerationMix(BaseModel):
    """Generation sources configuration"""
    bess: BESSConfig
    solar_mw: float = Field(default=0, ge=0, description="Solar capacity MW")
    wind_mw: float = Field(default=0, ge=0, description="Wind capacity MW")
    gas_enabled: bool = Field(default=False, description="Enable gas generation")
    gas_scenario: Optional[GasScenario] = None
    bess_only: bool = Field(default=False, description="BESS standalone mode")


class SimulationRequest(BaseModel):
    """Simulation request"""
    generation_mix: GenerationMix
    year: int = Field(default=2025, ge=2020, le=2050)
    simulation_years: int = Field(default=10, ge=1, le=25, description="Years to simulate")


class SimulationResult(BaseModel):
    """Single hour simulation result"""
    hour: int  # 0-8759
    rdn_price_uah_per_mwh: float
    solar_output_mwh: float
    wind_output_mwh: float
    bess_charge_mwh: float  # positive = charging
    bess_soc_pct: float  # state of charge %
    gas_output_mwh: float
    total_revenue_uah: float
    total_opex_uah: float


class AnnualResult(BaseModel):
    """Annual aggregated results"""
    year: int
    total_revenue_uah: float
    total_opex_uah: float
    total_capex_uah: float = 0  # CAPEX only in year 1
    net_cashflow_uah: float
    cumulative_cashflow_uah: float


class SensitivityResult(BaseModel):
    """Sensitivity analysis for one parameter"""
    parameter: str  # "gas_price", "solar_output", "wind_output"
    scenarios: List[dict]  # [{scenario_name, irr, npv, payback_years}]


class SimulationOutput(BaseModel):
    """Complete simulation output"""
    generation_mix: GenerationMix
    annual_results: List[AnnualResult]
    irr_pct: float
    npv_eur: float
    payback_years: float
    capex_eur: float
    opex_annual_eur: float
    revenue_annual_avg_eur: float
    sensitivity: List[SensitivityResult]
    calculated_at: datetime
    
    class Config:
        json_schema_extra = {
            "description": "Complete simulation results for investor report"
        }
