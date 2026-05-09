"""
Chervonohrad BESS Simulator - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import json

from models import (
    BESSConfig, GasScenario, GenerationMix, SimulationRequest, 
    SimulationOutput, GasScenarioType
)
from rdn_api import RDNClient
from simulator import BESSSimulator

app = FastAPI(
    title="Chervonohrad BESS Simulator",
    description="Battery Energy Storage System modeling for renewable + storage combinations",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
rdn_client = RDNClient()
simulator = BESSSimulator(rdn_client=rdn_client)

# In-memory storage (replace with DB later)
bess_configs: dict = {}
saved_simulations: dict = {}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now()}


# ============ BESS Constructor Endpoints ============

@app.post("/bess/create")
async def create_bess_config(config: BESSConfig):
    """Create new BESS configuration"""
    config.id = str(uuid.uuid4())
    bess_configs[config.id] = config.dict()
    return {"id": config.id, "config": config}


@app.get("/bess/{config_id}")
async def get_bess_config(config_id: str):
    """Get BESS configuration by ID"""
    if config_id not in bess_configs:
        raise HTTPException(status_code=404, detail="BESS config not found")
    return bess_configs[config_id]


@app.get("/bess")
async def list_bess_configs():
    """List all BESS configurations"""
    return list(bess_configs.values())


@app.delete("/bess/{config_id}")
async def delete_bess_config(config_id: str):
    """Delete BESS configuration"""
    if config_id not in bess_configs:
        raise HTTPException(status_code=404, detail="BESS config not found")
    del bess_configs[config_id]
    return {"deleted": config_id}


# ============ Gas Scenario Endpoints ============

@app.post("/gas/scenarios")
async def get_gas_scenarios():
    """Get predefined gas scenarios"""
    return {
        "low": {
            "type": "low",
            "gas_price_per_mmbtu": 3.0,
            "plant_efficiency": 0.45,
            "min_load_pct": 0.3,
            "ramp_rate_mw_per_min": 10,
            "co2_price_per_ton": 80
        },
        "mid": {
            "type": "mid",
            "gas_price_per_mmbtu": 5.0,
            "plant_efficiency": 0.45,
            "min_load_pct": 0.3,
            "ramp_rate_mw_per_min": 10,
            "co2_price_per_ton": 80
        },
        "high": {
            "type": "high",
            "gas_price_per_mmbtu": 8.0,
            "plant_efficiency": 0.45,
            "min_load_pct": 0.3,
            "ramp_rate_mw_per_min": 10,
            "co2_price_per_ton": 80
        }
    }


# ============ Simulation Endpoints ============

@app.post("/simulate")
async def run_simulation(request: SimulationRequest):
    """
    Run battery simulation
    
    Returns output in < 1 second
    Report generation happens async
    """
    try:
        # Run simulation
        result = await simulator.run(request)
        
        # Save for report generation
        sim_id = str(uuid.uuid4())
        saved_simulations[sim_id] = {
            "request": request.dict(),
            "result": result.dict(),
            "created_at": datetime.now()
        }
        
        return {
            "simulation_id": sim_id,
            "output": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/simulation/{sim_id}")
async def get_simulation(sim_id: str):
    """Get saved simulation"""
    if sim_id not in saved_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return saved_simulations[sim_id]


@app.post("/simulate/compare")
async def compare_scenarios(scenarios: list[SimulationRequest]):
    """Compare multiple scenarios"""
    results = []
    for scenario in scenarios:
        result = await simulator.run(scenario)
        results.append(result)
    
    # Rank by IRR
    ranked = sorted(results, key=lambda x: x.irr_pct, reverse=True)
    
    return {
        "scenarios": len(scenarios),
        "results": ranked,
        "best_3": ranked[:3]
    }


# ============ Report Endpoints ============

@app.post("/report/pdf")
async def generate_pdf_report(sim_id: str):
    """
    Generate PDF report
    
    Async job - returns task_id
    Can take up to 60 seconds
    """
    if sim_id not in saved_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # TODO: Implement async task
    return {
        "task_id": str(uuid.uuid4()),
        "status": "generating",
        "estimated_time_seconds": 30
    }


@app.post("/report/excel")
async def generate_excel_report(sim_id: str):
    """Generate Excel report with detailed monthly/yearly breakdown"""
    if sim_id not in saved_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # TODO: Implement async task
    return {
        "task_id": str(uuid.uuid4()),
        "status": "generating",
        "estimated_time_seconds": 20
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
