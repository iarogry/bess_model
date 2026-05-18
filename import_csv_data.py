
import pandas as pd
import sqlite3
import psycopg2
from pathlib import Path
import os

# Paths
DATA_DIR = Path("data")
DB_PATH = Path("data.db")

# PG Config
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "iaroslav"
PG_PASS = "vinylfun-1206"
PG_DB = "battery_sim"

os.environ['PGCLIENTENCODING'] = 'UTF8'

def import_csvs():
    # Files to process
    files = {
        'prices.csv': 'prices',
        'pv_gen.csv': 'pv_profile',
        'demand.csv': 'demand',
        'config.csv': 'system_config'
    }

    sl_conn = sqlite3.connect(DB_PATH)
    
    try:
        pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB)
        pg_conn.autocommit = True
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        pg_conn = None

    for csv_name, table in files.items():
        csv_path = DATA_DIR / csv_name
        if not csv_path.exists() or csv_path.stat().st_size < 30:
            print(f"Skipping {csv_name} (empty or missing)")
            continue
        
        print(f"Importing {csv_name} into {table}...")
        df = pd.read_csv(csv_path)
        
        # 1. Update SQLite
        df.to_sql(table, sl_conn, if_exists='replace', index=False)
        
        # 2. Update Postgres
        if pg_conn:
            # Drop and create to handle schema changes automatically
            pg_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            
            col_defs = []
            for col in df.columns:
                dtype = "DOUBLE PRECISION" if df[col].dtype == 'float64' else "TEXT"
                if col == "hour": dtype = "INTEGER"
                col_defs.append(f"{col} {dtype}")
                
            pg_cursor.execute(f"CREATE TABLE {table} ({', '.join(col_defs)})")
            
            cols = ",".join(list(df.columns))
            placeholders = ",".join(["%s"] * len(df.columns))
            insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
            pg_cursor.executemany(insert_sql, df.values.tolist())
            print(f"  Synced {len(df)} rows to PostgreSQL")

    sl_conn.close()
    if pg_conn: pg_conn.close()
    print("\n✅ Import complete.")

if __name__ == "__main__":
    import_csvs()
