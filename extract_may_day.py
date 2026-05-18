
import json
from pathlib import Path

def extract_day(target_date):
    path = Path("results/simulation_results.json")
    with open(path, 'r') as f:
        data = json.load(f)
    
    print(f"--- Hourly Dispatch for {target_date} ---")
    print(f"{'Hour':<6} | {'Price':<8} | {'Charge':<8} | {'Discharge':<10} | {'SoC':<8}")
    print("-" * 50)
    
    found = False
    for d in data['dispatch']:
        if d['date'] == target_date:
            found = True
            print(f"{d['hour']:<6} | {d['price_rdn']:<8.0f} | {d['battery_charge']:<8.1f} | {d['battery_discharge']:<10.1f} | {d['soc_after']:<8.1f}")
    
    if not found:
        print(f"No data found for {target_date}")

if __name__ == "__main__":
    extract_day("2024-05-22")
