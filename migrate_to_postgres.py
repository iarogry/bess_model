import sqlite3
import psycopg2
from pathlib import Path
import os

# Configuration from Odoo
SQLITE_DB = Path("data.db")
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "iaroslav"
PG_PASS = "vinylfun-1206"
PG_DB = "battery_sim"

os.environ['PGCLIENTENCODING'] = 'UTF8'

def sync_to_postgres():
    if not SQLITE_DB.exists():
        return

    try:
        pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=PG_DB)
        pg_conn.autocommit = True
        pg_cursor = pg_conn.cursor()
        
        sl_conn = sqlite3.connect(DB_PATH if 'DB_PATH' in globals() else "data.db")
        sl_cursor = sl_conn.cursor()

        # 1. Списки таблиць
        static_tables = ['prices', 'pv_profile', 'demand', 'system_config']
        result_tables = ['dispatch_results', 'daily_summary']

        # 2. Очищуємо лише результати (щоб бачити свіжий прогін)
        for table in result_tables:
            pg_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            # Скрипт імпорту створить їх заново або ми можемо просто видалити дані
            # Але для Postgres надійніше перестворити схему якщо вона змінилась
        
        # 3. Синхронізуємо дані
        for table in static_tables + result_tables:
            try:
                # Отримуємо імена колонок
                sl_cursor.execute(f"PRAGMA table_info({table})")
                cols_info = sl_cursor.fetchall()
                if not cols_info: continue
                
                cols = [col[1] for col in cols_info]
                
                sl_cursor.execute(f"SELECT * FROM {table}")
                rows = sl_cursor.fetchall()
                
                if rows:
                    pg_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    col_defs = []
                    for col in cols_info:
                        name = col[1]
                        ctype = col[2].upper()
                        pg_type = "DOUBLE PRECISION" if "REAL" in ctype else ("INTEGER" if "INT" in ctype else "TEXT")
                        col_defs.append(f"{name} {pg_type}")
                    
                    pg_cursor.execute(f"CREATE TABLE {table} ({', '.join(col_defs)})")
                    
                    placeholders = ",".join(["%s"] * len(cols))
                    insert_sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
                    pg_cursor.executemany(insert_sql, rows)
                    print(f"  Synced {table}: {len(rows)} rows")
            except Exception as table_e:
                print(f"  Error syncing table {table}: {table_e}")

        sl_conn.close()
        pg_conn.close()
        print("✅ Data pushed to PostgreSQL successfully.")
    except Exception as e:
        print(f"❌ PostgreSQL Sync Error: {e}")

if __name__ == "__main__":
    sync_to_postgres()
