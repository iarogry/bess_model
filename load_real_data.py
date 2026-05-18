
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

def setup_real_data():
    db_path = Path("data.db")
    json_path = Path("chervonohrad_data_corrected.json")
    
    if not json_path.exists():
        print(f"Error: {json_path} not found!")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    prices = data['hourly_data']['price_rdn_uah_per_mwh']
    pv_gen = data['hourly_data']['pv_generation_kwh']
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop and Re-create with correct schema
    cursor.execute("DROP TABLE IF EXISTS prices")
    cursor.execute("DROP TABLE IF EXISTS demand")
    cursor.execute("DROP TABLE IF EXISTS pv_profile")
    
    cursor.execute("""
        CREATE TABLE prices (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            price_hrn_per_mwh REAL NOT NULL,
            source TEXT DEFAULT 'historical',
            UNIQUE(date, hour)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE demand (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            demand_kw REAL NOT NULL,
            source TEXT DEFAULT 'historical',
            UNIQUE(date, hour)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE pv_profile (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            pv_kw REAL NOT NULL,
            UNIQUE(date, hour)
        )
    """)
    
    # Populate starting from 2024-01-01
    start_date = datetime(2024, 1, 1)
    
    print(f"Loading {len(prices)} hours of data...")
    
    for i in range(len(prices)):
        current_dt = start_date + timedelta(hours=i)
        date_str = current_dt.strftime("%Y-%m-%d")
        hour = current_dt.hour + 1 # 1-24
        
        cursor.execute("INSERT INTO prices (date, hour, price_hrn_per_mwh) VALUES (?, ?, ?)",
                      (date_str, hour, prices[i]))
        
        cursor.execute("INSERT INTO pv_profile (date, hour, pv_kw) VALUES (?, ?, ?)",
                      (date_str, hour, pv_gen[i]))
        
        # Simple demand simulation for now (constant 150 kW)
        cursor.execute("INSERT INTO demand (date, hour, demand_kw) VALUES (?, ?, ?)",
                      (date_str, hour, 150.0))
        
    conn.commit()
    conn.close()
    print("✅ Database populated with real Chervonohrad data.")

if __name__ == "__main__":
    setup_real_data()
