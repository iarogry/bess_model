#!/usr/bin/env python3
"""
Battery Simulator - Full Run
Execute: python run_simulation.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data.fetch_oree import OREEPriceFetcher, DemandProfileGenerator
from simulator import AnnualSimulator, EnergyConfig
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Complete pipeline:
    1. Fetch/generate price data
    2. Generate demand profile
    3. Run annual simulation
    4. Export results
    """
    
    DB_PATH = Path(__file__).parent / "data.db"
    OUTPUT_DIR = Path(__file__).parent / "results"
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("\n" + "=" * 70)
    print(" BATTERY SIMULATOR - FULL YEAR RUN")
    print("=" * 70)
    
    # Configuration
    start_date = "2025-01-01"
    end_date = "2025-12-31"
    
    # ========================================
    # STEP 1 & 2: Skip (Using real data from DB)
    # ========================================
    print("\n[1/3] Using real historical data from data.db...")
    
    # ========================================
    # STEP 3: Run Annual Simulation
    # ========================================
    print("\n[3/3] Running full-year simulation...")
    print("      (This will optimize 365 days × 24 hours)")
    print()
    
    config = EnergyConfig()
    config.pv_capacity_kw = 2500
    config.battery_capacity_kwh = 10000 # 10MWh as per user's earlier context
    config.battery_max_charge_kw = 2500
    config.battery_max_discharge_kw = 2500
    
    # Economics from user: 6750 UAH/kWh, 6000 cycles
    config.battery_capex_uah_per_kwh = 6750.0
    config.battery_lifespan_cycles = 6000
    
    simulator = AnnualSimulator(config, DB_PATH)
    results = simulator.simulate_year(start_date, end_date)


    
    # ========================================
    # STEP 4: Export Results
    # ========================================
    print("\n[4/3] Exporting results...")
    
    simulator.export_results_json(results, OUTPUT_DIR / "simulation_results.json")
    simulator.export_daily_csv(results, OUTPUT_DIR / "daily_summary.csv")
    simulator.export_monthly_csv(results, OUTPUT_DIR / "monthly_summary.csv")
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 70)
    print(" SIMULATION COMPLETE ✅")
    print("=" * 70)
    
    summary = results['annual_summary']
    
    print("\n📊 ANNUAL RESULTS:")
    print(f"   Total Revenue:        {summary['total_revenue_hrn']:>15,.2f} грн")
    print(f"   Daily Average:        {summary['avg_daily_revenue_hrn']:>15,.2f} грн")
    print(f"   Hourly Average:       {summary['avg_hourly_revenue_hrn']:>15,.2f} грн")
    
    print("\n⚡ ENERGY FLOWS (MWh):")
    print(f"   PV Generation:        {summary['pv_generation_mwh']:>15,.1f}")
    print(f"   Grid Purchased:       {summary['grid_purchased_mwh']:>15,.1f}")
    print(f"   Grid Sold:            {summary['grid_sold_mwh']:>15,.1f}")
    print(f"   CHP Output:           {summary['chp_output_mwh']:>15,.1f}")
    
    print("\n🔋 BATTERY STATS:")
    print(f"   Total Cycles:         {summary['battery_cycles']:>15,.1f}")
    print(f"   Charge (MWh):         {summary['battery_charge_mwh']:>15,.1f}")
    print(f"   Discharge (MWh):      {summary['battery_discharge_mwh']:>15,.1f}")
    print(f"   Final Capacity:       {summary['battery_final_capacity_kwh']:>15,.1f} kWh")
    print(f"   Degradation:          {summary['battery_degradation_percent']:>15,.2f}%")
    
    print("\n📁 EXPORTS:")
    print(f"   {OUTPUT_DIR / 'simulation_results.json'}")
    print(f"   {OUTPUT_DIR / 'daily_summary.csv'}")
    print(f"   {OUTPUT_DIR / 'monthly_summary.csv'}")
    
    # Push to PostgreSQL
    try:
        print("\n[5/3] Pushing data to PostgreSQL...")
        from migrate_to_postgres import sync_to_postgres
        sync_to_postgres()
    except Exception as e:
        print(f"⚠️ Could not push to PostgreSQL: {e}")

    print("\n" + "=" * 70)

    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
