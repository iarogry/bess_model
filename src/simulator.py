"""
Phase 4: Full-Year Simulator
Runs 365 days × 24h rolling window optimizations
Produces annual revenue, statistics, and detailed dispatch logs
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import json
import logging
from dotenv import load_dotenv

# Use centralized PostgreSQL connector
from db_connector import DBConnector
from optimizer_v5_scipy import Optimizer24hV5SciPy as Optimizer24h, EnergySourceConfig as EnergyConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnnualSimulator:
    """Run full-year simulation (365 days × 24h)"""
    
    def __init__(self, config: EnergyConfig):
        self.config = config
        self.optimizer = Optimizer24h(config)
        self._init_results_table()
    
    def _init_results_table(self):
        """Initialize database tables for dispatch results in PostgreSQL"""
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_results (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
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
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    date DATE PRIMARY KEY,
                    revenue_hrn REAL,
                    pv_mwh REAL,
                    grid_sold_mwh REAL,
                    grid_bought_mwh REAL,
                    chp_mwh REAL,
                    battery_charge_mwh REAL,
                    battery_discharge_mwh REAL,
                    battery_cycles REAL,
                    final_soc_kwh REAL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            cursor.close()
        finally:
            DBConnector.release_connection(conn)
    
    def simulate_year(self, start_date: str, end_date: str) -> Dict:
        """
        Simulate full year with 24h rolling windows using PostgreSQL
        """
        # 1. Clear previous results
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dispatch_results")
            cursor.execute("DELETE FROM daily_summary")
            conn.commit()
            cursor.close()
        finally:
            DBConnector.release_connection(conn)

        # 2. Refresh config from DB
        self.config._load_from_db()
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
        all_dispatch_records = []
        
        current = start
        day_count = 0
        current_soc = self.config.battery_capacity_kwh * 0.5  # Start at 50%
        
        while current <= end:
            day_count += 1
            date_str = current.strftime("%Y-%m-%d")
            month_key = current.strftime("%Y-%m")
            
            if month_key not in monthly_buckets:
                monthly_buckets[month_key] = {
                    "revenue": 0, "pv_mwh": 0, "grid_sold": 0, 
                    "grid_bought": 0, "chp_mwh": 0, "days": 0
                }
            
            day_result = self.optimizer.optimize_day(date_str, current_soc)
            daily_revenue = day_result["total_revenue"]
            dispatch = day_result["dispatch"]
            final_soc = day_result["final_soc"]
            
            pv_total = sum(d["pv_total"] for d in dispatch) / 1000
            grid_sell = sum(d["grid_export"] for d in dispatch) / 1000
            grid_buy = sum(d.get("grid_import_total", 0) for d in dispatch) / 1000
            chp_total = sum(d.get("chp_kw", 0) for d in dispatch) / 1000
            charge_total = sum(d["battery_charge"] for d in dispatch) / 1000
            discharge_total = sum(d["battery_discharge"] for d in dispatch) / 1000
            battery_cycles = (charge_total + discharge_total) / (2 * self.config.battery_capacity_kwh / 1000)
            
            for d in dispatch:
                all_dispatch_records.append((
                    date_str, int(d["hour"]), float(d["price_rdn"]),
                    float(d["pv_total"]), float(d.get("grid_import_total", 0)), float(d["grid_export"]),
                    float(d.get("chp_kw", 0)), float(d["battery_charge"]), float(d["battery_discharge"]),
                    float(d["soc_after"]), float(d["revenue"])
                ))
            
            current_soc = final_soc
            annual_results["total_revenue_hrn"] += float(daily_revenue)
            annual_results["pv_generation_mwh"] += float(pv_total)
            annual_results["grid_purchased_mwh"] += float(grid_buy)
            annual_results["grid_sold_mwh"] += float(grid_sell)
            annual_results["chp_output_mwh"] += float(chp_total)
            annual_results["battery_cycles"] += float(battery_cycles)
            annual_results["battery_charge_mwh"] += float(charge_total)
            annual_results["battery_discharge_mwh"] += float(discharge_total)
            
            monthly_buckets[month_key]["revenue"] += daily_revenue
            monthly_buckets[month_key]["pv_mwh"] += pv_total
            monthly_buckets[month_key]["grid_sold"] += grid_sell
            monthly_buckets[month_key]["grid_bought"] += grid_buy
            monthly_buckets[month_key]["chp_mwh"] += chp_total
            monthly_buckets[month_key]["days"] += 1
            
            daily_results.append({
                "date": date_str, "revenue_hrn": round(daily_revenue, 2),
                "pv_mwh": round(pv_total, 3), "grid_sold_mwh": round(grid_sell, 3),
                "grid_bought_mwh": round(grid_buy, 3), "chp_mwh": round(chp_total, 3),
                "battery_charge_mwh": round(charge_total, 3), "battery_discharge_mwh": round(discharge_total, 3),
                "battery_cycles": round(battery_cycles, 3), "final_soc_kwh": round(final_soc, 1),
            })
            
            if day_count % 30 == 0 or day_count == total_days:
                progress_pct = (day_count / total_days) * 100
                logger.info(f"Day {day_count:3d}/{total_days}: {date_str} - "
                           f"Revenue: {daily_revenue:8,.0f} грн | "
                           f"YTD: {annual_results['total_revenue_hrn']:10,.0f} грн | "
                           f"Progress: {progress_pct:5.1f}%")
            
            current += timedelta(days=1)
        
        self._bulk_store_dispatch_details(all_dispatch_records)
        
        battery_degradation = annual_results["battery_cycles"] * 0.003
        final_capacity = self.config.battery_capacity_kwh * (1 - battery_degradation / 100)
        
        monthly_breakdown = []
        for month_key in sorted(monthly_buckets.keys()):
            bucket = monthly_buckets[month_key]
            monthly_breakdown.append({
                "month": month_key, "days": bucket["days"],
                "revenue_hrn": round(bucket["revenue"], 2),
                "avg_daily_revenue_hrn": round(bucket["revenue"] / max(1, bucket["days"]), 2),
                "pv_mwh": round(bucket["pv_mwh"], 1), "grid_sold_mwh": round(bucket["grid_sold"], 1),
                "grid_bought_mwh": round(bucket["grid_bought"], 1), "chp_mwh": round(bucket["chp_mwh"], 1),
            })
        
        results = {
            "simulation_period": {"start_date": start_date, "end_date": end_date, "days": total_days},
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
        logger.info(f"Battery Cycles: {results['annual_summary']['battery_cycles']:.1f}")
        logger.info("=" * 70 + "\n")
        
        return results
    
    def _bulk_store_dispatch_details(self, all_records: List[tuple]):
        """Store all detailed dispatch schedules in PostgreSQL in one transaction"""
        if not all_records: return
        conn = DBConnector.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO dispatch_results
                (date, hour, price_hrn_per_mwh, pv_kw, grid_buy_kw, grid_sell_kw, 
                 chp_kw, battery_charge_kw, battery_discharge_kw, battery_soc_kwh, revenue_hrn)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, all_records)
            conn.commit()
            logger.info(f"Bulk stored {len(all_records)} hourly records in PostgreSQL.")
            cursor.close()
        except Exception as e:
            logger.error(f"Error in bulk storing dispatch records: {e}")
            conn.rollback()
        finally:
            DBConnector.release_connection(conn)
    
    def export_results_json(self, results: Dict, output_path: Path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results exported to {output_path}")
    
    def export_daily_csv(self, results: Dict, output_path: Path):
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
    config = EnergyConfig()
    # Initial defaults, will be overridden by load_from_db
    config.pv_capacity_kw = 2500
    config.battery_capacity_kwh = 5000
    
    start_date = "2025-01-01"
    end_date = "2025-12-31"
    
    simulator = AnnualSimulator(config)
    results = simulator.simulate_year(start_date, end_date)
    
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    simulator.export_results_json(results, output_dir / "simulation_results.json")
    simulator.export_daily_csv(results, output_dir / "daily_summary.csv")
    
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print(f"Annual Revenue: {results['annual_summary']['total_revenue_hrn']:,.2f} грн")
    print(f"Results saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
