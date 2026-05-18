#!/usr/bin/env python3
"""
Test V5 optimizer on May 1, 2026
V5 = V4 + Grid Charging (arbitrage: buy low, sell high)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from optimizer_v5_scipy import Optimizer24hV5SciPy, EnergySourceConfig
import json

DB_PATH = Path(__file__).parent / "data.db"

def main():
    print("\n" + "=" * 80)
    print(" V5 OPTIMIZER - SINGLE DAY TEST (WITH GRID ARBITRAGE)")
    print("=" * 80)
    
    config = EnergySourceConfig()
    optimizer = Optimizer24hV5SciPy(config, DB_PATH)
    
    test_date = "2026-05-01"
    initial_soc = 2500.0
    
    print(f"\nOptimizing {test_date} with grid charging enabled...")
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
    print(f"Grid Arbitrage: {result['grid_arbitrage_mwh']:.3f} MWh (grid → battery)")
    
    # Analyze arbitrage opportunities
    print("\n" + "-" * 80)
    print("ARBITRAGE ANALYSIS (Grid → Battery)")
    print("-" * 80)
    print(f"{'Hour':>4} {'Price':>8} {'Grid→B':>8} {'Status':>20}")
    print("-" * 50)
    
    arbitrage_hours = []
    for h in result['dispatch']:
        hour = h['hour']
        price = h['price_rdn']
        grid_to_b = h['grid_to_battery']
        
        if grid_to_b > 1:
            status = "⚡ CHARGING FROM GRID"
            arbitrage_hours.append((hour, price, grid_to_b))
        else:
            status = "-"
        
        if grid_to_b > 1 or (h['hour'] < 6 or h['hour'] > 18):  # Show night hours
            print(f"{hour:4d} {price:8.0f} {grid_to_b:8.1f} {status:>20}")
    
    if arbitrage_hours:
        print("\n" + "-" * 80)
        print("ARBITRAGE PROFIT BREAKDOWN")
        print("-" * 80)
        print(f"Grid arbitrage detected in {len(arbitrage_hours)} hour(s)")
        print("Strategy: buy cheap (night) → charge battery → sell expensive (day)")
    else:
        print("\nℹ️  No grid arbitrage detected (prices relatively flat)")
    
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
    
    if result['grid_arbitrage_mwh'] > 0.001:
        print(f"⚡ Grid arbitrage active: {result['grid_arbitrage_mwh']:.3f} MWh")
    
    print("\n" + "=" * 80)
    if health_ok:
        print("✅ V5 SINGLE DAY TEST PASSED")
    else:
        print("❌ V5 SINGLE DAY TEST FAILED - CHECK CONSTRAINTS")
    print("=" * 80 + "\n")
    
    # Save detailed results
    output_file = Path(__file__).parent / "results" / "v5_single_day_test.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        result_json = result.copy()
        result_json['dispatch'] = result['dispatch']
        json.dump(result_json, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Detailed results saved to {output_file}\n")
    
    return 0 if health_ok else 1

if __name__ == "__main__":
    sys.exit(main())
