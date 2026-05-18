
import json
import numpy as np
from src.optimizer_v5_scipy import Optimizer24hV5SciPy, EnergySourceConfig

def test_arbitrage_dynamic_costs():
    config = EnergySourceConfig()
    config.pv_capacity_kw = 0
    config.battery_capacity_kwh = 5000
    config.battery_max_charge_kw = 1000
    config.battery_max_discharge_kw = 1000
    
    # Custom battery parameters
    config.battery_capex_usd_per_kwh = 250.0  # $250 / kWh
    config.battery_lifespan_cycles = 6000     # 6000 cycles
    config.battery_degradation_threshold = 0.20 # to 20% loss
    
    optimizer = Optimizer24hV5SciPy(config)
    
    deg_cost = config.battery_degradation_cost_per_kwh
    print(f"\n--- Dynamic Battery Profile ---")
    print(f"CAPEX: {config.battery_capex_usd_per_kwh} USD/kWh")
    print(f"Lifespan: {config.battery_lifespan_cycles} cycles to {config.battery_degradation_threshold*100}% loss")
    print(f"Calculated Degradation Cost: {deg_cost:.4f} UAH/kWh throughput")
    print(f"Full Cycle Cost: {deg_cost * 2 * config.battery_capacity_kwh:,.0f} UAH")
    
    # SCENARIO: Two strong peaks
    prices = [500]*6 + [4000]*6 + [500]*6 + [4000]*6
    optimizer._load_prices = lambda date: prices
    optimizer._get_pv_profile = lambda date: [0.0]*24
    optimizer._get_demand_profile = lambda date: [0.0]*24
    
    print("\n--- Testing Multi-Strategy with Dynamic Costs ---")
    result = optimizer.optimize_day_multi_strategy("2026-01-01", initial_soc_kwh=2500)
    print(f"Strategy Chosen: {result['strategy_chosen']}")
    print(f"Total Revenue: {result['total_revenue']:,.2f} UAH")
    
    # Print throughput to verify cycle count
    throughput = sum(d['battery_charge'] + d['battery_discharge'] for d in result['dispatch'])
    print(f"Total Throughput: {throughput/1000:.2f} MWh (~{throughput/(2*config.battery_capacity_kwh):.2f} cycles)")

if __name__ == "__main__":
    test_arbitrage_dynamic_costs()


