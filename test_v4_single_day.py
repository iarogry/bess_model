#!/usr/bin/env python3
"""
Test V4 optimizer on a single day (May 1, 2026)
Check: energy balance, revenue, PV utilization
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from optimizer_v4_scipy import Optimizer24hV4SciPy, EnergySourceConfig
import json

DB_PATH = Path(__file__).parent / "data.db"

def main():
    print("\n" + "=" * 80)
    print(" V4 OPTIMIZER - SINGLE DAY TEST")
    print("=" * 80)
    
    config = EnergySourceConfig()
    optimizer = Optimizer24hV4SciPy(config, DB_PATH)
    
    # Test on May 1, 2026 (real prices)
    test_date = "2026-05-01"
    initial_soc = 2500.0  # 50% of 5000 kWh
    
    print(f"\nOptimizing {test_date}...")
    print(f"Initial SoC: {initial_soc} kWh")
    print()
    
    result = optimizer.optimize_day(test_date, initial_soc)
    
    # Print summary
    print("\n" + "-" * 80)
    print("RESULT SUMMARY")
    print("-" * 80)
    print(f"Date: {result['date']}")
    print(f"Optimizer: {result['optimizer_used']}")
    print(f"Daily Revenue: {result['total_revenue']:,.0f} грн")
    print(f"Final SoC: {result['final_soc']:.1f} kWh")
    print(f"Energy Balance Error: {result['energy_balance_error']:.2f} kWh")
    print(f"PV Utilization: {result['pv_utilization']*100:.1f}%")
    
    # Print dispatch details
    print("\n" + "-" * 80)
    print("HOURLY DISPATCH")
    print("-" * 80)
    print(f"{'Hour':>4} {'Price':>8} {'Demand':>8} {'PV Avail':>8} {'PV→D':>7} {'PV→E':>7} {'PV→C':>7} "
          f"{'BC':>7} {'BD':>7} {'GI':>7} {'GE':>7} {'SOC':>8} {'Rev':>10}")
    print("-" * 140)
    
    for h in result['dispatch']:
        hour = h['hour']
        price = h['price_rdn']
        demand = h['demand']
        pv_avail = h['pv_available']
        pv_d = h['pv_to_demand']
        pv_e = h['pv_to_export']
        pv_c = h['pv_to_charge']
        bc = h['battery_charge']
        bd = h['battery_discharge']
        gi = h['grid_import']
        ge = h['grid_export']
        soc = h['soc_after']
        rev = h['revenue']
        balance_err = h['balance_error']
        
        print(f"{hour:4d} {price:8.0f} {demand:8.1f} {pv_avail:8.1f} {pv_d:7.1f} {pv_e:7.1f} {pv_c:7.1f} "
              f"{bc:7.1f} {bd:7.1f} {gi:7.1f} {ge:7.1f} {soc:8.1f} {rev:10.0f}")
    
    # Validate energy balance
    print("\n" + "-" * 80)
    print("ENERGY BALANCE VALIDATION")
    print("-" * 80)
    
    total_supplied = 0
    total_demanded = 0
    max_error = 0
    
    for h in result['dispatch']:
        supplied = h['energy_supplied']
        demanded = h['energy_demanded']
        error = h['balance_error']
        
        total_supplied += supplied
        total_demanded += demanded
        max_error = max(max_error, abs(error))
    
    print(f"Total Energy Supplied: {total_supplied:.2f} kWh")
    print(f"Total Energy Demanded: {total_demanded:.2f} kWh")
    print(f"Cumulative Balance Error: {result['energy_balance_error']:.2f} kWh")
    print(f"Max Hourly Error: {max_error:.2f} kWh")
    print(f"Average Hourly Error: {result['energy_balance_error']/24:.4f} kWh")
    
    # Health check
    print("\n" + "-" * 80)
    print("HEALTH CHECK")
    print("-" * 80)
    
    health_ok = True
    
    if abs(result['energy_balance_error']) > 1.0:
        print(f"❌ Energy balance error too large: {result['energy_balance_error']:.2f} kWh")
        health_ok = False
    else:
        print(f"✅ Energy balance OK (error: {result['energy_balance_error']:.2f} kWh)")
    
    if result['pv_utilization'] < 0.8:
        print(f"⚠️  Low PV utilization: {result['pv_utilization']*100:.1f}%")
    else:
        print(f"✅ PV utilization good: {result['pv_utilization']*100:.1f}%")
    
    if result['final_soc'] < 1000:
        print(f"⚠️  Low final SoC: {result['final_soc']:.1f} kWh")
    else:
        print(f"✅ Final SoC healthy: {result['final_soc']:.1f} kWh")
    
    print("\n" + "=" * 80)
    if health_ok:
        print("✅ V4 SINGLE DAY TEST PASSED")
    else:
        print("❌ V4 SINGLE DAY TEST FAILED - CHECK CONSTRAINTS")
    print("=" * 80 + "\n")
    
    # Save detailed results
    output_file = Path(__file__).parent / "results" / "v4_single_day_test.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Convert for JSON serialization
        result_json = result.copy()
        result_json['dispatch'] = result['dispatch']
        json.dump(result_json, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Detailed results saved to {output_file}\n")
    
    return 0 if health_ok else 1

if __name__ == "__main__":
    sys.exit(main())
