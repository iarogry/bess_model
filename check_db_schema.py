import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_schema():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "battery_sim"),
        user=os.getenv("DB_USER", "iaroslav"),
        password=os.getenv("DB_PASS", "vinylfun-1206"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )
    cursor = conn.cursor()
    
    tables = ["system_config", "prices", "pv_profile", "demand"]
    for table in tables:
        print(f"\nSchema for {table}:")
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
        for col in cursor.fetchall():
            print(f"  - {col[0]}: {col[1]}")
            
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
