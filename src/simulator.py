"""
Phase 4: Full-Year Simulator
Runs 365 days × 24h rolling window optimizations
Produces annual revenue, statistics, and detailed dispatch logs
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import json
import logging

from optimizer_v5_scipy import Optimizer24hV5SciPy as Optimizer24h, EnergySourceConfig as EnergyConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data.db"


class AnnualSimulator:
    """Run full-year simulation (365 days × 24h)"""
    
    def __init__(self, config: EnergyConfig, db_path=DB_PATH):
        self.config = config
        self.db_path = db_path
        self.optimizer = Optimizer24h(config, db_path)
        self._init_results_table()
    
    def _init_results_table(self):
        """Initialize database table for dispatch results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_results (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                hour INTEGER NOT NULL,
                price_hrn_per_mwh REAL,
                pv_kw REAL,
                grid_buy_kw REAL,
                grid_sell_kw REAL,
                chp_kw REAL,
                battery_charge_kw REAL,
                battery_discharge_kw REAL,
                battery_soc_kwh REAL,
                revenue_hrn REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                date TEXT PRIMARY KEY,
                revenue_hrn REAL,
                pv_mwh REAL,
                grid_sold_mwh REAL,
                grid_bought_mwh REAL,
                chp_mwh REAL,
                battery_charge_mwh REAL,
                battery_discharge_mwh REAL,
                battery_cycles REAL,
                final_soc_kwh REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def simulate_year(self, start_date: str, end_date: str) -> Dict:
        """
        Simulate full year with 24h rolling windows
        """
        # 1. Clear previous results from SQLite to avoid mixing data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dispatch_results")
        cursor.execute("DELETE FROM daily_summary")
        conn.commit()
        conn.close()

        # 2. Refresh config from DB just in case
        self.config._load_from_db(self.db_path)
        logger.info(f"Config loaded: Battery {self.config.battery_capacity_kwh}kWh, SOC {self.config.battery_soc_min_percent}%-{self.config.battery_soc_max_percent}%")

        start = datetime.strptime(start_date, "%Y-%m-%d")

        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_days = (end - start).days + 1
        
        logger.info("=" * 70)
        logger.info(f"ANNUAL SIMULATION: {start_date} to {end_date}")
        logger.info(f"Total days: {total_days}")
        logger.info("=" * 70)
        
        annual_results = {
            "total_revenue_hrn": 0,
            "pv_generation_mwh": 0,
            "grid_purchased_mwh": 0,
            "grid_sold_mwh": 0,
            "chp_output_mwh": 0,
            "battery_cycles": 0,
            "battery_charge_mwh": 0,
            "battery_discharge_mwh": 0,
        }
        
        daily_results = []
        monthly_buckets = {}
        
        current = start
        day_count = 0
        current_soc = self.config.battery_capacity_kwh * 0.5  # Start at 50%
        
        while current <= end:
            day_count += 1
            date_str = current.strftime("%Y-%m-%d")
            month_key = current.strftime("%Y-%m")
            
            # Initialize month bucket
            if month_key not in monthly_buckets:
                monthly_buckets[month_key] = {
                    "revenue": 0,
                    "pv_mwh": 0,
                    "grid_sold": 0,
                    "grid_bought": 0,
                    "chp_mwh": 0,
                    "days": 0
                }
            
            # Step 1: Optimize this day
            day_result = self.optimizer.optimize_day(date_str, current_soc)
            
            # Step 2: Extract results
            daily_revenue = day_result["total_revenue"]
            dispatch = day_result["dispatch"]
            final_soc = day_result["final_soc"]
            
            # Calculate daily aggregates
            pv_total = sum(d["pv_total"] for d in dispatch) / 1000  # kW → MWh
            grid_sell = sum(d["grid_export"] for d in dispatch) / 1000
            grid_buy = sum(d.get("grid_import_total", d.get("grid_import", 0)) for d in dispatch) / 1000
            chp_total = sum(d.get("chp_kw", 0) for d in dispatch) / 1000
            charge_total = sum(d["battery_charge"] for d in dispatch) / 1000
            discharge_total = sum(d["battery_discharge"] for d in dispatch) / 1000
            
            # Battery cycles (full cycle = 2× charge+discharge)
            battery_cycles = (charge_total + discharge_total) / (2 * self.config.battery_capacity_kwh / 1000)
            
            # Step 3: Store dispatch details
            self._store_dispatch_details(date_str, dispatch)
            
            # Step 4: Update SoC for next day
            current_soc = final_soc
            
            # Step 5: Accumulate annual totals
            annual_results["total_revenue_hrn"] += daily_revenue
            annual_results["pv_generation_mwh"] += pv_total
            annual_results["grid_purchased_mwh"] += grid_buy
            annual_results["grid_sold_mwh"] += grid_sell
            annual_results["chp_output_mwh"] += chp_total
            annual_results["battery_cycles"] += battery_cycles
            annual_results["battery_charge_mwh"] += charge_total
            annual_results["battery_discharge_mwh"] += discharge_total
            
            # Step 6: Update monthly bucket
            monthly_buckets[month_key]["revenue"] += daily_revenue
            monthly_buckets[month_key]["pv_mwh"] += pv_total
            monthly_buckets[month_key]["grid_sold"] += grid_sell
            monthly_buckets[month_key]["grid_bought"] += grid_buy
            monthly_buckets[month_key]["chp_mwh"] += chp_total
            monthly_buckets[month_key]["days"] += 1
            
            # Step 7: Store daily summary
            daily_results.append({
                "date": date_str,
                "revenue_hrn": round(daily_revenue, 2),
                "pv_mwh": round(pv_total, 3),
                "grid_sold_mwh": round(grid_sell, 3),
                "grid_bought_mwh": round(grid_buy, 3),
                "chp_mwh": round(chp_total, 3),
                "battery_charge_mwh": round(charge_total, 3),
                "battery_discharge_mwh": round(discharge_total, 3),
                "battery_cycles": round(battery_cycles, 3),
                "final_soc_kwh": round(final_soc, 1),
            })
            
            # Step 8: Progress logging
            if day_count % 30 == 0 or day_count == total_days:
                progress_pct = (day_count / total_days) * 100
                logger.info(f"Day {day_count:3d}/{total_days}: {date_str} - "
                           f"Revenue: {daily_revenue:8,.0f} грн | "
                           f"YTD: {annual_results['total_revenue_hrn']:10,.0f} грн | "
                           f"Progress: {progress_pct:5.1f}%")
            
            current += timedelta(days=1)
        
        # Calculate battery degradation
        battery_degradation = annual_results["battery_cycles"] * 0.003  # ~0.3% per cycle
        final_capacity = self.config.battery_capacity_kwh * (1 - battery_degradation / 100)
        
        # Build monthly breakdown
        monthly_breakdown = []
        for month_key in sorted(monthly_buckets.keys()):
            bucket = monthly_buckets[month_key]
            monthly_breakdown.append({
                "month": month_key,
                "days": bucket["days"],
                "revenue_hrn": round(bucket["revenue"], 2),
                "avg_daily_revenue_hrn": round(bucket["revenue"] / max(1, bucket["days"]), 2),
                "pv_mwh": round(bucket["pv_mwh"], 1),
                "grid_sold_mwh": round(bucket["grid_sold"], 1),
                "grid_bought_mwh": round(bucket["grid_bought"], 1),
                "chp_mwh": round(bucket["chp_mwh"], 1),
            })
        
        # Final results
        results = {
            "simulation_period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": total_days
            },
            "annual_summary": {
                "total_revenue_hrn": round(annual_results["total_revenue_hrn"], 2),
                "avg_daily_revenue_hrn": round(annual_results["total_revenue_hrn"] / total_days, 2),
                "avg_hourly_revenue_hrn": round(annual_results["total_revenue_hrn"] / (total_days * 24), 2),
                "pv_generation_mwh": round(annual_results["pv_generation_mwh"], 1),
                "grid_purchased_mwh": round(annual_results["grid_purchased_mwh"], 1),
                "grid_sold_mwh": round(annual_results["grid_sold_mwh"], 1),
                "chp_output_mwh": round(annual_results["chp_output_mwh"], 1),
                "battery_cycles": round(annual_results["battery_cycles"], 1),
                "battery_charge_mwh": round(annual_results["battery_charge_mwh"], 1),
                "battery_discharge_mwh": round(annual_results["battery_discharge_mwh"], 1),
                "battery_final_capacity_kwh": round(final_capacity, 1),
                "battery_degradation_percent": round(battery_degradation, 2)
            },
            "monthly_breakdown": monthly_breakdown,
            "daily_results": daily_results,
            "configuration": {
                "pv_capacity_kw": self.config.pv_capacity_kw,
                "battery_capacity_kwh": self.config.battery_capacity_kwh,
                "chp_capacity_kw": self.config.chp_capacity_kw,
            }
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("SIMULATION COMPLETE")
        logger.info(f"Annual Revenue: {results['annual_summary']['total_revenue_hrn']:,.2f} грн")
        logger.info(f"Average Daily: {results['annual_summary']['avg_daily_revenue_hrn']:,.2f} грн")
        logger.info(f"PV Generation: {results['annual_summary']['pv_generation_mwh']:,.1f} MWh")
        logger.info(f"Grid Sold: {results['annual_summary']['grid_sold_mwh']:,.1f} MWh")
        logger.info(f"Battery Cycles: {results['annual_summary']['battery_cycles']:.1f}")
        logger.info(f"Battery Degradation: {results['annual_summary']['battery_degradation_percent']:.2f}%")
        logger.info("=" * 70 + "\n")
        
        return results
    
    def _store_dispatch_details(self, date: str, dispatch: List[Dict]):
        """Store detailed dispatch schedule in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for d in dispatch:
                cursor.execute("""
                    INSERT INTO dispatch_results
                    (date, hour, price_hrn_per_mwh, pv_kw, grid_buy_kw, grid_sell_kw, 
                     chp_kw, battery_charge_kw, battery_discharge_kw, battery_soc_kwh, revenue_hrn)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    date, d["hour"], d["price_rdn"],
                    d["pv_total"], d.get("grid_import_total", d.get("grid_import", 0)), d["grid_export"],
                    d.get("chp_kw", 0), d["battery_charge"], d["battery_discharge"],
                    d["soc_after"], d["revenue"]
                ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing dispatch for {date}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def export_results_json(self, results: Dict, output_path: Path):
        """Export full results to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results exported to {output_path}")
    
    def export_daily_csv(self, results: Dict, output_path: Path):
        """Export daily summary to CSV"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'revenue_hrn', 'pv_mwh', 'grid_sold_mwh', 'grid_bought_mwh',
                'chp_mwh', 'battery_charge_mwh', 'battery_discharge_mwh', 'battery_cycles', 'final_soc_kwh'
            ])
            writer.writeheader()
            writer.writerows(results['daily_results'])
        
        logger.info(f"Daily summary exported to {output_path}")
    
    def export_monthly_csv(self, results: Dict, output_path: Path):
        """Export monthly summary to CSV"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'month', 'days', 'revenue_hrn', 'avg_daily_revenue_hrn',
                'pv_mwh', 'grid_sold_mwh', 'grid_bought_mwh', 'chp_mwh'
            ])
            writer.writeheader()
            writer.writerows(results['monthly_breakdown'])
        
        logger.info(f"Monthly summary exported to {output_path}")


def main():
    """Main: Run full-year simulation"""
    
    # Configuration
    config = EnergyConfig()
    config.pv_capacity_kw = 2500
    config.battery_capacity_kwh = 5000
    config.chp_capacity_kw = 1000
    
    # Simulation period
    start_date = "2025-05-10"
    end_date = "2026-05-09"
    
    # Run simulation
    simulator = AnnualSimulator(config)
    results = simulator.simulate_year(start_date, end_date)
    
    # Export results
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    simulator.export_results_json(results, output_dir / "simulation_results.json")
    simulator.export_daily_csv(results, output_dir / "daily_summary.csv")
    simulator.export_monthly_csv(results, output_dir / "monthly_summary.csv")
    
    # Print summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Period: {start_date} to {end_date}")
    print(f"Annual Revenue: {results['annual_summary']['total_revenue_hrn']:,.2f} грн")
    print(f"Daily Average: {results['annual_summary']['avg_daily_revenue_hrn']:,.2f} грн")
    print(f"PV Generation: {results['annual_summary']['pv_generation_mwh']:,.1f} MWh")
    print(f"Battery Degradation: {results['annual_summary']['battery_degradation_percent']:.2f}%")
    print(f"\nResults saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
