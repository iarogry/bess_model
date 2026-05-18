
import sqlite3
from pathlib import Path

def extract_day_from_db(target_date):
    db_path = Path("data.db")
    if not db_path.exists():
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"--- Hourly Dispatch for {target_date} (from DB) ---")
    print(f"{'Hour':<6} | {'Price':<8} | {'Charge':<8} | {'Discharge':<10} | {'SoC':<8}")
    print("-" * 50)
    
    cursor.execute("""
        SELECT hour, price_hrn_per_mwh, battery_charge_kw, battery_discharge_kw, battery_soc_kwh 
        FROM dispatch_results 
        WHERE date = ? 
        ORDER BY hour
    """, (target_date,))
    
    rows = cursor.fetchall()
    for row in rows:
        hour, price, charge, discharge, soc = row
        print(f"{hour:<6} | {price:<8.0f} | {charge:<8.1f} | {discharge:<10.1f} | {soc:<8.1f}")
    
    if not rows:
        print(f"No data found for {target_date}")
    
    conn.close()

if __name__ == "__main__":
    extract_day_from_db("2024-05-22")
