
import sqlite3
from pathlib import Path

def check_db():
    db_path = Path("data.db")
    if not db_path.exists():
        print("Database data.db does not exist!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Database Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"Table: {table[0]}")
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  Count: {count}")

    print("\n--- Sample Prices (if available) ---")
    try:
        cursor.execute("SELECT date, hour, price_hrn_per_mwh FROM prices LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error reading prices: {e}")

    conn.close()

if __name__ == "__main__":
    check_db()
